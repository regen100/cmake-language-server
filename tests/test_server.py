from concurrent import futures
from pathlib import Path
from typing import Optional, Tuple

import pytest
from lsprotocol.types import (
    INITIALIZE,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_HOVER,
    ClientCapabilities,
    CompletionContext,
    CompletionList,
    CompletionParams,
    CompletionTriggerKind,
    DidOpenTextDocumentParams,
    DocumentFormattingParams,
    FormattingOptions,
    HoverParams,
    InitializeParams,
    Position,
    TextDocumentIdentifier,
    TextDocumentItem,
)
from pygls.server import LanguageServer

from cmake_language_server.server import CMakeLanguageServer

CALL_TIMEOUT = 2


def _init(client: LanguageServer, root: Path) -> None:
    retry = 3
    while retry > 0:
        try:
            client.lsp.send_request(  # type:ignore[no-untyped-call]
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
        text = path.read_text()

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
) -> CompletionList:
    client, server = client_server
    _init(client, datadir)
    path = datadir / "CMakeLists.txt"
    _open(client, path, content)
    params = CompletionParams(
        text_document=TextDocumentIdentifier(uri=path.as_uri()),
        position=Position(line=0, character=len(content)),
        context=context,
    )
    ret = client.lsp.send_request(  # type:ignore[no-untyped-call]
        TEXT_DOCUMENT_COMPLETION, params
    ).result(timeout=CALL_TIMEOUT)
    assert isinstance(ret, CompletionList)
    return ret


def test_initialize(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    client, server = client_server

    assert server._api is None
    _init(client, datadir)
    assert server._api is not None


@pytest.mark.parametrize(
    "context", [CompletionContext(trigger_kind=CompletionTriggerKind.Invoked), None]
)
def test_completions(
    context: Optional[CompletionContext],
    client_server: Tuple[LanguageServer, CMakeLanguageServer],
    datadir: Path,
) -> None:
    response = _test_completion(client_server, datadir, "projec", context)
    item = next(filter(lambda x: x.label == "project", response.items), None)
    assert item is not None
    assert isinstance(item.documentation, str)
    assert "<PROJECT-NAME>" in item.documentation


@pytest.mark.parametrize(
    "text, item",
    [("find_package(", "Boost"), ("include(", "GoogleTest"), ("${", "PROJECT_VERSION")],
)
def test_completions_triggercharacter(
    text: str,
    item: str,
    client_server: Tuple[LanguageServer, CMakeLanguageServer],
    datadir: Path,
) -> None:
    response = _test_completion(
        client_server,
        datadir,
        text,
        CompletionContext(
            trigger_kind=CompletionTriggerKind.TriggerCharacter,
            trigger_character=text[-1],
        ),
    )
    assert item in [x.label for x in response.items]

    response_nocontext = _test_completion(client_server, datadir, text, None)
    assert response == response_nocontext


def test_formatting(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    client, server = client_server
    _init(client, datadir)
    path = datadir / "CMakeLists.txt"
    _open(client, path, "a ( b c ) ")
    response = client.lsp.send_request(  # type:ignore[no-untyped-call]
        TEXT_DOCUMENT_FORMATTING,
        DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri=path.as_uri()),
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        ),
    ).result(timeout=CALL_TIMEOUT)
    assert response[0].new_text == "a(b c)\n"


def test_hover(
    client_server: Tuple[LanguageServer, CMakeLanguageServer], datadir: Path
) -> None:
    client, server = client_server
    _init(client, datadir)
    path = datadir / "CMakeLists.txt"
    _open(client, path, "project()")
    response = client.lsp.send_request(  # type:ignore[no-untyped-call]
        TEXT_DOCUMENT_HOVER,
        HoverParams(
            text_document=TextDocumentIdentifier(uri=path.as_uri()),
            position=Position(line=0, character=0),
        ),
    ).result(timeout=CALL_TIMEOUT)
    assert "<PROJECT-NAME>" in response.contents.value
