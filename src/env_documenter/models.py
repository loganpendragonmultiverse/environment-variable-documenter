from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import __version__


@dataclass(frozen=True, order=True)
class Occurrence:
    path: str
    line: int
    syntax: str


@dataclass
class VariableRecord:
    name: str
    occurrences: list[Occurrence] = field(default_factory=list)
    declared_in_examples: list[str] = field(default_factory=list)
    sensitive: bool = False

    @property
    def status(self) -> str:
        if self.occurrences and self.declared_in_examples:
            return "documented"
        if self.occurrences:
            return "undocumented"
        return "unused-example"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "sensitive": self.sensitive,
            "occurrences": [asdict(item) for item in sorted(self.occurrences)],
            "declared_in_examples": sorted(self.declared_in_examples),
        }


@dataclass
class ScanReport:
    root: Path
    variables: dict[str, VariableRecord]
    files_scanned: int
    files_skipped: int
    dynamic_accesses: list[Occurrence] = field(default_factory=list)

    @property
    def undocumented(self) -> list[str]:
        return sorted(
            name for name, item in self.variables.items() if item.status == "undocumented"
        )

    @property
    def unused_examples(self) -> list[str]:
        return sorted(
            name for name, item in self.variables.items() if item.status == "unused-example"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool_version": __version__,
            "root": str(self.root),
            "summary": {
                "variables": len(self.variables),
                "undocumented": len(self.undocumented),
                "unused_examples": len(self.unused_examples),
                "dynamic_accesses": len(self.dynamic_accesses),
                "files_scanned": self.files_scanned,
                "files_skipped": self.files_skipped,
            },
            "variables": [self.variables[name].to_dict() for name in sorted(self.variables)],
            "dynamic_accesses": [asdict(item) for item in sorted(self.dynamic_accesses)],
        }
