# Development handoff

Version 1.1.0 is a read-only, name-only configuration inventory. The defining security rule is that value-bearing `.env` files are excluded before file reads. Example-template values are ignored rather than copied into reports.

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


## 1.1.0 Python alias handling

Recognize direct Python os/getenv/environ aliases using syntax trees, conservatively reject shadowed bindings, and retain value-free dynamic review items.

Validation: 45 regression tests pass on supported Python versions, with Ruff, strict types, package builds, dependency audit and the complete GitHub platform/CodeQL matrix. Independent review found no actionable findings. Keep the value-free dynamic review behavior and conservative shadowing boundaries; no real dotenv reads are added.
