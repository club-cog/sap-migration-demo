# Migration report: Quill to Python

> All fictional (Exemplar Bank, Quill, RiskDB).

All 10 legacy Quill models are migrated to `risk_models/`. Each has unit tests and is checked case by
case against `legacy/reference_outputs/` (numeric abs tolerance `1e-9` as `Decimal`; text, dates
and booleans exact). Reference outputs were not modified; `legacy/run_all.sh --check` passes.

**9 of 10 models: 100% parity. 1 model needs a human decision (3 weekend cases).**

| # | Model | Cases | Parity | Status | Notes |
|---|---|---|---|---|---|
| 1 | `hqla_haircut` | 18 | 18/18 (100%) | Ready for review | Foreign non-AAA sovereign downgrade and L2 caps covered by unit tests |
| 2 | `lcr_outflows` | 30 | 30/30 (100%) | Ready for review | Imports the `hqla_haircut` port for the HQLA stock and the stress haircut |
| 3 | `nsfr` | 18 | 18/18 (100%) | Ready for review | Uses `common.daycount` buckets |
| 4 | `frtb_ir_delta` | 18 | 18/18 (100%) | Ready for review | Correlation scenarios LOW/MED/HIGH, tie order kept |
| 5 | `hist_var` | 27 | 27/27 (100%) | Ready for review | Includes 3 INSUFFICIENT-history cases |
| 6 | `expected_shortfall` | 21 | 21/21 (100%) | Ready for review | Imports the `hist_var` port; fixed 2023 stress window |
| 7 | `saccr_addon` | 20 | 20/20 (100%) | Ready for review | IR + FX only, as in legacy |
| 8 | `cva_simple` | 24 | 24/24 (100%) | Ready for review | EM uplift applies to proxy spreads only |
| 9 | `stress_shock` | 36 | 36/36 (100%) | Ready for review | HY multiplier, -100% floor |
| 10 | `collateral_margin_call` | 28 | 25/28 (89%), 3 xfail | **Human decision needed** | Legacy truncates weekend calls instead of rounding half-up. See `docs/findings/collateral_margin_call.md` |
| | **Total** | **240** | **237 match, 3 xfail, 0 fail** | | |

## Dependency order used

```
common (rounding, daycount, stats, data)   ports of legacy/models/lib, in place before migration
  -> hqla_haircut -> lcr_outflows
  -> hist_var     -> expected_shortfall
  -> nsfr, frtb_ir_delta, saccr_addon, cva_simple, stress_shock, collateral_margin_call
```

## How to verify

```bash
pip install -r requirements.txt
legacy/run_all.sh --check     # reference outputs reproduce from Quill byte for byte
pytest -v                     # exits 0; 3 xfailed (collateral_margin_call MC-006, MC-012, MC-023)
```

## Open decision

`collateral_margin_call`: Option A (replicate legacy truncation on weekends) or Option B (half-up
every day, restate weekend calls). The port implements B. Details, root cause with Quill line
numbers, and impact are in `docs/findings/collateral_margin_call.md`.
