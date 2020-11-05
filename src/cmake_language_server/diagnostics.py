from itertools import combinations
from typing import List, Optional

import pyparsing as pp
from pygls.types import Diagnostic, DiagnosticSeverity, Position, Range

from .grammar import ASTNode


class DiagnosticVisitor(object):
    """ Base class for visitors """

    def __init__(self, liststr):
        self.diagnostics = []
        self.liststr = liststr

    def visit(self, node):
        ast_node_bases = [x.__name__ for x in ASTNode.mro()]
        visit_fns = [
            "visit_" + x.__name__ for x in type(node).mro()
            if x.__name__ not in ast_node_bases
        ]
        for visit_fn_name in visit_fns:
            if hasattr(self, visit_fn_name):
                maybe_diagnostic = getattr(self, visit_fn_name)(node)
                if maybe_diagnostic is not None:
                    self.diagnostics.append(maybe_diagnostic)

    def loc_to_pos(self, loc):
        return Position(pp.lineno(loc, self.liststr) - 1, pp.col(loc, self.liststr) - 1)

    def loc_to_range(self, loc):
        return Range(self.loc_to_pos(loc), self.loc_to_pos(loc + 1))


class OrphanedLoopCommand(DiagnosticVisitor):
    """ Finds continue() and break() invocations outside of loops """

    def __init__(self, liststr):
        super().__init__(liststr)
        self.loop_counter = 0

    def visit_LoopDeclaration(self, node):
        self.loop_counter += 1

    def visit_LoopEnd(self, node):
        self.loop_counter -= 1

    def visit_CommandInvocation(self, node) -> Optional[Diagnostic]:
        if node.identifier.lower() not in ["break", "continue"]:
            return None

        if self.loop_counter > 0:
            return None

        return Diagnostic(
            range=self.loc_to_range(node.loc),
            message="Orphaned loop command: Break or continue without parent loop",
            source="cmake-ls",
            severity=DiagnosticSeverity.Error
        )


class ReturnInMacro(DiagnosticVisitor):
    """ Finds return() invocations in macros """

    def __init__(self, liststr):
        super().__init__(liststr)
        self.macro_counter = 0

    def visit_CommandDeclarationStart(self, node):
        if node.identifier.lower() == "macro":
            self.macro_counter += 1

    def visit_CommandDeclarationEnd(self, node):
        if node.identifier.lower() == "endmacro":
            self.macro_counter -= 1

    def visit_CommandInvocation(self, node) -> Optional[Diagnostic]:
        if node.identifier.lower() != "return":
            return None

        if self.macro_counter < 0:
            return None

        return Diagnostic(
            range=self.loc_to_range(node.loc),
            message="Return in macro: Prefer message(FATAL_ERROR ...) to halt "
            "execution in macro",
            source="cmake-ls",
            severity=DiagnosticSeverity.Warning
        )


class RedundantAssignment(DiagnosticVisitor):
    """ Finds assignments of the form set(A ${A}) """

    def visit_CommandInvocation(self, node) -> Optional[Diagnostic]:
        if node.identifier.lower() != "set":
            return None

        if len(node.arguments) != 2:
            return None

        lhs = node.arguments[0].value
        rhs = node.arguments[1].value

        # Refuse to diagnose expressions with multiple variable evaluations
        if rhs.count("$") != 1:
            return None

        if lhs != rhs.strip("${}"):
            return None

        return Diagnostic(
            range=self.loc_to_range(node.loc),
            message="Redundant assignment: Destination and source variable names match",
            source="cmake-ls",
            severity=DiagnosticSeverity.Warning
        )


class DuplicateBranch(DiagnosticVisitor):
    """ Finds conditional branches with the exact same conditions """

    def visit_ConditionalBlock(self, node) -> Optional[Diagnostic]:
        for a, b in combinations(node.branches, 2):
            all_args_match = all([
                m.value == n.value
                for m, n in zip(a.declaration.arguments, b.declaration.arguments)
            ])
            if all_args_match:
                # Mark b a duplicate
                return Diagnostic(
                    range=self.loc_to_range(b.loc),
                    message="Duplicate conditional branch: "
                    "Condition matches a previous branch",
                    source="cmake-ls",
                    severity=DiagnosticSeverity.Warning
                )

        return None


class ModernizeLowercaseCommands(DiagnosticVisitor):
    """ Finds uppercase command incovations """
    # TODO this doesn't find instances of this on block keywords
    # (if/function/foreach/etc) because the CaselessLiteral used in the parser
    # grammar causes loss of case information. Using a case-insensitive Regex
    # instead has the drawback that the parsing exceptions become unreadable

    def visit_CommandInvocation(self, node) -> Optional[Diagnostic]:
        if not node.identifier.isupper():
            return None

        return Diagnostic(
            range=self.loc_to_range(node.loc),
            message="Modernize: prefer lowercase commands",
            source="cmake-ls",
            severity=DiagnosticSeverity.Information
        )


class ModernizePreferTargetCmds(DiagnosticVisitor):
    """ Diagnoses directory-based api calls """
    dir_api = [
        "add_definitions",
        "add_compile_options",
        "add_compile_definitions",
        "include_directories",
        "link_libraries"
    ]
    msg = "Modernize: prefer target-based commands over directory-based commands"

    def visit_CommandInvocation(self, node) -> Optional[Diagnostic]:
        if node.identifier.lower() not in ModernizePreferTargetCmds.dir_api:
            return None

        return Diagnostic(
            range=self.loc_to_range(node.loc),
            message=ModernizePreferTargetCmds.msg,
            source="cmake-ls",
            severity=DiagnosticSeverity.Information
        )


def diagnose(ast: pp.ParseResults, liststr: str) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []

    visitors = [
        DuplicateBranch,
        ModernizeLowercaseCommands,
        ModernizePreferTargetCmds,
        OrphanedLoopCommand,
        RedundantAssignment,
        ReturnInMacro,
    ]

    for visitor_class in visitors:
        visitor = visitor_class(liststr)
        ast[0].visit(visitor)
        diagnostics.extend(visitor.diagnostics)

    return diagnostics
