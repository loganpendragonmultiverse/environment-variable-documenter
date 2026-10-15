# Changelog

## 1.1.0 - Unreleased

- Recognize direct Python os/getenv/environ aliases using syntax trees, conservatively reject shadowed bindings, and retain value-free dynamic review items.
- Preserve default CLI policy and source safety boundaries; add regression tests and documented limits.

## [1.0.0] - 2026-07-21

- Added read-only environment-variable scanning for Python, JavaScript/TypeScript, PHP, shell, and dotenv templates.
- Added documented, undocumented, unused-example, sensitive-name, and dynamic-access classifications.
- Added redacted `.env.example`, Markdown, and stable JSON output.
- Added explicit overwrite protection, directory exclusions, size limits, automated tests, CI, CodeQL, and release packaging.

[1.0.0]: https://github.com/loganpendragonmultiverse/environment-variable-documenter/releases/tag/v1.0.0

