"""Conservative lexical recognition of Python environment access; never imports code."""

from __future__ import annotations

import ast
import re

from .models import Occurrence, VariableRecord

Binding = tuple[str, int]
VARIABLE_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


class _Bindings(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: dict[str, list[Binding | None]] = {}
        self.conditional = False

    def bind(self, name: str, value: Binding | None = None) -> None:
        self.names.setdefault(name, []).append(value)

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            name = item.asname or item.name.split(".")[0]
            self.bind(
                name, ("os", node.lineno) if item.name == "os" and not self.conditional else None
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for item in node.names:
            if item.name == "*":
                # A star import can replace any visible alias.
                self.bind("*")
            else:
                known = (
                    not self.conditional
                    and node.level == 0
                    and node.module == "os"
                    and item.name in {"environ", "getenv"}
                )
                self.bind(item.asname or item.name, (item.name, node.lineno) if known else None)

    def _conditional(self, node: ast.AST) -> None:
        previous = self.conditional
        self.conditional = True
        self.generic_visit(node)
        self.conditional = previous

    visit_If = _conditional
    visit_For = _conditional
    visit_AsyncFor = _conditional
    visit_While = _conditional
    visit_Try = _conditional
    visit_TryStar = _conditional
    visit_With = _conditional
    visit_AsyncWith = _conditional
    visit_Match = _conditional

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bind(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            value: ast.expr = node
            while isinstance(value, ast.Attribute):
                value = value.value
            if isinstance(value, ast.Name):
                self.bind(value.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bind(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.bind(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bind(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        pass

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self.bind(name)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            self.bind(name)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.bind(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.bind(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.bind(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.bind(node.rest)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._comprehension(node)

    def _comprehension(self, node: ast.AST) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.NamedExpr):
                self.visit(child.target)


def _scope(
    body: list[ast.stmt], inherited: dict[str, Binding], arguments: ast.arguments | None = None
) -> dict[str, Binding]:
    collector = _Bindings()
    for statement in body:
        collector.visit(statement)
    if arguments:
        for arg in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
            collector.bind(arg.arg)
        for optional_arg in (arguments.vararg, arguments.kwarg):
            if optional_arg:
                collector.bind(optional_arg.arg)
    if "*" in collector.names:
        return {}
    aliases = dict(inherited)
    for name, bindings in collector.names.items():
        aliases.pop(name, None)
        if len(bindings) == 1 and bindings[0] is not None:
            aliases[name] = bindings[0]
    return aliases


class _Accesses(ast.NodeVisitor):
    def __init__(
        self,
        path: str,
        records: dict[str, VariableRecord],
        dynamic: list[Occurrence],
        aliases: dict[str, Binding],
        lexical_aliases: dict[str, Binding] | None = None,
    ) -> None:
        self.path = path
        self.records = records
        self.dynamic = dynamic
        self.aliases = aliases
        self.lexical_aliases = aliases if lexical_aliases is None else lexical_aliases

    def _kind(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            binding = self.aliases.get(node.id)
            return binding[0] if binding and node.lineno >= binding[1] else None
        if isinstance(node, ast.Attribute):
            parent = self._kind(node.value)
            if parent == "os" and node.attr in {"getenv", "environ"}:
                return node.attr
            if parent == "environ" and node.attr == "get":
                return "environ.get"
        return None

    def _access(self, node: ast.expr | None, line: int, syntax: str, mapping: bool = False) -> None:
        from .scanner import _record

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if VARIABLE_NAME.fullmatch(node.value):
                occurrence = Occurrence(self.path, line, syntax)
                record = _record(self.records, node.value)
                if occurrence not in record.occurrences:
                    record.occurrences.append(occurrence)
        else:
            description = (
                "dynamic Python mapping access" if mapping else "dynamic Python function access"
            )
            occurrence = Occurrence(self.path, line, description)
            if occurrence not in self.dynamic:
                self.dynamic.append(occurrence)

    def visit_Call(self, node: ast.Call) -> None:
        kind = self._kind(node.func)
        if kind in {"getenv", "environ.get"}:
            self._access(node.args[0] if node.args else None, node.lineno, "os." + kind)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._kind(node.value) == "environ":
            self._access(node.slice, node.lineno, "os.environ", mapping=True)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for expression in [
            *node.decorator_list,
            *node.args.defaults,
            *[item for item in node.args.kw_defaults if item],
        ]:
            self.visit(expression)
        aliases = _scope(node.body, self.lexical_aliases, node.args)
        child = _Accesses(self.path, self.records, self.dynamic, aliases)
        for statement in node.body:
            child.visit(statement)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        for expression in [
            *node.decorator_list,
            *node.args.defaults,
            *[item for item in node.args.kw_defaults if item],
        ]:
            self.visit(expression)
        child = _Accesses(
            self.path,
            self.records,
            self.dynamic,
            _scope(node.body, self.lexical_aliases, node.args),
        )
        for statement in node.body:
            child.visit(statement)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for expression in [*node.args.defaults, *[item for item in node.args.kw_defaults if item]]:
            self.visit(expression)
        aliases = _scope([ast.Expr(value=node.body)], self.lexical_aliases, node.args)
        _Accesses(self.path, self.records, self.dynamic, aliases).visit(node.body)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for expression in [
            *node.decorator_list,
            *node.bases,
            *[item.value for item in node.keywords],
        ]:
            self.visit(expression)
        # Definition-time expressions use the class namespace. Function/lambda
        # bodies and nested class bodies do not close over that namespace.
        child = _Accesses(
            self.path,
            self.records,
            self.dynamic,
            _scope(node.body, self.lexical_aliases),
            self.lexical_aliases,
        )
        for statement in node.body:
            child.visit(statement)

    def _comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        aliases = dict(self.lexical_aliases)
        for generator in node.generators:
            for item in ast.walk(generator.target):
                if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store):
                    aliases.pop(item.id, None)
        child = _Accesses(self.path, self.records, self.dynamic, aliases)
        # Python evaluates the first iterable in the surrounding namespace;
        # the remaining comprehension runs in its own lexical scope.
        self.visit(node.generators[0].iter)
        for index, generator in enumerate(node.generators):
            if index:
                child.visit(generator.iter)
            for condition in generator.ifs:
                child.visit(condition)
        if isinstance(node, ast.DictComp):
            child.visit(node.key)
            child.visit(node.value)
        else:
            child.visit(node.elt)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._comprehension(node)


def read_python(
    text: str, path: str, records: dict[str, VariableRecord], dynamic: list[Occurrence]
) -> None:
    staged_records: dict[str, VariableRecord] = {}
    staged_dynamic: list[Occurrence] = []
    try:
        tree = ast.parse(text)
        aliases = _scope(tree.body, {"os": ("os", 0)})
        visitor = _Accesses(path, staged_records, staged_dynamic, aliases)
        visitor.visit(tree)
    except (SyntaxError, ValueError, RecursionError):
        dynamic.append(
            Occurrence(
                path,
                1,
                "unparsed Python source (syntax unsupported, invalid, or too deeply nested)",
            )
        )
        return
    for name, record in staged_records.items():
        existing = records.setdefault(name, record)
        for occurrence in record.occurrences:
            if occurrence not in existing.occurrences:
                existing.occurrences.append(occurrence)
    for occurrence in staged_dynamic:
        if occurrence not in dynamic:
            dynamic.append(occurrence)
