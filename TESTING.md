# Testing

Install `python -m pip install -e ".[dev]"`, then run `ruff format --check .`,
`ruff check .`, `mypy src tests`, `pytest --cov` and `python -m build`. Keep the
existing 90% branch-coverage gate, native platform matrix and dependency audit.

Boundary regressions cover no reads through symlink templates/source roots,
real dotenv and source output protection, duplicate destinations, no-clobber
races, explicit regular-report replacement and whitespace before literal keys.
Test installed wheel/source distributions outside the checkout and inspect the
actual package imports. No real credentials or user files are test fixtures.
