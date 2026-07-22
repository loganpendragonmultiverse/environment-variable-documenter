from pathlib import Path

from env_documenter.render import render_example, render_json, render_markdown
from env_documenter.scanner import scan


def test_renders_redacted_outputs(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        'import os\nos.getenv("API_SECRET")\nos.getenv("PUBLIC_URL")\n', encoding="utf-8"
    )
    (tmp_path / ".env.example").write_text("PUBLIC_URL=https://private.example\n", encoding="utf-8")
    report = scan(tmp_path)
    example = render_example(report)
    markdown = render_markdown(report)
    json_text = render_json(report)

    assert "https://private.example" not in example + markdown + json_text
    assert "API_SECRET=\n" in example
    assert "Sensitive value" in example
    assert "undocumented" in markdown
    assert '"schema_version": 1' in json_text
    assert "Real `.env` files were excluded" in markdown


def test_markdown_lists_dynamic_accesses(tmp_path: Path) -> None:
    (tmp_path / "app.js").write_text("process.env[name]\n", encoding="utf-8")
    markdown = render_markdown(scan(tmp_path))
    assert "## Dynamic accesses" in markdown
    assert "app.js:1" in markdown
