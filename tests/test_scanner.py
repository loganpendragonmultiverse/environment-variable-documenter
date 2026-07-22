from pathlib import Path

import pytest

from env_documenter.scanner import scan


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scans_supported_languages_and_reconciles_examples(tmp_path: Path) -> None:
    write(
        tmp_path / "app.py",
        'import os\nurl = os.environ["DATABASE_URL"]\n'
        'key = os.getenv("API_KEY")\nport = os.environ.get("PORT", "3000")\n',
    )
    write(
        tmp_path / "web.ts",
        "const a = process.env.API_KEY; const b = process.env['PUBLIC_URL']; "
        "const c = import.meta.env.VITE_MODE;\n",
    )
    write(
        tmp_path / "app.php",
        "<?php $a = env('DATABASE_URL'); $b = getenv(\"MAIL_HOST\"); "
        "$c = $_ENV['API_KEY']; $d = $_SERVER['SERVER_NAME'];\n",
    )
    write(tmp_path / "start.sh", 'echo "$DEPLOY_REGION ${WORKER_COUNT:-2} $HOME"\n')
    write(
        tmp_path / ".env.example",
        "DATABASE_URL=secret-should-not-be-read\nAPI_KEY=also-hidden\nOLD_SETTING=1\n",
    )
    report = scan(tmp_path)

    assert report.variables["DATABASE_URL"].status == "documented"
    assert report.variables["API_KEY"].sensitive
    assert report.variables["OLD_SETTING"].status == "unused-example"
    assert "PUBLIC_URL" in report.undocumented
    assert "HOME" not in report.variables
    assert report.files_scanned == 5


def test_never_reads_real_dotenv_files(tmp_path: Path) -> None:
    (tmp_path / ".env").write_bytes(b"REAL_SECRET=do-not-read\xff")
    write(tmp_path / ".env.production", "OTHER_SECRET=do-not-read")
    write(tmp_path / "app.py", 'import os\nos.getenv("PUBLIC_NAME")\n')
    report = scan(tmp_path)
    assert set(report.variables) == {"PUBLIC_NAME"}
    assert report.files_skipped == 2


def test_finds_dynamic_accesses_without_inventing_names(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "os.getenv(variable)\nos.environ[key]\n")
    write(tmp_path / "app.js", "process.env[name]\n")
    write(tmp_path / "app.php", "<?php env($name); getenv($other);\n")
    report = scan(tmp_path)
    assert len(report.dynamic_accesses) == 5
    assert report.variables == {}


def test_skips_dependencies_large_files_and_custom_excludes(tmp_path: Path) -> None:
    write(tmp_path / "node_modules" / "package.js", "process.env.DEPENDENCY_SECRET")
    write(tmp_path / "generated" / "file.py", 'os.getenv("GENERATED")')
    large = tmp_path / "large.py"
    large.write_bytes(b"#" * 1_000_001)
    report = scan(tmp_path, ["generated"])
    assert report.variables == {}
    assert report.files_skipped == 3


def test_ignores_unsupported_files(tmp_path: Path) -> None:
    write(tmp_path / "notes.md", "process.env.NOT_CODE")
    write(tmp_path / "data.txt", "$NOT_SHELL")
    report = scan(tmp_path)
    assert report.files_scanned == 0


def test_rejects_missing_scan_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a directory"):
        scan(tmp_path / "missing")


def test_accepts_template_name_variants(tmp_path: Path) -> None:
    write(tmp_path / ".env.sample", "ONE=\n")
    write(tmp_path / ".env.production.example", "TWO=\n")
    write(tmp_path / "example.env", "THREE=\n")
    report = scan(tmp_path)
    assert set(report.variables) == {"ONE", "TWO", "THREE"}
