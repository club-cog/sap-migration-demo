# Devin Fleet Upgrade Cost Estimate: 3,918 Servers

> Estimated ACUs and USD for Devin to assist an upgrade program across 3,918 servers, broken down by VM/software type.
> Companion files: `vm-upgrade-cost-estimate.csv` (per-type table, both scenarios) and `vm_upgrade_cost_model.py` (the model; edit the `ASSUMPTIONS` block and re-run to regenerate every table below).

```
python vm_upgrade_cost_model.py --csv vm-upgrade-cost-estimate.csv
```

---

## Headline

Cost projections use $1.667/ACU.

| Scenario | Total ACUs | USD @ $1.667 | Human review hours |
|---|---:|---:|---:|
| **Mid** | **197,534** | **$329,290** | **2,929** |
| High | 634,797 | $1,058,207 | 5,858 |

Mid scenario: about 6,800 Devin sessions, 50 ACUs per server, 20 servers upgraded per 1,000 ACUs.

Three server types make up 50% of the fleet and 41% of mid-scenario ACUs: RHEL7 (1,566 servers), Windows 2016 (1,102), and JWS v5 (405). Any change to the OS-tier or middleware-tier assumptions moves the total more than every other input combined. The Pega tier is 4.5% of servers but 26% of ACUs because each Pega upgrade needs several long sessions.

---

## Formula

For each server type and each scenario (mid / high):

```
ACUs = server_count x sessions_per_server x ACUs_per_session x retry_overhead
USD  = ACUs x 1.667
```

Human review hours are tracked separately (`server_count x review_hours_per_server`) and are not billed in ACUs.

---

## Complexity tiers

| Tier | Server types in tier | Servers | Typical Devin work |
|---|---|---:|---|
| OS upgrade | RHEL6, RHEL7, Windows 2012, Windows 2016 | 2,702 | Pre-flight inventory, package/feature compatibility checks, upgrade runbook, config drift fixes, post-upgrade smoke tests. Highly repeatable once a playbook exists. |
| App server / middleware | JWS v5, JBOSS EAP v7.x, Confluent Kafka, MQ Mod, WAS Liberty v21.x, WAS7 | 854 | Config migration, deprecated API and descriptor changes, connector/client library bumps, deployment script updates, integration test runs. |
| Database | SQL2016, SQL2017, Oracle12c | 186 | Compatibility-level analysis, deprecated feature scans, T-SQL/PL-SQL fixes, job and linked-server updates, backup/restore rehearsal scripts. |
| Pega platform | Pega v7.x, v8.8, v23.1, v24.1, v24.2 | 176 | Rule and ruleset analysis, guardrail warnings, deprecated API replacement, custom Java step rewrites, regression harness. Longest sessions, most human checkpoints. |

### Per-tier assumptions (mid / high)

| Tier | Sessions per server | ACUs per session | `dim_sessions` size band (mid) | Review hours per server |
|---|---|---|---|---|
| OS upgrade | 1.0 / 2.0 | 16 / 30 | M-L | 0.5 / 1.0 |
| App server / middleware | 2.0 / 3.0 | 30 / 50 | L-XL | 1.0 / 2.0 |
| Database | 3.0 / 5.0 | 50 / 80 | XL | 2.0 / 4.0 |
| Pega platform | 4.0 / 6.0 | 60 / 100 | XL | 2.0 / 4.0 |

Retry overhead multiplier: 1.20 / 1.35.

---

## ACU benchmarks: source and status

The per-session ACU values above were intended to be derived from Cognition's historical consumption data:

- `usacognition/analytics`, `dbt/analytics_dbt/models/marts/finance/consumption_by_devin.sql`: `total_acus` per `devin_id`, the per-session ACU distribution.
- `usacognition/analytics`, `dbt/analytics_dbt/models/marts/sessions/dim_sessions.sql`: session-size tiers (XS / S / M / L / XL) with their ACU thresholds.

**Status: live data was not available when this estimate was built.** The `usacognition/analytics` repository returned 403 for this session's git credentials and the Redshift MCP server was not attached. The ACU-per-session values are therefore explicit assumptions. They are set at 2x the first-draft values as a deliberate conservative buffer, and sit inside the size band named in the table above. When query access is available, replace them with:

```sql
-- per-tier calibration query (pseudo; adjust table/column names to the dbt marts)
select size_tier,
       percentile_cont(0.5) within group (order by total_acus) as p50_acus,
       percentile_cont(0.8) within group (order by total_acus) as p80_acus,
       count(*)                                                 as sessions
from analytics.dim_sessions s
join analytics.consumption_by_devin c using (devin_id)
where s.created_at >= dateadd(day, -90, current_date)
  and s.is_internal = false
group by 1;
```

Use p50 for the mid case and p80 for the high case, then paste the values into `TIERS` in `vm_upgrade_cost_model.py`. The "Session Data Analysis" knowledge note says the session-features dataset only covers July 1, 2026 onward, so restrict any calibration window accordingly.

Pricing: $1.667/ACU is the rate used for these projections. For reference, list rates in the Ops/BizOps sources-of-truth doc (`usacognition/playground`, `docs/onboarding/resources/ops-bizops-sources-of-truth.md`) are $1.25/ACU Standard Enterprise and $2.50/ACU Dedicated Enterprise; effective per-customer rates live in the ERP.

---

## Cost by tier

| Tier | Servers | ACUs mid | ACUs high | USD mid | USD high | Share of mid ACUs |
|---|---:|---:|---:|---:|---:|---:|
| OS upgrade | 2,702 | 51,878 | 218,862 | $86,481 | $364,843 | 26.3% |
| App server / middleware | 854 | 61,488 | 172,935 | $102,500 | $288,283 | 31.1% |
| Database | 186 | 33,480 | 100,440 | $55,811 | $167,433 | 16.9% |
| Pega platform | 176 | 50,688 | 142,560 | $84,497 | $237,648 | 25.7% |
| **Grand total** | **3,918** | **197,534** | **634,797** | **$329,290** | **$1,058,207** | **100%** |

---

## Cost by server type

| Server type | Tier | Servers | ACUs mid | ACUs high | USD mid | USD high | Share of mid ACUs |
|---|---|---:|---:|---:|---:|---:|---:|
| RHEL7 | OS upgrade | 1,566 | 30,067 | 126,846 | $50,122 | $211,452 | 15.2% |
| Windows 2016 | OS upgrade | 1,102 | 21,158 | 89,262 | $35,271 | $148,800 | 10.7% |
| Windows 2012 | OS upgrade | 22 | 422 | 1,782 | $704 | $2,971 | 0.2% |
| RHEL6 | OS upgrade | 12 | 230 | 972 | $384 | $1,620 | 0.1% |
| **Subtotal: OS upgrade** | | **2,702** | **51,878** | **218,862** | **$86,481** | **$364,843** | **26.3%** |
| JWS v5 | App server / middleware | 405 | 29,160 | 82,012 | $48,610 | $136,715 | 14.8% |
| JBOSS EAP v7.x | App server / middleware | 230 | 16,560 | 46,575 | $27,606 | $77,641 | 8.4% |
| Confluent Kafka | App server / middleware | 147 | 10,584 | 29,768 | $17,644 | $49,622 | 5.4% |
| MQ Mod | App server / middleware | 47 | 3,384 | 9,518 | $5,641 | $15,866 | 1.7% |
| WAS Liberty v21.x | App server / middleware | 20 | 1,440 | 4,050 | $2,400 | $6,751 | 0.7% |
| WAS7 | App server / middleware | 5 | 360 | 1,013 | $600 | $1,688 | 0.2% |
| **Subtotal: App server / middleware** | | **854** | **61,488** | **172,935** | **$102,500** | **$288,283** | **31.1%** |
| SQL2016 | Database | 120 | 21,600 | 64,800 | $36,007 | $108,022 | 10.9% |
| SQL2017 | Database | 48 | 8,640 | 25,920 | $14,403 | $43,209 | 4.4% |
| Oracle12c | Database | 18 | 3,240 | 9,720 | $5,401 | $16,203 | 1.6% |
| **Subtotal: Database** | | **186** | **33,480** | **100,440** | **$55,811** | **$167,433** | **16.9%** |
| Pega v24.1 | Pega platform | 63 | 18,144 | 51,030 | $30,246 | $85,067 | 9.2% |
| Pega v8.8 | Pega platform | 60 | 17,280 | 48,600 | $28,806 | $81,016 | 8.7% |
| Pega v24.2 | Pega platform | 33 | 9,504 | 26,730 | $15,843 | $44,559 | 4.8% |
| Pega v7.x | Pega platform | 13 | 3,744 | 10,530 | $6,241 | $17,554 | 1.9% |
| Pega v23.1 | Pega platform | 7 | 2,016 | 5,670 | $3,361 | $9,452 | 1.0% |
| **Subtotal: Pega platform** | | **176** | **50,688** | **142,560** | **$84,497** | **$237,648** | **25.7%** |
| **Grand total** | | **3,918** | **197,534** | **634,797** | **$329,290** | **$1,058,207** | **100%** |

---

## Sensitivity: what moves the total

Mid scenario, $1.667/ACU, one input changed at a time:

| Change | Effect on total ACUs | Effect on USD |
|---|---:|---:|
| OS tier ACUs/session 16 -> 24 | +25,939 (+13%) | +$43,241 |
| OS tier sessions/server 1.0 -> 0.5 (batch playbook) | -25,939 (-13%) | -$43,241 |
| Middleware tier ACUs/session 30 -> 40 | +20,496 (+10%) | +$34,167 |
| Pega tier sessions/server 4 -> 6 | +25,344 (+13%) | +$42,248 |
| Retry overhead 1.20 -> 1.10 | -16,461 (-8%) | -$27,441 |
| Price $1.667 -> $1.25 | 0 | -$82,372 (-25%) |

The OS-tier assumptions and the effective price per ACU are the two levers worth measuring or negotiating first. Everything else is second-order.

---

## Assumptions

All values live in the `ASSUMPTIONS` block of `vm_upgrade_cost_model.py`.

1. **Sessions per server.** One Devin session is one unit of delegated work ending in a reviewable artifact (PR, runbook, test report). OS mid case assumes one session per server; Pega high case assumes six sessions per server (analysis, rule fixes, Java rewrites, regression, two rounds of rework).
2. **ACUs per session.** Assumed, not measured, and doubled from the first-draft values as a conservative buffer. Positioned inside the `dim_sessions` size bands named per tier. See "ACU benchmarks" for the calibration query.
3. **Retry overhead.** 20% / 35% of session spend is re-work (failed runs, rejected PRs, re-runs after environment fixes). Applied as a multiplier on ACUs, not on session count for the review-hours line.
4. **Human review effort.** Hours an engineer spends prompting, reviewing, and approving Devin's output per server. Not billed as ACUs; shown so the estimate can be compared with a fully manual program. Does not include change-window execution, CAB approvals, or application-owner UAT.
5. **Scope of Devin's work.** Devin does analysis, code and config changes, scripts, tests, and documentation. Devin does not execute the production cutover itself; that stays with the platform team and existing change process.
6. **No environment blockers priced in.** Network allowlists, credentials, and access to test environments are assumed available. Each blocker typically costs one wasted session.
7. **Inventory as given.** 3,918 servers from "Count of Server Name." Grouped by the software named; a server running both an OS due for upgrade and a middleware product is counted once, in the row the inventory placed it.
8. **Price per ACU.** $1.667 for all projections. Change `PRICE_PER_ACU` in the model to re-price.
9. **Learning curve not modelled.** The first 5-10% of each tier will run closer to the high case while playbooks are built; the remainder trends below mid. The mid case is a program-wide average.

---

## Measurement framing (Measuring a Devin Pilot)

Track the program with the same metrics the pilot-measurement playbook uses (`usacognition/playground`, `docs/onboarding/resources/measuring-devin-pilot.md`), so results can be compared with other Devin deployments:

| Metric | Definition here | Mid-scenario target |
|---|---|---:|
| Sessions | Devin sessions started, including retries | 6,806 |
| PRs / artifacts created | One reviewable artifact per successful session | ~5,670 (sessions / 1.20) |
| ACUs consumed | Total | 197,534 |
| ACU efficiency | ACUs per server upgraded | 50.4 |
| Servers per 1K ACUs | Analog of "PRs per 1K ACUs" | 19.8 |
| Success rate | Sessions producing an accepted artifact / total sessions | 83% (1 / 1.20) |
| Review hours per 1K ACUs | Human effort intensity | 14.8 |

ROI framing: compare mid-scenario $329,290 plus 2,929 review hours against the fully manual estimate for the same 3,918 servers. Per the playbook, present productivity gains as measured outcomes (servers upgraded, artifacts produced, ACU efficiency) rather than as a cost comparison alone, filter internal Cognition sessions from any pilot data, and use working days for throughput baselines.

Recommended checkpoint: after the first 100 servers in each tier, re-run the calibration query, replace the assumed ACUs/session with measured p50/p80, and re-issue this estimate.
