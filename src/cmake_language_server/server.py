import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from pygls.features import (COMPLETION, FORMATTING, HOVER, INITIALIZE,
                            INITIALIZED, TEXT_DOCUMENT_DID_SAVE)
from pygls.server import LanguageServer
from pygls.types import (CompletionItem, CompletionItemKind, CompletionList,
                         CompletionParams, CompletionTriggerKind,
                         DocumentFormattingParams, Hover, InitializeParams,
                         MarkupContent, MarkupKind, Position, Range,
                         TextDocumentPositionParams, TextEdit)

from .api import API
from .formatter import Formatter
from .parser import ListParser

logger = logging.getLogger(__name__)


class CMakeLanguageServer(LanguageServer):
    _parser: ListParser
    _api: API

    def __init__(self):
        super().__init__()

        self._parser = ListParser()
        self._api = None

        @self.feature(INITIALIZE)
        def initialize(params: InitializeParams):
            opts = params.initializationOptions

            cmake = getattr(opts, 'cmakeExecutable', 'cmake')
            builddir = getattr(opts, 'buildDirectory', '')
            logging.info(f'cmakeExecutable={cmake}, buildDirectory={builddir}')

            self._api = API(cmake, Path(builddir))
            self._api.parse_doc()

        @self.feature(COMPLETION, trigger_characters=['{'])
        def completions(params: CompletionParams):
            if (params.context.triggerKind ==
                    CompletionTriggerKind.TriggerCharacter):
                token = ''
                trigger = params.context.triggerCharacter
            else:
                ret = self.cursor_word(params.textDocument.uri,
                                       params.position, False)
                if not ret:
                    return None
                token = ret[0]
                trigger = None

            items: List[CompletionItem] = []

            if trigger != '{':
                commands = self._api.search_command(token)
                items.extend(
                    CompletionItem(x,
                                   CompletionItemKind.Function,
                                   documentation=self._api.get_command_doc(x))
                    for x in commands)

            variables = self._api.search_variable(token)
            items.extend(
                CompletionItem(x,
                               CompletionItemKind.Variable,
                               documentation=self._api.get_variable_doc(x))
                for x in variables)

            if trigger != '{':
                targets = self._api.search_target(token)
                items.extend(
                    CompletionItem(x, CompletionItemKind.Class)
                    for x in targets)

            return CompletionList(False, items)

        @self.feature(FORMATTING)
        def formatting(params: DocumentFormattingParams):
            doc = self.workspace.get_document(params.textDocument.uri)
            content = doc.source
            tokens, remain = self._parser.parse(content)
            if remain:
                self.show_message('CMake parser failed')
                return None

            formatted = Formatter().format(tokens)
            lines = content.count('\n')
            return [
                TextEdit(Range(Position(0, 0), Position(lines + 1, 0)),
                         formatted)
            ]

        @self.feature(HOVER)
        def hover(params: TextDocumentPositionParams):
            ret = self.cursor_word(params.textDocument.uri, params.position)
            if not ret:
                return None
            doc = self._api.get_command_doc(ret[0].lower())
            if not doc:
                doc = self._api.get_variable_doc(ret[0])
                if not doc:
                    return None
            return Hover(MarkupContent(MarkupKind.Markdown, doc), ret[1])

        @self.thread()
        @self.feature(TEXT_DOCUMENT_DID_SAVE, includeText=False)
        @self.feature(INITIALIZED)
        def run_cmake(*args):
            if self._api.query():
                self._api.read_reply()

    def cursor_word(self,
                    uri: str,
                    position: Position,
                    include_all: bool = True) -> Optional[Tuple[str, Range]]:
        doc = self.workspace.get_document(uri)
        content = doc.source
        line = content.split('\n')[position.line]
        cursor = position.character
        for m in re.finditer(r'\w+', line):
            if m.start() <= cursor <= m.end():
                end = m.end() if include_all else cursor
                return (line[m.start():end],
                        Range(Position(position.line, m.start()),
                              Position(position.line, end)))

        return None


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('pygls').setLevel(logging.WARNING)
    CMakeLanguageServer().start_io()
