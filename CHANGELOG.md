# Changelog

## 1.1.2 - 2026-10-20

- Avoid symlink scan reads and enforce the source size limit while reading.
- Preflight distinct outputs and refuse source, dotenv and symlink destinations.
- Publish new reports without clobbering competing files; retain explicit regular-report overwrite.
- Avoid spurious dynamic JavaScript/PHP findings for whitespace before literal keys.

## 1.1.1 - 2026-10-15

- Correct current README release status and wheel-install links after the Python alias detection release.

## 1.1.0 - 2026-10-15

- Recognize direct Python os/getenv/environ aliases using syntax trees, conservatively reject shadowed bindings, and retain value-free dynamic review items.
- Preserve default CLI policy and source safety boundaries; add regression tests and documented limits.

## [1.0.0] - 2026-07-21

- Added read-only environment-variable scanning for Python, JavaScript/TypeScript, PHP, shell, and dotenv templates.
- Added documented, undocumented, unused-example, sensitive-name, and dynamic-access classifications.
- Added redacted `.env.example`, Markdown, and stable JSON output.
- Added explicit overwrite protection, directory exclusions, size limits, automated tests, CI, CodeQL, and release packaging.

[1.0.0]: https://github.com/loganpendragonmultiverse/environment-variable-documenter/releases/tag/v1.0.0

