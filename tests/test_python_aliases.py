from pathlib import Path

import pytest

from env_documenter.scanner import scan


def inventory(tmp_path: Path, source: str):  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text(source, encoding="utf-8")
    return scan(tmp_path)


def test_module_and_direct_aliases_with_multiline_literals(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
import os as platform_os
from os import getenv as setting, environ as settings
a = platform_os.getenv(
    "API_KEY", "never-export-this-default"
)
b = platform_os.environ["DATABASE_URL"]
c = settings.get("PORT")
d = settings["REGION"]
e = setting("MODE")
f = setting(variable)
g = settings[key]
h = platform_os.environ.get(other)
""",
    )
    assert set(report.variables) == {"API_KEY", "DATABASE_URL", "PORT", "REGION", "MODE"}
    assert len(report.dynamic_accesses) == 3
    assert report.variables["API_KEY"].occurrences[0].line == 4
    assert "never-export-this-default" not in str(report.to_dict())


def test_comments_strings_and_unrelated_names_are_not_evidence(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
# os.getenv("COMMENT")
text = 'os.environ["STRING"]'
def getenv(name):
    return name
getenv("UNRELATED")
from another_module import getenv as setting
setting("OTHER_MODULE")
""",
    )
    assert not report.variables and not report.dynamic_accesses


@pytest.mark.parametrize(
    "source",
    [
        'import os as x\nx = object()\nx.getenv("HIDDEN")',
        'from os import getenv as x\ndef f(x):\n    return x("HIDDEN")',
        'import os as x\ndef f():\n    x.getenv("HIDDEN")\n    x = object()',
        'import os as x\ndef x():\n    pass\nx.getenv("HIDDEN")',
        'import os as x\nx.getenv = lambda name: None\nx.getenv("HIDDEN")',
        'import os as x\ndel x\nx.getenv("HIDDEN")',
        'import os as x\n[x.getenv("HIDDEN") for x in others]',
        'import os as x\nfn = lambda x: x.getenv("HIDDEN")',
        'import os as x\nfrom unknown import *\nx.getenv("HIDDEN")',
        'if enabled:\n    import os as x\nx.getenv("HIDDEN")',
        'from os import getenv as x\ndef f():\n    global x\n    return x("HIDDEN")',
    ],
)
def test_shadowed_or_ambiguous_aliases_are_not_guessed(tmp_path: Path, source: str) -> None:
    assert not inventory(tmp_path, source).variables


def test_scopes_do_not_leak_and_class_methods_use_outer_aliases(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
import os as outer
def function():
    from os import getenv as local
    return local("LOCAL")
async def worker():
    return outer.getenv("ASYNC")
local("NOT_IN_SCOPE")
class Settings:
    outer = object()
    value = outer.getenv("CLASS_SHADOW")
    def method(self):
        return outer.getenv("METHOD")
outer.getenv("MODULE")
""",
    )
    assert set(report.variables) == {"LOCAL", "ASYNC", "METHOD", "MODULE"}


def test_unimported_os_compatibility_and_dynamic_access(tmp_path: Path) -> None:
    report = inventory(tmp_path, 'os.getenv("PORT")\nos.environ[name]\nos.getenv(dynamic)')
    assert set(report.variables) == {"PORT"}
    assert len(report.dynamic_accesses) == 2


def test_invalid_python_becomes_value_free_review_item(tmp_path: Path) -> None:
    report = inventory(tmp_path, 'os.getenv("SECRET_NAME", private_value=\n')
    assert not report.variables
    assert len(report.dynamic_accesses) == 1
    assert report.dynamic_accesses[0].syntax.startswith("unparsed Python")
    assert "private_value" not in str(report.to_dict())


def test_exclusions_are_enforced_before_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("SECRET=never-read", encoding="utf-8")
    (tmp_path / ".env.production").write_text("SECRET=never-read", encoding="utf-8")
    excluded = tmp_path / "node_modules"
    excluded.mkdir()
    (excluded / "secret.py").write_text('os.getenv("IGNORED")', encoding="utf-8")
    (tmp_path / "app.py").write_text('import os as x\nx.getenv("PUBLIC")', encoding="utf-8")
    original = Path.read_text

    def guarded_read(path: Path, *args: object, **kwargs: object) -> str:
        assert path.name not in {".env", ".env.production", "secret.py"}
        return original(path, encoding="utf-8")

    monkeypatch.setattr(Path, "read_text", guarded_read)
    report = scan(tmp_path)
    assert set(report.variables) == {"PUBLIC"}


def test_alias_names_do_not_transfer_through_assignments(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
import os as original
copy = original
copy.getenv("NOT_RESOLVED")
original.getenv("DIRECT")
""",
    )
    assert set(report.variables) == {"DIRECT"}


def test_defaults_lambdas_and_comprehension_scopes(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
import os as x
def f(a=x.getenv("DEFAULT"), *, b=x.getenv("KEYWORD"), **kwargs):
    return x.getenv("BODY")
fn = lambda a=x.getenv("LAMBDA_DEFAULT"): x.getenv("LAMBDA_BODY")
items = {x.getenv("SET") for item in source}
mapping = {item: x.getenv("DICT") for item in source}
generated = (x.getenv("GENERATOR") for item in source)
x.getenv("lowercase_ignored")
x.getenv()
x.environ.get(variable)
x.environ[another]
""",
    )
    assert set(report.variables) == {
        "DEFAULT",
        "KEYWORD",
        "BODY",
        "LAMBDA_DEFAULT",
        "LAMBDA_BODY",
        "SET",
        "DICT",
        "GENERATOR",
    }
    assert len(report.dynamic_accesses) == 3


@pytest.mark.parametrize(
    "binding",
    [
        "try:\n    action()\nexcept Exception as x:\n    pass",
        "match value:\n    case x:\n        pass",
        "match value:\n    case [*x]:\n        pass",
        "match value:\n    case {**x}:\n        pass",
        "[(x := item) for item in source]",
        "class x:\n    pass",
        "async def x():\n    pass",
    ],
)
def test_binding_forms_are_conservative(tmp_path: Path, binding: str) -> None:
    source = "import os as x\ndef outer():\n"
    source += "\n".join("    " + line for line in binding.splitlines())
    source += '\n    return x.getenv("NOT_PROVEN")\n'
    assert not inventory(tmp_path, source).variables


def test_lambda_local_assignment_and_direct_environment_import(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
from os import environ
import os as x
fn = lambda: ((x := object()), x.getenv("NOT_ENV"))
environ["DIRECT_MAPPING"]
environ.get("DIRECT_GET")
""",
    )
    assert set(report.variables) == {"DIRECT_MAPPING", "DIRECT_GET"}


def test_nonlocal_review_does_not_hide_outer_evidence(tmp_path: Path) -> None:
    report = inventory(
        tmp_path,
        """
def outer():
    import os as x
    def inner():
        nonlocal x
        return x.getenv("NOT_PROVEN")
    return x.getenv("OUTER")
""",
    )
    assert set(report.variables) == {"OUTER"}
