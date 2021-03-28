from concurrent import futures
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cmake_language_server.server import CMakeLanguageServer
from pygls.lsp.methods import (
    COMPLETION,
    FORMATTING,
    HOVER,
    INITIALIZE,
    TEXT_DOCUMENT_DID_OPEN,
)
from pygls.lsp.types import (
    ClientCapabilities,
    CompletionContext,
    CompletionParams,
    CompletionTriggerKind,
    DidOpenTextDocumentParams,
    DocumentFormattingParams,
    FormattingOptions,
    InitializeParams,
    Position,
    TextDocumentIdentifier,
    TextDocumentItem,
    TextDocumentPositionParams,
)
from pygls.server import LanguageServer

CALL_TIMEOUT = 2


def _init(client: LanguageServer, root: Path) -> None:
    retry = 3
    while retry > 0:
        try:
            client.lsp.send_request(
                INITIALIZE,
                InitializeParams(
                    process_id=1234,
                    root_uri=root.as_uri(),
                    capabilities=ClientCapabilities(),
                ),
            ).result(timeout=CALL_TIMEOUT)
        except futures.TimeoutError:
            retry -= 1
        else:
            break


def _open(client: LanguageServer, path: Path, text: Optional[str] = None) -> None:
    if text is None:
        with open(path) as fp:
            text = fp.read()

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(
            text_document=TextDocumentItem(
                uri=path.as_uri(), language_id="cmake", version=1, text=text
            )
        ),
    )


def _test_completion(
    client_server: Tuple[LanguageServer, CMakeLanguageServer],
    datadir: Path,
    content: str,
    context: Optional[CompletionContext],
) -> Dict[str, Any]:
    client, server = client_server
    _init(client, datadir)
    path = datadir / "CMakeLists.txt"
    _open(client, path, content)
    params = CompletionParams(
        text_document=TextDocumentIdentifier(uri=path.as_uri()),
        position=Position(line=0, character=len(content)),
        context=context,
    )
    if context is None:
        # some clients do not send context
        del params.context
    ret = client.lsp.send_request(COMPLETION, params).result(timeout=CALL_TIMEOUT)
    assert isinstance(ret, dict)
    return ret


def test_initialize(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    client, server = client_server

    assert server._api is None
    _init(client, datadir)
    assert server._api is not None


def test_completions_invoked(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    response = _test_completion(
        client_server,
        datadir,
        "projec",
        CompletionContext(trigger_kind=CompletionTriggerKind.Invoked),
    )
    item = next(filter(lambda x: x["label"] == "project", response["items"]), None)
    assert item is not None
    assert isinstance(item["documentation"], str)
    assert "<PROJECT-NAME>" in item["documentation"]


def test_completions_nocontext(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    response = _test_completion(client_server, datadir, "projec", None)
    item = next(filter(lambda x: x["label"] == "project", response["items"]), None)
    assert item is not None
    assert isinstance(item["documentation"], str)
    assert "<PROJECT-NAME>" in item["documentation"]


def test_completions_triggercharacter_variable(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    response = _test_completion(
        client_server,
        datadir,
        "${",
        CompletionContext(
            trigger_kind=CompletionTriggerKind.TriggerCharacter, trigger_character="{"
        ),
    )
    assert "PROJECT_VERSION" in [x["label"] for x in response["items"]]

    response_nocontext = _test_completion(client_server, datadir, "${", None)
    assert response == response_nocontext


def test_completions_triggercharacter_module(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    response = _test_completion(
        client_server,
        datadir,
        "include(",
        CompletionContext(
            trigger_kind=CompletionTriggerKind.TriggerCharacter, trigger_character="("
        ),
    )
    assert "GoogleTest" in [x["label"] for x in response["items"]]

    response_nocontext = _test_completion(client_server, datadir, "include(", None)
    assert response == response_nocontext


def test_completions_triggercharacter_package(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    response = _test_completion(
        client_server,
        datadir,
        "find_package(",
        CompletionContext(
            trigger_kind=CompletionTriggerKind.TriggerCharacter, trigger_character="("
        ),
    )
    assert "Boost" in [x["label"] for x in response["items"]]

    response_nocontext = _test_completion(client_server, datadir, "find_package(", None)
    assert response == response_nocontext


def test_formatting(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    client, server = client_server
    _init(client, datadir)
    path = datadir / "CMakeLists.txt"
    _open(client, path, "a ( b c ) ")
    response = client.lsp.send_request(
        FORMATTING,
        DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri=path.as_uri()),
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        ),
    ).result(timeout=CALL_TIMEOUT)
    assert response[0]["newText"] == "a(b c)\n"


def test_hover(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    client, server = client_server
    _init(client, datadir)
    path = datadir / "CMakeLists.txt"
    _open(client, path, "project()")
    response = client.lsp.send_request(
        HOVER,
        TextDocumentPositionParams(
            text_document=TextDocumentIdentifier(uri=path.as_uri()),
            position=Position(line=0, character=0),
        ),
    ).result(timeout=CALL_TIMEOUT)
    assert "<PROJECT-NAME>" in response["contents"]["value"]
