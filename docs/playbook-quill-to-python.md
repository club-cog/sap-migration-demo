# Playbook: migrate one Quill risk model to Python

> Register this file as a Devin playbook. Run it **once per model, one model per session**.
> Input: the model name (e.g. `lcr_outflows`). Repo: this repo. All content is fictional.

## Procedure

<phase name="1. Understand">

1. Read `AGENTS.md` and `legacy/MODEL_INVENTORY.md`.
2. Read `legacy/models/<model>.quill` end to end, then every file it pulls in with `use`
   (`legacy/models/lib/*.quill` and any other model, e.g. `lcr_outflows` uses `hqla_haircut`).
3. Read `legacy/quill_runtime/README.md` for the semantics that bite: Decimal math, half-up
   `ROUND`, 1-indexed lists, `TABLE.LOOKUP` wildcard + first match, weekend-only calendar.
4. Write down (for yourself) every business rule: tables used, thresholds, floors/caps, rounding
   points, day counts, branches on dates or flags. Note the Quill line numbers of each.
5. Run the legacy model on two cases: `python -m legacy.quill_runtime <model> <case_id>`.

<verification>
- [ ] Every `use` dependency read
- [ ] Every business rule listed with Quill line numbers
- [ ] Legacy model runs locally
</verification>
</phase>

<phase name="2. Port and test">

1. Create `risk_models/<model>.py`:
   - idiomatic, typed Python 3.10 (`dataclass` results, type hints), `Decimal` only, no floats;
   - `compute(...)` with typed arguments and `run(case: Mapping[str, str]) -> dict` whose keys
     are the reference output columns;
   - reuse `risk_models/common/` (rounding, daycount, stats, data) and existing ports of
     dependencies; do not duplicate them;
   - module docstring = table **Rule | Quill lines | Python function** covering every rule.
2. Create `tests/unit/test_<model>.py`: at least one test per business rule that has a branch,
   threshold or cap.
3. Run parity: `pytest tests/parity -k <model> -v`, then the full suite `pytest -v`.

<verification>
- [ ] `risk_models/<model>.py` has the rule-to-Quill-line table
- [ ] Unit tests pass
- [ ] Parity run for every case of the model
- [ ] `legacy/run_all.sh --check` still passes (nothing in `legacy/` changed)
</verification>
</phase>

<phase name="3. When parity fails">

First assume the port is wrong: re-read the Quill, check indexing, rounding order and table
lookups. Fix and re-run.

**CRITICAL RULE.** If the remaining differences come from legacy behavior that looks like a bug
(e.g. a branch that rounds differently, a stale date, an inconsistent cap):

1. Do **not** replicate it silently. Implement the correct behavior.
2. **NEVER edit `legacy/reference_outputs/`** (or anything else in `legacy/`).
3. Mark **only** the affected cases as xfail in `tests/parity/known_deviations.py`, with a reason
   that names the root cause and points to the finding.
4. Write `docs/findings/<model>.md`:
   - affected cases (case id, as-of, legacy value, Python value, difference);
   - root cause with Quill file + line numbers;
   - impact (how often it triggers, size, direction);
   - **Option A: replicate legacy** (bit-for-bit, document as known behavior);
   - **Option B: fix and restate** (keep correct behavior, restate affected history, notify owners);
   - recommendation.
5. Flag the PR: first line of the description is `**Human decision needed**` plus one sentence.

<verification>
- [ ] Reference outputs untouched (`git diff --stat legacy/` is empty)
- [ ] Only the affected cases are xfail, each with a reason
- [ ] `docs/findings/<model>.md` has cases, root cause with line numbers, options A and B
</verification>
</phase>

<phase name="4. Open the PR">

One PR per model, branch `migrate/<model>`. Title: `Migrate <model> from Quill to Python`.
Description:

```
[**Human decision needed**: <one sentence>   <- only if there is a finding]

## Parity
| Model | Cases | Match | xfail | Fail | Tolerance |
|---|---|---|---|---|---|
| <model> | N | N | 0 | 0 | abs 1e-9 (Decimal) |

## Business rules
<the rule -> Quill line table from the docstring>

## Dependencies
<Quill files read; Python modules reused>

## Tests
<pytest summary line>
```

<verification>
- [ ] One model in the PR, no changes under `legacy/`
- [ ] Parity table in the description
- [ ] `pytest -v` exits 0
</verification>
</phase>

## Rules

- One model per session and per PR. Never merge: a human approves every PR.
- Never edit reference outputs, Quill models or legacy data.
- Never copy a suspected legacy bug silently; never hide a difference with a looser tolerance.
- Keep everything fictional.
