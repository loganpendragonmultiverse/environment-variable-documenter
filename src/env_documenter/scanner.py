from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from .models import Occurrence, ScanReport, VariableRecord

MAX_FILE_BYTES = 1_000_000
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".venv",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "vendor",
        "venv",
    }
)
SUPPORTED_EXTENSIONS = frozenset(
    {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".php", ".sh", ".bash"}
)
SHELL_BUILT_INS = frozenset(
    {
        "BASH",
        "HOME",
        "HOSTNAME",
        "IFS",
        "OLDPWD",
        "PATH",
        "PPID",
        "PWD",
        "RANDOM",
        "SHELL",
        "SHLVL",
        "UID",
        "USER",
    }
)
SENSITIVE_WORDS = (
    "API_KEY",
    "AUTH",
    "CERT",
    "CREDENTIAL",
    "PRIVATE",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
)

PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "python": [
        ("os.environ", re.compile(r"\bos\.environ\s*\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\]")),
        ("os.environ.get", re.compile(r"\bos\.environ\.get\s*\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]")),
        ("os.getenv", re.compile(r"\bos\.getenv\s*\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]")),
    ],
    "javascript": [
        ("process.env", re.compile(r"\bprocess\.env\.([A-Z][A-Z0-9_]*)\b")),
        ("process.env[]", re.compile(r"\bprocess\.env\s*\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\]")),
        ("import.meta.env", re.compile(r"\bimport\.meta\.env\.([A-Z][A-Z0-9_]*)\b")),
    ],
    "php": [
        ("env", re.compile(r"\benv\s*\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]")),
        ("getenv", re.compile(r"\bgetenv\s*\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]")),
        ("$_ENV", re.compile(r"\$_ENV\s*\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\]")),
        ("$_SERVER", re.compile(r"\$_SERVER\s*\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\]")),
    ],
    "shell": [
        ("shell", re.compile(r"(?<!\\)\$(?:\{([A-Z][A-Z0-9_]*)[^}]*\}|([A-Z][A-Z0-9_]*))")),
    ],
}

DYNAMIC_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "python": [
        (
            "dynamic Python function access",
            re.compile(r"\bos\.(?:getenv|environ\.get)\s*\(\s*(?!['\"])"),
        ),
        (
            "dynamic Python mapping access",
            re.compile(r"\bos\.environ\s*\[\s*(?!['\"])"),
        ),
    ],
    "javascript": [
        (
            "dynamic JavaScript mapping access",
            re.compile(r"\bprocess\.env\s*\[\s*(?!['\"])"),
        )
    ],
    "php": [
        ("dynamic PHP env access", re.compile(r"\benv\s*\(\s*(?!['\"])")),
        ("dynamic PHP getenv access", re.compile(r"\bgetenv\s*\(\s*(?!['\"])")),
    ],
}

DOTENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=")


def scan(root: Path, extra_excludes: Iterable[str] = ()) -> ScanReport:
    scan_root = root.expanduser().resolve()
    if not scan_root.is_dir():
        raise ValueError(f"Scan root is not a directory: {scan_root}")
    exclusions = EXCLUDED_DIRECTORIES | frozenset(extra_excludes)
    records: dict[str, VariableRecord] = {}
    dynamic: list[Occurrence] = []
    files_scanned = 0
    files_skipped = 0

    for path in sorted(scan_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(scan_root)
        if any(part in exclusions for part in relative.parts[:-1]):
            files_skipped += 1
            continue
        if _is_real_dotenv(path.name):
            files_skipped += 1
            continue
        template = _is_dotenv_template(path.name)
        language = _language(path)
        if not template and language is None:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            files_skipped += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            files_skipped += 1
            continue
        files_scanned += 1
        relative_text = relative.as_posix()
        if template:
            _read_template(text, relative_text, records)
        if language:
            _read_source(text, relative_text, language, records, dynamic)

    return ScanReport(scan_root, records, files_scanned, files_skipped, dynamic)


def _read_template(text: str, path: str, records: dict[str, VariableRecord]) -> None:
    for line in text.splitlines():
        match = DOTENV_LINE.match(line)
        if match:
            record = _record(records, match.group(1))
            if path not in record.declared_in_examples:
                record.declared_in_examples.append(path)


def _read_source(
    text: str,
    path: str,
    language: str,
    records: dict[str, VariableRecord],
    dynamic: list[Occurrence],
) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for syntax, pattern in PATTERNS[language]:
            for match in pattern.finditer(line):
                name = next((value for value in match.groups() if value), "")
                if not name or (language == "shell" and name in SHELL_BUILT_INS):
                    continue
                occurrence = Occurrence(path, line_number, syntax)
                record = _record(records, name)
                if occurrence not in record.occurrences:
                    record.occurrences.append(occurrence)
        for syntax, pattern in DYNAMIC_PATTERNS.get(language, []):
            if pattern.search(line):
                occurrence = Occurrence(path, line_number, syntax)
                if occurrence not in dynamic:
                    dynamic.append(occurrence)


def _record(records: dict[str, VariableRecord], name: str) -> VariableRecord:
    if name not in records:
        records[name] = VariableRecord(
            name=name,
            sensitive=any(word in name for word in SENSITIVE_WORDS),
        )
    return records[name]


def _language(path: Path) -> str | None:
    if path.suffix == ".py":
        return "python"
    if path.suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
        return "javascript"
    if path.suffix == ".php":
        return "php"
    if path.suffix in {".sh", ".bash"}:
        return "shell"
    return None


def _is_dotenv_template(name: str) -> bool:
    lowered = name.lower()
    standard_names = {
        ".env.example",
        ".env.sample",
        ".env.template",
        "example.env",
    }
    environment_variant = lowered.startswith(".env.") and lowered.endswith(
        (".example", ".sample", ".template")
    )
    return lowered in standard_names or environment_variant


def _is_real_dotenv(name: str) -> bool:
    lowered = name.lower()
    return lowered == ".env" or (lowered.startswith(".env.") and not _is_dotenv_template(name))
