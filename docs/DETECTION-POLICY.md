# Detection policy

Environment Variable Documenter favors explainable literal-name detection over language-complete parsing. Every occurrence records a relative file path, line number, and syntax family without retaining the surrounding source line.

## Source versus documentation

A variable is `documented` when it has both a supported source occurrence and an example-template declaration. A source-only name is `undocumented`. A template-only name is `unused-example`; it may be obsolete or may support code outside the scanner's syntax surface.

Dynamic accesses are separate findings because the name cannot be proven statically.

## Value exclusion

Files matching real dotenv conventions are skipped before `read_text`. In templates, only a valid uppercase assignment name before `=` is retained. The right-hand side never enters the report model.

## Extending detection

New patterns need positive, negative, multiline, quoting, dynamic-name, alias, generated-directory, file-size, and value-redaction tests. Avoid broad patterns that interpret ordinary uppercase identifiers as environment variables.

