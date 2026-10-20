from pathlib import Path

from env_documenter.scanner import scan


def test_shipped_examples_are_documented_name_only_inputs() -> None:
    root = Path(__file__).parents[1] / "examples"
    report = scan(root)
    assert set(report.variables) == {"APP_REGION", "API_KEY", "DB_HOST"}
    assert all(record.status == "documented" for record in report.variables.values())
    assert not report.dynamic_accesses
