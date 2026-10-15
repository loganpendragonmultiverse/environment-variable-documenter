# Detection policy

Environment Variable Documenter favors explainable literal-name detection over language-complete parsing. Every occurrence records a relative file path, line number, and syntax family without retaining the surrounding source line.

## Source versus documentation

A variable is `documented` when it has both a supported source occurrence and an example-template declaration. A source-only name is `undocumented`. A template-only name is `unused-example`; it may be obsolete or may support code outside the scanner's syntax surface.

Dynamic accesses are separate findings because the name cannot be proven statically.

## Value exclusion

Files matching real dotenv conventions are skipped before `read_text`. In templates, only a valid uppercase assignment name before `=` is retained. The right-hand side never enters the report model.

## Extending detection

New patterns need positive, negative, multiline, quoting, dynamic-name, alias, generated-directory, file-size, and value-redaction tests. Avoid broad patterns that interpret ordinary uppercase identifiers as environment variables.


## Python aliases (1.1.0 source candidate)

Python source is parsed with the standard-library syntax tree; scanned modules
are never imported or executed. These direct imports are recognized:

```python
import os as platform_os
from os import getenv as setting, environ as settings

platform_os.getenv("API_KEY")
platform_os.environ["DATABASE_URL"]
setting("REGION")
settings.get("PORT")
```

Literal uppercase names and source locations are retained; default values and
surrounding source text are not. Dynamic keys remain review items. Comments and
ordinary string examples are not treated as Python accesses. Existing unimported
`os.getenv` / `os.environ` recognition is retained when `os` is not shadowed.

Recognition is deliberately conservative: assignments, parameters, deletion,
attribute replacement, competing imports, star imports and conditional imports
can make a binding ambiguous. Such aliases are not guessed, even if a particular
runtime path would work. Function scopes and class-method lexical lookup are
handled separately. Assignment-derived aliases, arbitrary wrappers, monkeypatching
and runtime import resolution remain outside scope. Invalid or interpreter-newer
Python syntax produces a value-free review item instead of falling back to regex
matches. Use an interpreter that supports the scanned source's syntax.

Real dotenv files and excluded directories remain filtered **before** source
reads. Template assignment values remain excluded from the report model.
