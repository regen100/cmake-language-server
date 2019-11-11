from typing import List, Tuple, Union

import pyparsing as pp

CommandTokenType = Tuple[str, List[str]]
TokenType = Union[str, CommandTokenType]
TokenList = List[TokenType]


class ListParser(object):
    _parser: pp.ParserElement

    def __init__(self):
        newline = '\n'
        space_plus = pp.Regex('[ \t]+')
        space_star = pp.Optional(space_plus)

        quoted_element = pp.Regex(r'[^\\"]|\\[^A-Za-z0-9]|\\[trn]')
        quoted_argument = pp.Combine('"' + pp.ZeroOrMore(quoted_element) + '"')

        bracket_content = pp.Forward()

        def action_bracket_open(tokens: pp.ParseResults):
            nonlocal bracket_content
            marker = ']' + '=' * (len(tokens[0]) - 2) + ']'
            bracket_content <<= pp.SkipTo(marker, include=True)

        bracket_open = pp.Regex(r'\[=*\[').setParseAction(action_bracket_open)
        bracket_argument = pp.Combine(bracket_open + bracket_content)

        unquoted_element = pp.Regex(r'[^\s()#"\\]|\\[^A-Za-z0-9]|\\[trn]')
        unquoted_argument = pp.Combine(pp.OneOrMore(unquoted_element))

        argument = bracket_argument | quoted_argument | unquoted_argument

        line_comment = pp.Combine('#' + ~bracket_open +
                                  pp.SkipTo(pp.LineEnd()))
        bracket_comment = pp.Combine('#' + bracket_argument)
        line_ending = (space_star +
                       pp.ZeroOrMore(bracket_comment + space_star) +
                       pp.Optional(line_comment) + (newline | pp.lineEnd))

        identifier = pp.Word(pp.alphas + '_', pp.alphanums + '_')
        arguments = pp.Forward()
        arguments << pp.ZeroOrMore(argument | line_ending | space_plus
                                   | '(' + arguments + ')').leaveWhitespace()
        arguments = pp.Group(arguments)
        PAREN_L, PAREN_R = map(pp.Suppress, '()')
        command_invocation = (
            identifier + space_star.suppress() + PAREN_L + arguments +
            PAREN_R).setParseAction(lambda t: (t[0], t[1].asList()))

        file_element = (space_star + command_invocation + line_ending
                        | line_ending).leaveWhitespace()
        file = pp.ZeroOrMore(file_element)

        self._parser = file

    def parse(self, liststr: str) -> Tuple[TokenList, str]:
        for t, s, e in self._parser.scanString(liststr, maxMatches=1):
            if s == 0:
                return t.asList(), liststr[e:]
        return [], liststr
