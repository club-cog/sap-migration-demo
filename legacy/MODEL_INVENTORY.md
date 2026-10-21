# Legacy model inventory (Quill / RiskDB)

> All fictional: Exemplar Bank, its people and its models are invented for this demo.

| # | Model | Purpose | Depends on | Original author | Last changed | Owner status |
|---|---|---|---|---|---|---|
| 1 | `hqla_haircut.quill` | HQLA stock after haircuts by asset class + rating, Level 2 caps | `lib/rounding` | rkessler (2009) | 2014 (dpatel) | Author left 2016; dpatel moved to Treasury IT |
| 2 | `lcr_outflows.quill` | LCR: 30-day stressed outflows, inflow cap, stress haircut on HQLA | `hqla_haircut`, `lib/rounding` | rkessler (2010) | 2014 (dpatel) | Author left 2016; no named owner |
| 3 | `nsfr.quill` | Net stable funding ratio (ASF / RSF by maturity bucket) | `lib/daycount`, `lib/rounding` | mfournier (2013) | 2015 (mfournier) | Author on another team, "best effort" support |
| 4 | `frtb_ir_delta.quill` | FRTB-style interest-rate delta capital with correlation scenarios | `lib/rounding` | aokafor (2016) | 2016 (aokafor) | Author left 2019 |
| 5 | `hist_var.quill` | 1d / 10d historical-simulation VaR | `lib/stats`, `lib/rounding` | tnakamura (2011) | 2014 (tnakamura) | Author retired 2018 |
| 6 | `expected_shortfall.quill` | 97.5% ES, current vs fixed stress window | `hist_var`, `lib/stats`, `lib/rounding` | tnakamura (2014) | 2016 (aokafor) | No owner since 2019 |
| 7 | `saccr_addon.quill` | Counterparty exposure add-on, PFE multiplier, EAD (IR + FX) | `lib/daycount`, `lib/rounding` | lbaptiste (2015) | 2016 (lbaptiste) | Author in Model Risk now, reviews only |
| 8 | `cva_simple.quill` | Simplified unilateral CVA on an EE profile | `lib/rounding` | sliang (2012) | 2015 (lbaptiste) | Author left 2017 |
| 9 | `stress_shock.quill` | Scenario shocks on trading positions vs book limits | `lib/rounding` | jwong (2010) | 2013 (jwong) | Author left 2015 |
| 10 | `collateral_margin_call.quill` | Daily variation margin call per CSA (threshold, MTA, rounding unit) | `lib/rounding` | rkessler (2011) | 2014 (dpatel) | Author left 2016; ops team runs it, nobody changes it |

Shared libraries (`legacy/models/lib/`):

| Library | Purpose | Author | Last changed | Used by |
|---|---|---|---|---|
| `rounding.quill` | All money/rate rounding (half-up), CSA unit rounding, clamps | rkessler (2009) | 2012 (dpatel) | all 10 models |
| `daycount.quill` | A360 / A365 / 30360 year fractions, maturity buckets | rkessler (2009) | 2013 (mfournier) | `nsfr`, `saccr_addon` |
| `stats.quill` | Historical-simulation quantile and tail mean | tnakamura (2011) | 2014 (tnakamura) | `hist_var`, `expected_shortfall` |

Dependency graph:

```
lib/rounding.quill  <-- every model
hqla_haircut.quill  <-- lcr_outflows.quill
hist_var.quill      <-- expected_shortfall.quill
lib/daycount.quill  <-- nsfr.quill, saccr_addon.quill
lib/stats.quill     <-- hist_var.quill, expected_shortfall.quill
```
