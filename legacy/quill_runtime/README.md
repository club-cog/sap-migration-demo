# quill_runtime

Emulates the legacy RiskDB engine so reference outputs can be regenerated for this demo.

> All fictional. "Quill" and "RiskDB" are invented for this demo repo; Exemplar Bank is not a real bank.

A small tree-walking interpreter for the Quill risk DSL, written in plain Python (no third-party deps).

| File | What it does |
|---|---|
| `lexer.py` | Tokens, keywords, `;;` comments, newline-terminated statements |
| `parser.py` | Recursive-descent parser (grammar in the module docstring) |
| `ast.py` | AST node dataclasses |
| `interpreter.py` | Evaluator: modules (`use`), read-only `cell`s, `defn`, records, 1-indexed lists |
| `builtins.py` | `ROUND`/`TRUNC`/`MIN`/`MAX`/..., `DATE.*`, `BUSDAYS`, `TABLE.LOAD/LOOKUP/WHERE/ROWS` |
| `run_all.py` | Runs every `legacy/models/<model>.quill` over `legacy/data/cases/<model>.csv` |
| `__main__.py` | Run a single case: `python -m legacy.quill_runtime lcr_outflows LCR-002` |

## Semantics that matter for a port

- Numbers are `decimal.Decimal` (default context, 28 significant digits). Never floats.
- `ROUND(x, n)` is half-up (ties away from zero). `TRUNC(x, n)` drops digits toward zero.
- Lists are **1-indexed**. `xs[0]` is an error.
- Calendar is weekends only. `DATE.DOW` is ISO (Mon=1 .. Sun=7). `DATE.ROLL(d, "F"|"P"|"MF"|"MP")`.
  `BUSDAYS(d1, d2)` counts business days in `(d1, d2]`.
- `TABLE.LOAD` types CSV cells: number, `YYYY-MM-DD` date, empty = `nil`, else string.
- `TABLE.LOOKUP(tbl, col, k1, k2, ...)` matches keys against the leading columns in file order,
  `*` in the table is a wildcard, first match wins, a miss returns `nil`.
- Output formatting (reference CSVs): `nil` -> empty, booleans `true`/`false`, numbers normalized
  (`1.50` -> `1.5`), dates ISO.

## Commands

```bash
python -m legacy.quill_runtime.run_all            # regenerate legacy/reference_outputs/*.csv
python -m legacy.quill_runtime.run_all --check    # byte-for-byte check vs committed files
legacy/run_all.sh --check                         # same, from anywhere
pytest tests/runtime                              # interpreter tests
```
