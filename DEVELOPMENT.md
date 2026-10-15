# Development handoff

Version 1.0.0 is a read-only, name-only configuration inventory. The defining security rule is that value-bearing `.env` files are excluded before file reads. Example-template values are ignored rather than copied into reports.

The initial language surface is Python, JavaScript/TypeScript, PHP, and shell plus dotenv templates. Expand it only with narrow syntax patterns, realistic fixtures, dynamic-access behavior, and false-positive tests.

## Verification

```console
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
mypy src tests
pytest --cov --cov-report=term-missing
python -m build
python -m pip_audit
```

Do not add automatic reads of real dotenv files, secret values, deployment credentials, or network services.


## 1.1.0 candidate

Recognize direct Python os/getenv/environ aliases using syntax trees, conservatively reject shadowed bindings, and retain value-free dynamic review items.

Run the existing project gates before review. This source candidate is not published.
