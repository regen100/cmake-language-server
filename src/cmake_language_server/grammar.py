import pyparsing as pp


class ASTNode(object):
    def __init__(self, loc, tokens):
        self.loc = loc
        self.tokens = tokens
        self.assign_fields()

    def __str__(self):
        return self.__class__.__name__ + ':' + str(self.__dict__)

    def __repr__(self):
        return self.__str__()


class ListsFile(ASTNode):
    def assign_fields(self):
        self.invocations = self.tokens.asList()
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)
        for child in self.invocations:
            child.visit(visitor)


class CommandInvocation(ASTNode):
    def assign_fields(self):
        self.identifier = self.tokens[0]
        self.arguments = self.tokens[1].asList()
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)
        for child in self.arguments:
            child.visit(visitor)


class QuotedArgument(ASTNode):
    def assign_fields(self):
        self.value = self.tokens[0]
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)


class UnquotedArgument(ASTNode):
    def assign_fields(self):
        self.value = self.tokens[0]
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)


class BracketArgument(ASTNode):
    def assign_fields(self):
        self.value = self.tokens[0]
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)


def cmake_grammar(generate_ast: bool) -> pp.ParserElement:
    """ Defines the cmake grammar and semantic actions to generate an AST """
    # Spaces and new lines
    newline = "\n"
    space_plus = pp.Regex("[ \t]+")
    space_star = pp.Optional(space_plus)

    # Quoted arguments
    quoted_element = pp.Regex(r'[^\\"]|\\[^A-Za-z0-9]|\\[trn]')
    if generate_ast:
        quoted_argument = pp.Combine(
            pp.Suppress('"')
            + pp.ZeroOrMore(quoted_element)
            + pp.Suppress('"')
        ).setParseAction(QuotedArgument)
    else:
        quoted_argument = pp.Combine('"' + pp.ZeroOrMore(quoted_element) + '"')

    # Bracket content
    bracket_content = pp.Forward()

    def action_bracket_open(tokens: pp.ParseResults):
        nonlocal bracket_content
        marker = "]" + "=" * (len(tokens[0]) - 2) + "]"
        bracket_content <<= pp.SkipTo(marker, include=True)

    bracket_open = pp.Regex(r"\[=*\[").setParseAction(action_bracket_open)
    bracket_argument = pp.Combine(bracket_open + bracket_content)
    if generate_ast:
        bracket_argument = bracket_argument.setParseAction(BracketArgument)

    # Unquoted arguments
    unquoted_element = pp.Regex(r'[^\s()#"\\]|\\[^A-Za-z0-9]|\\[trn]')
    unquoted_argument = pp.Combine(pp.OneOrMore(unquoted_element))
    if generate_ast:
        unquoted_argument = unquoted_argument.setParseAction(UnquotedArgument)

    argument = bracket_argument | quoted_argument | unquoted_argument

    # Comments
    line_comment = pp.Combine("#" + ~bracket_open + pp.SkipTo(pp.LineEnd()))
    bracket_comment = pp.Combine("#" + bracket_argument)
    line_ending = (
        space_star
        + pp.ZeroOrMore(bracket_comment + space_star)
        + pp.Optional(line_comment)
        + (newline | pp.lineEnd)
    )

    # Command invocation
    identifier = pp.Word(pp.alphas + "_", pp.alphanums + "_")
    arguments = pp.Forward()
    if generate_ast:
        arguments << pp.ZeroOrMore(
            argument
            | line_ending.suppress()
            | space_plus.suppress()
            | pp.Suppress("(") + arguments + pp.Suppress(")")
        ).leaveWhitespace()
    else:
        arguments << pp.ZeroOrMore(
            argument | line_ending | space_plus | "(" + arguments + ")"
        ).leaveWhitespace()

    arguments = pp.Group(arguments)
    PAREN_L, PAREN_R = map(pp.Suppress, "()")
    command_invocation = (
        identifier + space_star.suppress() + PAREN_L + arguments + PAREN_R
    )
    if generate_ast:
        command_invocation = command_invocation.setParseAction(CommandInvocation)
    else:
        command_invocation = command_invocation.setParseAction(
            lambda t: (t[0], t[1].asList()))

    # Superstructure
    if generate_ast:
        file_element = (
            space_star.suppress() + command_invocation + line_ending.suppress()
            | line_ending.suppress()
        ).leaveWhitespace()
    else:
        file_element = (
            space_star + command_invocation + line_ending | line_ending
        ).leaveWhitespace()

    listsfile = pp.ZeroOrMore(file_element)
    if generate_ast:
        listsfile.setParseAction(ListsFile)

    # Assign expression names for rr diagram and better explanations
    var_name = None
    for var_name in locals().keys():
        if isinstance(locals()[var_name], pp.ParserElement):
            locals()[var_name].setName(var_name)
            # locals()[var_name].setDebug()

    return listsfile
