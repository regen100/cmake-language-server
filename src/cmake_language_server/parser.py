from typing import List, Tuple, Union
import pyparsing as pp
from .grammar import cmake_grammar

CommandTokenType = Tuple[str, List[str]]
TokenType = Union[str, CommandTokenType]
TokenList = List[TokenType]


class CMakeListsParser(object):
    token_parser: pp.ParserElement
    ast_parser: pp.ParserElement

    def __init__(self):
        self.token_parser = cmake_grammar(generate_ast=False)
        self.ast_parser = cmake_grammar(generate_ast=True)

    def parse_tokens(self, liststr: str) -> Tuple[TokenList, str]:
        """ Parse a CMakeLists file into tokens """
        for t, s, e in self.token_parser.scanString(liststr, maxMatches=1):
            if s == 0:
                return t.asList(), liststr[e:]
        return [], liststr

    def parse_ast(self, liststr: str) -> Tuple[pp.ParseResults, str]:
        """ Parse a CMakeLists file into an AST """
        for t, s, e in self.ast_parser.scanString(liststr, maxMatches=1):
            if s == 0:
                return t, liststr[e:]

        return pp.ParseResults(), liststr
