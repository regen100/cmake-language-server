from typing import Any, List

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

    def visit(self, visitor):
        visitor.visit(self)

    def visit_self_and_children(self, visitor, children):
        visitor.visit(self)
        for child in children:
            child.visit(visitor)


class Argument(ASTNode):
    value: str  # NOTE: Without parsed quotes or bracket!

    def assign_fields(self):
        self.value = self.tokens[0]
        del self.tokens


class UnquotedArgument(Argument):
    pass


class QuotedArgument(Argument):
    pass


class BracketArgument(Argument):
    pass


class CommandInvocation(ASTNode):
    identifier: str
    arguments: List[Argument]

    def assign_fields(self):
        self.identifier = self.tokens[0]
        self.arguments = self.tokens[1].asList()
        del self.tokens

    def visit(self, visitor):
        self.visit_self_and_children(visitor, self.arguments)


class CommandDeclarationStart(CommandInvocation):
    identifier: str  # Some case of the keyword function or macro
    name: Argument  # Name of the command being declared
    arguments: List[Argument]  # Arguments to the command being declared

    def assign_fields(self):
        self.identifier = self.tokens[0]
        self.name = self.tokens[1][0]
        self.arguments = self.tokens[1][1:]
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)
        self.name.visit(visitor)
        for child in self.arguments:
            child.visit(visitor)


class CommandDeclarationEnd(CommandInvocation):
    pass


class CommandDeclarationBlock(ASTNode):
    declaration: CommandDeclarationStart
    children: List[Any]
    end: CommandDeclarationEnd

    def assign_fields(self):
        self.declaration = self.tokens[0]
        self.end = self.tokens[-1]
        self.children = self.tokens[1:-1]
        del self.tokens

    def visit(self, visitor):
        self.visit_self_and_children(visitor, self.children)


class ConditionalBranchDeclaration(CommandInvocation):
    pass


class ConditionalEnd(CommandInvocation):
    pass


class ConditionalBranch(ASTNode):
    declaration: ConditionalBranchDeclaration
    children: List[Any]

    def assign_fields(self):
        self.declaration = self.tokens[0]
        self.children = self.tokens[1:]
        del self.tokens

    def visit(self, visitor):
        self.visit_self_and_children(visitor, self.children)


class ConditionalBlock(ASTNode):
    branches: List[ConditionalBranch]
    end: ConditionalEnd

    def assign_fields(self):
        self.branches = self.tokens[:-1]
        self.end = self.tokens[-1]
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)
        for child in self.branches:
            child.visit(visitor)

        self.end.visit(visitor)


class LoopDeclaration(CommandInvocation):
    pass


class LoopEnd(CommandInvocation):
    pass


class LoopBlock(ASTNode):
    declaration: LoopDeclaration
    children: List[Any]
    end: LoopEnd

    def assign_fields(self):
        self.declaration = self.tokens[0]
        self.children = self.tokens[1:-1]
        self.end = self.tokens[-1]
        del self.tokens

    def visit(self, visitor):
        visitor.visit(self)
        self.declaration.visit(visitor)
        for child in self.children:
            child.visit(visitor)

        self.end.visit(visitor)


class ListsFile(ASTNode):
    blocks: List[Any]

    def assign_fields(self):
        self.blocks = self.tokens.asList()
        del self.tokens

    def visit(self, visitor):
        self.visit_self_and_children(visitor, self.blocks)


def token_grammar() -> pp.ParserElement:
    """ Defines a cmake grammar to generate formattable tokens """
    # Spaces and new lines
    newline = "\n"
    space_plus = pp.Regex("[ \t]+")
    space_star = pp.Optional(space_plus)

    # Quoted arguments
    quoted_element = pp.Regex(r'[^\\"]|\\[^A-Za-z0-9]|\\[trn]')
    quoted_argument = pp.Combine('"' + pp.ZeroOrMore(quoted_element) + '"')

    # Bracket content
    bracket_content = pp.Forward()

    def action_bracket_open(tokens: pp.ParseResults):
        nonlocal bracket_content
        marker = "]" + "=" * (len(tokens[0]) - 2) + "]"
        bracket_content <<= pp.SkipTo(marker, include=True)

    bracket_open = pp.Regex(r"\[=*\[").setParseAction(action_bracket_open)
    bracket_argument = pp.Combine(bracket_open + bracket_content)

    # Unquoted arguments
    unquoted_element = pp.Regex(r'[^\s()#"\\]|\\[^A-Za-z0-9]|\\[trn]')
    unquoted_argument = pp.Combine(pp.OneOrMore(unquoted_element))

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
    arguments << pp.ZeroOrMore(
        argument | line_ending | space_plus | "(" + arguments + ")"
    ).leaveWhitespace()

    arguments = pp.Group(arguments)
    PAREN_L, PAREN_R = map(pp.Suppress, "()")
    command_invocation = (
        identifier + space_star.suppress() + PAREN_L + arguments + PAREN_R
    )
    command_invocation = command_invocation.setParseAction(
        lambda t: (t[0], t[1].asList()))

    # Superstructure
    file_element = (
        space_star + command_invocation + line_ending | line_ending
    ).leaveWhitespace()
    listsfile = pp.ZeroOrMore(file_element)

    return listsfile


def ast_grammar() -> pp.ParserElement:
    """ Defines a cmake grammar and semantic actions to generate an AST """
    # Spaces and new lines
    newline = "\n"
    space_plus = pp.Regex("[ \t]+")
    space_star = pp.Optional(space_plus)

    # Quoted arguments
    quoted_element = pp.Regex(r'[^\\"]|\\[^A-Za-z0-9]|\\[trn]')
    quoted_argument = pp.Combine(
        pp.Suppress('"')
        + pp.ZeroOrMore(quoted_element)
        + pp.Suppress('"')
    ).setParseAction(QuotedArgument)

    # Bracket content
    bracket_content = pp.Forward()

    def action_bracket_open(tokens: pp.ParseResults):
        nonlocal bracket_content
        marker = "]" + "=" * (len(tokens[0]) - 2) + "]"
        bracket_content <<= pp.SkipTo(marker, include=True)

    bracket_open = pp.Regex(r"\[=*\[").setParseAction(action_bracket_open)
    bracket_argument = (bracket_open.suppress() +
                        bracket_content).setParseAction(BracketArgument)

    # Unquoted arguments
    unquoted_element = pp.Regex(r'[^\s()#"\\]|\\[^A-Za-z0-9]|\\[trn]')
    unquoted_argument = pp.Combine(pp.OneOrMore(
        unquoted_element)).setParseAction(UnquotedArgument)

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
    block_keyword_strs = [
        "function", "macro", "endfunction", "endmacro",
        "if", "elseif", "endif",
        "foreach", "endforeach", "while", "endwhile"
    ]
    block_keywords = pp.Or([pp.CaselessLiteral(lit) for lit in block_keyword_strs])
    identifier = ~block_keywords + pp.Word(pp.alphas + "_", pp.alphanums + "_")
    arguments = pp.Forward()
    arguments << pp.ZeroOrMore(
        argument
        | line_ending.suppress()
        | space_plus.suppress()
        | pp.Suppress("(") + arguments + pp.Suppress(")")
    ).leaveWhitespace()

    arguments = pp.Group(arguments)
    PAREN_L, PAREN_R = map(pp.Suppress, "()")
    command_invocation = (
        identifier + space_star.suppress() + PAREN_L + arguments + PAREN_R
    ).setParseAction(CommandInvocation)

    # Superstructure
    block = pp.Forward()

    def make_line_parser(invocation):
        return space_star.suppress() + invocation + line_ending.suppress()

    def make_keyword_parser(literal_parser, action):
        return (
            literal_parser + space_star.suppress() + PAREN_L + arguments + PAREN_R
        ).setParseAction(action)

    def make_keyword_line_parser(literal, action):
        # parser = pp.Regex(pattern=literal, flags=re.IGNORECASE)
        parser = pp.CaselessLiteral(literal)
        kw_parser = make_keyword_parser(parser, action)
        return make_line_parser(kw_parser)

    # Command declaration (function and macro)
    function_decl_start = make_keyword_line_parser("function", CommandDeclarationStart)
    function_decl_end = make_keyword_line_parser("endfunction", CommandDeclarationEnd)
    macro_decl_start = make_keyword_line_parser("macro", CommandDeclarationStart)
    macro_decl_end = make_keyword_line_parser("endmacro", CommandDeclarationEnd)
    command_decl_block = (
        (function_decl_start - pp.ZeroOrMore(block) - function_decl_end)
        | (macro_decl_start - pp.ZeroOrMore(block) - macro_decl_end)
    ).setParseAction(CommandDeclarationBlock)

    # Conditional block
    if_line = make_keyword_line_parser("if", ConditionalBranchDeclaration)
    elseif_line = make_keyword_line_parser("elseif", ConditionalBranchDeclaration)
    endif_line = make_keyword_line_parser("endif", ConditionalEnd)
    conditional_block = (
        (if_line - pp.ZeroOrMore(block)).setParseAction(ConditionalBranch)
        - pp.ZeroOrMore(
            (elseif_line - pp.ZeroOrMore(block)).setParseAction(ConditionalBranch)
        )
        - endif_line
    ).setParseAction(ConditionalBlock)

    # Loops
    foreach_start = make_keyword_line_parser("foreach", LoopDeclaration)
    foreach_end = make_keyword_line_parser("endforeach", LoopEnd)
    while_start = make_keyword_line_parser("while", LoopDeclaration)
    while_end = make_keyword_line_parser("endwhile", LoopEnd)
    loop_block = (
        (foreach_start - pp.ZeroOrMore(block) - foreach_end)
        | (while_end - pp.ZeroOrMore(block) - while_end)
    ).setParseAction(LoopBlock)

    # Now we can define block
    block <<= (
        command_decl_block
        | conditional_block
        | loop_block
        | space_star.suppress() + command_invocation + line_ending.suppress()
        | line_ending.suppress()
    ).leaveWhitespace()

    listsfile = pp.ZeroOrMore(block).setParseAction(ListsFile)

    # Assign expression names for rr diagram and better explanations
    var_name = None
    for var_name in locals().keys():
        if isinstance(locals()[var_name], pp.ParserElement):
            locals()[var_name].setName(var_name)
            # locals()[var_name].setDebug()

    return listsfile
