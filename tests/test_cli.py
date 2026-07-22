from pathlib import Path

from env_documenter.cli import main


def test_cli_writes_explicit_outputs(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "project"
    source.mkdir()
    (source / "app.py").write_text('import os\nos.getenv("API_KEY")\n', encoding="utf-8")
    markdown = tmp_path / "report.md"
    example = tmp_path / ".env.example"
    json_path = tmp_path / "report.json"
    result = main(
        [
            str(source),
            "--markdown",
            str(markdown),
            "--example",
            str(example),
            "--json",
            str(json_path),
        ]
    )
    assert result == 0
    assert markdown.is_file() and example.is_file() and json_path.is_file()
    assert "Variables: 1" in capsys.readouterr().out


def test_cli_refuses_overwrite_then_allows_it(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    output = tmp_path / "report.md"
    output.write_text("keep", encoding="utf-8")
    assert main([str(tmp_path), "--markdown", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "keep"
    assert "use --overwrite" in capsys.readouterr().err
    assert main([str(tmp_path), "--markdown", str(output), "--overwrite"]) == 0


def test_cli_failure_policies_and_stdout(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text(
        'os.getenv("MISSING_DOC")\nos.getenv(name)\n', encoding="utf-8"
    )
    assert main([str(tmp_path), "--fail-on", "undocumented"]) == 1
    assert main([str(tmp_path), "--fail-on", "dynamic"]) == 1
    assert main([str(tmp_path), "--fail-on", "either"]) == 1
    output = capsys.readouterr().out
    assert "# Environment variable inventory" in output
