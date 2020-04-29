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

    def __init__(self, *args):
        super().__init__(*args)

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

        trigger_characters = ['{', '(']

        @self.feature(COMPLETION, trigger_characters=trigger_characters)
        def completions(params: CompletionParams):
            if (hasattr(params, 'context') and params.context.triggerKind ==
                    CompletionTriggerKind.TriggerCharacter):
                token = ''
                trigger = params.context.triggerCharacter
            else:
                line = self._cursor_line(params.textDocument.uri,
                                         params.position)
                idx = params.position.character - 1
                if 0 <= idx < len(line) and line[idx] in trigger_characters:
                    token = ''
                    trigger = line[idx]
                else:
                    word = self._cursor_word(params.textDocument.uri,
                                             params.position, False)
                    token = '' if word is None else word[0]
                    trigger = None

            items: List[CompletionItem] = []

            if trigger is None:
                commands = self._api.search_command(token)
                items.extend(
                    CompletionItem(x,
                                   CompletionItemKind.Function,
                                   documentation=self._api.get_command_doc(x),
                                   insert_text=x) for x in commands)

            if trigger is None or trigger == '{':
                variables = self._api.search_variable(token)
                items.extend(
                    CompletionItem(x,
                                   CompletionItemKind.Variable,
                                   documentation=self._api.get_variable_doc(x),
                                   insert_text=x) for x in variables)

            if trigger is None:
                targets = self._api.search_target(token)
                items.extend(
                    CompletionItem(x, CompletionItemKind.Class, insert_text=x)
                    for x in targets)

            if trigger == '(':
                func = self._cursor_function(params.textDocument.uri,
                                             params.position)
                if func is not None:
                    func = func.lower()
                    if func == 'include':
                        modules = self._api.search_module(token, False)
                        items.extend(
                            CompletionItem(x,
                                           CompletionItemKind.Module,
                                           documentation=self._api.
                                           get_module_doc(x, False),
                                           insert_text=x) for x in modules)
                    elif func == 'find_package':
                        modules = self._api.search_module(token, True)
                        items.extend(
                            CompletionItem(x,
                                           CompletionItemKind.Module,
                                           documentation=self._api.
                                           get_module_doc(x, True),
                                           insert_text=x) for x in modules)

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
            word = self._cursor_word(params.textDocument.uri, params.position,
                                     True)
            if not word:
                return None

            candidates = [
                lambda x: self._api.get_command_doc(x.lower()),
                lambda x: self._api.get_variable_doc(x),
                lambda x: self._api.get_module_doc(x, False),
                lambda x: self._api.get_module_doc(x, True),
            ]
            for c in candidates:
                doc = c(word[0])
                if doc is None:
                    continue
                return Hover(MarkupContent(MarkupKind.Markdown, doc), word[1])
            return None

        @self.thread()
        @self.feature(TEXT_DOCUMENT_DID_SAVE, includeText=False)
        @self.feature(INITIALIZED)
        def run_cmake(*args):
            if self._api.query():
                self._api.read_reply()

    def _cursor_function(self, uri: str, position: Position) -> Optional[str]:
        doc = self.workspace.get_document(uri)
        lines = doc.source.split('\n')[:position.line + 1]
        lines[-1] = lines[-1][:position.character - 1].strip()
        words = re.split(r'[\s\n()]+', '\n'.join(lines))
        return words[-1] if words else None

    def _cursor_line(self, uri: str, position: Position) -> str:
        doc = self.workspace.get_document(uri)
        content = doc.source
        line = content.split('\n')[position.line]
        return line

    def _cursor_word(self,
                     uri: str,
                     position: Position,
                     include_all: bool = True) -> Optional[Tuple[str, Range]]:
        line = self._cursor_line(uri, position)
        cursor = position.character
        for m in re.finditer(r'\w+', line):
            end = m.end() if include_all else cursor
            if m.start() <= cursor <= m.end():
                word = (line[m.start():end],
                        Range(Position(position.line, m.start()),
                              Position(position.line, end)))
                return word
        return None


def main(args=None):
    from argparse import ArgumentParser
    from . import __version__

    parser = ArgumentParser(description='CMake Language Server')
    parser.add_argument('--version',
                        action='version',
                        version=f'%(prog)s {__version__}')
    args = parser.parse_args(args)

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('pygls').setLevel(logging.WARNING)
    CMakeLanguageServer().start_io()
