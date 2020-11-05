from typing import Optional, List
import pyparsing as pp
from pygls.types import Diagnostic, DiagnosticSeverity, Range, Position


class DiagnosticVisitor(object):
    def __init__(self, liststr):
        self.diagnostics = []
        self.liststr = liststr

    def visit(self, node):
        visit_fn_name = "visit_" + type(node).__name__
        if hasattr(self, visit_fn_name):
            maybe_diagnostic = getattr(self, visit_fn_name)(node)
            if maybe_diagnostic is not None:
                self.diagnostics.append(maybe_diagnostic)

    def loc_to_pos(self, loc):
        return Position(pp.lineno(loc, self.liststr) - 1, pp.col(loc, self.liststr) - 1)

    def loc_to_range(self, loc):
        return Range(self.loc_to_pos(loc), self.loc_to_pos(loc + 1))


class RedundantAssignment(DiagnosticVisitor):
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


class ModernizeLowercaseCommands(DiagnosticVisitor):
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
    diagnostics = []

    for visitor_class in [RedundantAssignment, ModernizeLowercaseCommands, ModernizePreferTargetCmds]:
        visitor = visitor_class(liststr)
        ast[0].visit(visitor)
        diagnostics.extend(visitor.diagnostics)

    return diagnostics
