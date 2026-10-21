# Finding: collateral_margin_call truncates weekend margin calls

**Human decision needed.** On Saturday/Sunday runs the legacy model truncates the call amount
instead of rounding half-up. The Python port rounds half-up every day. 3 of 28 reference cases
differ; they are `xfail` in `tests/parity/known_deviations.py`. Reference outputs were not edited.

> All fictional: Exemplar Bank, CSAs and counterparties are invented.

## Affected cases

| Case | As-of | Day | Fixing used | CSA | Rounding unit | Call type | Raw amount | Legacy (truncated) | Python (half-up) | Difference |
|---|---|---|---|---|---|---|---|---|---|---|
| MC-006 | 2024-03-30 | Sat | 2024-03-29 | CSA-0101 | 10,000 | DELIVERY | 516,974.80 | 510,000 | 520,000 | 10,000 |
| MC-012 | 2024-04-28 | Sun | 2024-04-26 | CSA-0207 | 100,000 | DELIVERY | 1,269,821.70 | 1,200,000 | 1,300,000 | 100,000 |
| MC-023 | 2024-06-15 | Sat | 2024-06-14 | CSA-0311 | 50,000 | RETURN | 1,088,250.84 | 1,050,000 | 1,100,000 | 50,000 |

All other fields (fixing date, exposure, required, held, raw diff, call type) match exactly.
All 25 weekday cases match exactly.

## Root cause

`legacy/models/collateral_margin_call.quill`:

- L62-64: if `DATE.DOW(as_of) >= 6` the model leaves the normal path and calls `wknd_call`.
- L49-57: `wknd_call` rolls back to the prior Friday fixing (`DATE.ROLL(as_of, "P")`, L52), which is
  correct per COLL-OPS-04 2.3, but then rounds with `rnd.to_unit_v1` (L55).
- L67: the weekday path rounds with `rnd.to_unit`.

`legacy/models/lib/rounding.quill`:

- L21-26 `to_unit`: `ROUND(x / unit, 0) * unit` (half-up). This is the documented rule.
- L28-34 `to_unit_v1`: `TRUNC(x / unit, 0) * unit` (always rounds down), labelled "eod batch v1
  (pre-2012 CSA engine)". The weekend path was "kept from eod batch v1 (rkessler 2011)" (L50)
  and was never switched when the weekday path moved to `to_unit` in 2012.

So the same CSA, same fixing, gives a different call amount depending on whether the batch runs
on Friday or Saturday. That is not a business rule anywhere in the code comments or the CSA terms.

## Impact

- Triggers only on weekend as-of dates (here 3 of 28 cases) and only when the amount is not
  already a whole multiple of the rounding unit.
- Error is always toward zero, up to one rounding unit (10k to 100k per call here).
- DELIVERY calls are under-called: Exemplar Bank asks for less collateral than it is owed
  (more unsecured exposure). RETURN calls are under-returned: the counterparty gets back less than
  it is owed (likely dispute).

## Options

**Option A: replicate legacy.** Port `to_unit_v1` and use it on weekends so parity is 100%.
Pros: zero change for downstream reports. Cons: knowingly keeps an inconsistent rule in the new
system; must be documented as intended behavior and signed off by the model owner.

**Option B: fix and restate (implemented in this PR).** Half-up on every day. Pros: one rule,
matches the documented rounding policy (`rounding.quill` L4, L20). Cons: weekend calls change by
up to one rounding unit; past weekend calls may need review with Collateral Ops; downstream
reconciliations that compare to the legacy batch must expect the 3 differences.

## Recommendation

Option B, with sign-off from the collateral model owner and Collateral Ops, and a one-off review
of historical weekend calls. If Option A is chosen instead, remove the 3 xfails and port
`to_unit_v1` explicitly with a comment pointing here.
