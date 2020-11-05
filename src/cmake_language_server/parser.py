from typing import List, Tuple, Union

import pyparsing as pp
from pygls.types import Diagnostic, DiagnosticSeverity, Position, Range

from .grammar import ast_grammar, token_grammar

CommandTokenType = Tuple[str, List[str]]
TokenType = Union[str, CommandTokenType]
TokenList = List[TokenType]


class CMakeListsParser(object):
    token_parser: pp.ParserElement
    ast_parser: pp.ParserElement

    def __init__(self):
        self.token_parser = token_grammar()
        self.ast_parser = ast_grammar()

    def parse_tokens(self, liststr: str) -> Tuple[TokenList, str]:
        """ Parse a CMakeLists file into tokens """
        for t, s, e in self.token_parser.scanString(liststr, maxMatches=1):
            if s == 0:
                return t.asList(), liststr[e:]
        return [], liststr

    def parse_ast(self, liststr: str) -> Union[Tuple[pp.ParseResults, str], Diagnostic]:
        """ Parse a CMakeLists file into an AST or make a Diagnostic if parsing fails"""
        try:
            for t, s, e in self.ast_parser.scanString(liststr, maxMatches=1):
                if s == 0:
                    return t, liststr[e:]

            return pp.ParseResults(), liststr

        except pp.ParseSyntaxException as pe:
            # Convert parsing exception into a diagnostic
            start = Position(max(0, pe.lineno-2), max(0, pe.col-1))
            end = Position(max(0, pe.lineno-2), pe.col)
            msg = str(pe)
            first_bracket = msg.find("(")
            if first_bracket != -1:
                msg = msg[:first_bracket].strip()

            return Diagnostic(
                range=Range(start, end),
                message=msg,
                source="cmake-ls",
                severity=DiagnosticSeverity.Error,
            )


def main(args: List[str] = None):
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser(description="Parse CMake list files")
    parser.add_argument("lists", type=Path, nargs="*", help="CMake list files")
    args = parser.parse_args(args)

    list_parser = CMakeListsParser()
    if not args.lists:
        return

    for listpath in args.lists:
        with listpath.open() as fp:
            content = fp.read()

        results = list_parser.ast_parser.parseString(content, parseAll=True)
        results.pprint()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
