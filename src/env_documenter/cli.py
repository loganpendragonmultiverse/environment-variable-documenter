from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from . import __version__
from .render import render_example, render_json, render_markdown
from .scanner import scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="env-documenter",
        description="Inventory environment-variable names without reading real .env values.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--markdown", type=Path, help="Write a Markdown inventory")
    parser.add_argument("--example", type=Path, help="Write a redacted .env.example")
    parser.add_argument("--json", dest="json_path", type=Path, help="Write stable JSON")
    parser.add_argument(
        "--exclude", action="append", default=[], help="Additional directory name to skip"
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--fail-on",
        choices=["never", "undocumented", "dynamic", "either"],
        default="never",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = scan(args.root, args.exclude)
        outputs = [
            (args.markdown, render_markdown(report)),
            (args.example, render_example(report)),
            (args.json_path, render_json(report)),
        ]
        for destination, content in outputs:
            if destination:
                _write_explicit(destination, content, overwrite=args.overwrite)
        summary = report.to_dict()["summary"]
        print(
            f"Variables: {summary['variables']} | Undocumented: {summary['undocumented']} | "
            f"Unused examples: {summary['unused_examples']} | "
            f"Dynamic: {summary['dynamic_accesses']}"
        )
        if not any(destination for destination, _ in outputs):
            print(render_markdown(report))
        should_fail = (
            args.fail_on in {"undocumented", "either"} and bool(report.undocumented)
        ) or (args.fail_on in {"dynamic", "either"} and bool(report.dynamic_accesses))
        return 1 if should_fail else 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _write_explicit(destination: Path, content: str, *, overwrite: bool) -> None:
    path = destination.expanduser().resolve()
    if path.exists() and not overwrite:
        raise ValueError(f"Output exists (use --overwrite): {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
