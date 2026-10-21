# AGENTS.md: working in this repo

All content is fictional (Exemplar Bank, Quill, RiskDB). Keep it that way: no real bank names,
people or code in anything you write.

## What this repo is

Legacy Quill risk models (`legacy/models/`) being migrated to Python (`risk_models/`).
The Quill code and its generated reference outputs are the source of truth.

## Setup

```bash
pip install -r requirements.txt      # pytest only; Python 3.10+
```

## Commands

| Task | Command |
|---|---|
| Run one legacy case | `python -m legacy.quill_runtime <model> <case_id>` |
| Regenerate reference outputs | `legacy/run_all.sh` (only when Quill or data changed on purpose) |
| Check outputs reproduce | `legacy/run_all.sh --check` |
| Interpreter tests | `pytest tests/runtime` |
| Parity for one model | `pytest tests/parity -k <model> -v` |
| Everything | `pytest -v` |

## Rules

1. **Never edit `legacy/reference_outputs/`** and never edit `legacy/models/` or `legacy/data/`
   as part of a migration. If parity fails, the port is wrong or the legacy is wrong; either way
   the reference stays.
2. One model per PR: `risk_models/<model>.py` + `tests/unit/test_<model>.py`.
3. Ports expose `run(case: Mapping[str, str]) -> dict` (keys = reference output columns) and a
   typed `compute(...)` function. Use `Decimal` everywhere, never `float`.
4. Rounding, day counts and tail statistics come from `risk_models/common/` (ports of
   `legacy/models/lib/`). Do not re-implement them inside a model. Changing `common/` needs its
   own PR and a full parity run.
5. Quill lists are 1-indexed; Python is 0-indexed. Check every index.
6. Module docstring: a table mapping each business rule to the Quill line numbers it came from.
7. If a legacy behavior looks like a bug: implement the correct behavior, xfail only the affected
   cases in `tests/parity/known_deviations.py` with a reason, write `docs/findings/<model>.md`,
   and put **Human decision needed** at the top of the PR. Do not copy the bug silently.
8. Dependencies matter: `lcr_outflows` uses `hqla_haircut`; `expected_shortfall` uses `hist_var`.
   Port the dependency first or import its Python port.

Full procedure: `docs/playbook-quill-to-python.md`.
