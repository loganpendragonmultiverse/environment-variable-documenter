import os
from pathlib import Path
from typing import Any

import pytest

from env_documenter.cli import main
from env_documenter.scanner import scan


def test_real_dotenv_and_symlink_template_are_never_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = tmp_path / ".env"
    secret.write_text("PRIVATE_NAME=synthetic-value")
    link = tmp_path / ".env.example"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    original = Path.open

    def checked(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path in {secret, link}:
            raise AssertionError("dotenv value read attempted")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    report = scan(tmp_path)
    assert report.variables == {} and report.files_skipped == 2


def test_selected_symlink_root_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "source"
    target.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="symlink"):
        scan(link)


@pytest.mark.parametrize(
    "filename,source",
    [
        ("app.js", "process.env[ 'PUBLIC_NAME' ]"),
        ("app.php", "<?php env( 'PUBLIC_NAME' ); getenv(  \"OTHER_NAME\");"),
    ],
)
def test_literal_whitespace_is_not_dynamic(tmp_path: Path, filename: str, source: str) -> None:
    (tmp_path / filename).write_text(source)
    report = scan(tmp_path)
    assert "PUBLIC_NAME" in report.variables
    assert report.dynamic_accesses == []


@pytest.mark.parametrize("filename", ["app.py", ".env", ".env.production"])
def test_output_cannot_replace_source_or_real_dotenv(tmp_path: Path, filename: str) -> None:
    output = tmp_path / filename
    output.write_text("original bytes")
    assert main([str(tmp_path), "--markdown", str(output), "--overwrite"]) == 2
    assert output.read_text() == "original bytes"


def test_output_preflight_prevents_partial_files(tmp_path: Path) -> None:
    first = tmp_path / "new.md"
    existing = tmp_path / "old.json"
    existing.write_text("keep")
    assert main([str(tmp_path), "--markdown", str(first), "--json", str(existing)]) == 2
    assert not first.exists() and existing.read_text() == "keep"
    assert main([str(tmp_path), "--markdown", str(first), "--json", str(first)]) == 2
    assert not first.exists()


def test_output_creation_race_is_no_clobber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "report.md"
    original = os.link

    def racing(source: Path, destination: Path) -> None:
        destination.write_text("other writer")
        original(source, destination)

    monkeypatch.setattr(os, "link", racing)
    assert main([str(tmp_path), "--markdown", str(output)]) == 2
    assert output.read_text() == "other writer"
    assert not list(tmp_path.glob(".report.md.*"))


def test_dangling_output_symlink_is_refused_even_with_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    target = tmp_path / "absent"
    try:
        output.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    assert main([str(tmp_path), "--markdown", str(output), "--overwrite"]) == 2
    assert output.is_symlink() and not target.exists()
