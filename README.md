# Environment Variable Documenter

Environment Variable Documenter is a read-only command-line tool that finds environment-variable names in common source-code patterns, reconciles them with redacted dotenv templates, and generates Markdown, JSON, or a safe `.env.example`.

It inventories names and source locations. It deliberately does **not** read real `.env` values.

**Release status:** 1.0.0, feature-complete initial CLI release.

## Three-minute start

Download and install the wheel from the [v1.0.0 release](https://github.com/loganpendragonmultiverse/environment-variable-documenter/releases/tag/v1.0.0):

```console
python -m pip install "environment-variable-documenter @ https://github.com/loganpendragonmultiverse/environment-variable-documenter/releases/download/v1.0.0/environment_variable_documenter-1.0.0-py3-none-any.whl"
env-documenter . --markdown environment-variables.md --example .env.example --json environment-variables.json
```

Existing outputs are preserved unless `--overwrite` is supplied.

## Detected source patterns

- Python: `os.environ[...]`, `os.environ.get(...)`, and `os.getenv(...)`.
- JavaScript and TypeScript: `process.env.NAME`, bracket access with literal names, and `import.meta.env.NAME`.
- PHP: `env(...)`, `getenv(...)`, `$_ENV[...]`, and `$_SERVER[...]`.
- Shell: uppercase `$NAME` and `${NAME...}` references, excluding common shell built-ins.
- Dotenv templates: `.env.example`, `.env.sample`, `.env.template`, `example.env`, and environment-specific example variants.

Dynamic lookups such as `os.getenv(variable)` are reported as review items without inventing a variable name.

## Safety behavior

- Real `.env`, `.env.local`, `.env.production`, and similar value-bearing files are skipped before reading.
- Values to the right of assignments in example templates are ignored; reports contain names and declaration paths only.
- Generated examples use blank values and mark names that appear sensitive.
- Dependency, VCS, build, coverage, cache, virtual-environment, and vendor directories are skipped.
- Files larger than 1 MB and unreadable/non-UTF-8 source files are skipped.
- Writes occur only for explicitly requested output paths and use a temporary file before replacement.

## Commands and exit codes

```console
env-documenter PATH [--markdown FILE] [--example FILE] [--json FILE]
                    [--exclude DIRECTORY] [--overwrite]
                    [--fail-on never|undocumented|dynamic|either]
```

Without output flags, the Markdown inventory is printed. Exit code `1` represents the selected policy finding, `2` represents an operational error, and `0` means the scan completed without a configured failure.

## Limitations

- Static patterns cannot resolve names assembled at runtime.
- Aliased imports, framework wrappers, indirect configuration objects, container manifests, and every language syntax are not covered in 1.0.0.
- Shell detection is intentionally limited to uppercase names and can still report application-local shell variables.
- “Sensitive” is a name-based warning, not proof of content or exposure.
- The tool does not verify which variables are actually set in a deployment.

## Privacy

Processing is local. There are no network calls, analytics, accounts, or telemetry. Reports can reveal project structure and configuration names, so review them before publishing.

## Development

```console
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
mypy src tests
pytest --cov
python -m build
```

See [DEVELOPMENT.md](DEVELOPMENT.md), [detection policy](docs/DETECTION-POLICY.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License. Copyright 2026 Logan Pendragon Multiverse.

## More open-source projects

This project is part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Browse the catalog for other released tools, source repositories, live demos, and downloads.
