# Devin Fleet Upgrade Cost Estimate: 3,918 Servers

> Estimated ACUs and USD for Devin to assist an upgrade program across 3,918 servers, broken down by VM/software type.
> Companion files: `vm-upgrade-cost-estimate.csv` (per-type table, all scenarios and prices) and `vm_upgrade_cost_model.py` (the model; edit the `ASSUMPTIONS` block and re-run to regenerate every table below).

```
python vm_upgrade_cost_model.py --csv vm-upgrade-cost-estimate.csv
```

---

## Headline

| Scenario | Total ACUs | USD @ $1.25 (Standard) | USD @ $2.00 (analytics default) | USD @ $2.50 (Dedicated) | Human review hours |
|---|---:|---:|---:|---:|---:|
| Low | 25,406 | $31,757 | $50,811 | $63,514 | 1,464 |
| **Mid** | **98,767** | **$123,459** | **$197,534** | **$246,918** | **2,929** |
| High | 317,398 | $396,748 | $634,797 | $793,496 | 5,858 |

Mid scenario: about 6,800 Devin sessions, 25 ACUs per server, 40 servers upgraded per 1,000 ACUs.

Three server types make up 50% of the fleet and 41% of mid-scenario ACUs: RHEL7 (1,566 servers), Windows 2016 (1,102), and JWS v5 (405). Any change to the OS-tier or middleware-tier assumptions moves the total more than every other input combined. The Pega tier is 4.5% of servers but 26% of ACUs because each Pega upgrade needs several long sessions.

---

## Formula

For each server type and each scenario (low / mid / high):

```
ACUs = server_count x sessions_per_server x ACUs_per_session x retry_overhead
USD  = ACUs x price_per_ACU
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

### Per-tier assumptions (low / mid / high)

| Tier | Sessions per server | ACUs per session | `dim_sessions` size band (mid) | Review hours per server |
|---|---|---|---|---|
| OS upgrade | 0.5 / 1.0 / 2.0 | 4 / 8 / 15 | S-M | 0.25 / 0.5 / 1.0 |
| App server / middleware | 1.0 / 2.0 / 3.0 | 8 / 15 / 25 | M-L | 0.5 / 1.0 / 2.0 |
| Database | 2.0 / 3.0 / 5.0 | 15 / 25 / 40 | L | 1.0 / 2.0 / 4.0 |
| Pega platform | 2.0 / 4.0 / 6.0 | 15 / 30 / 50 | L-XL | 1.0 / 2.0 / 4.0 |

Retry overhead multiplier: 1.10 / 1.20 / 1.35.

Sessions per server below 1.0 (OS low case) means one session handles a batch of servers of the same image, which is the realistic pattern once a per-OS playbook exists.

---

## ACU benchmarks: source and status

The per-session ACU values above were intended to be derived from Cognition's historical consumption data:

- `usacognition/analytics`, `dbt/analytics_dbt/models/marts/finance/consumption_by_devin.sql`: `total_acus` per `devin_id`, the per-session ACU distribution.
- `usacognition/analytics`, `dbt/analytics_dbt/models/marts/sessions/dim_sessions.sql`: session-size tiers (XS / S / M / L / XL) with their ACU thresholds.

**Status: live data was not available when this estimate was built.** The `usacognition/analytics` repository returned 403 for this session's git credentials and the Redshift MCP server was not attached. The ACU-per-session values are therefore explicit assumptions, chosen to sit inside the size band named in the table above. When query access is available, replace them with:

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

Pricing sources: $1.25/ACU Standard Enterprise and $2.50/ACU Dedicated Enterprise are the list rates in the Ops/BizOps sources-of-truth doc (`usacognition/playground`, `docs/onboarding/resources/ops-bizops-sources-of-truth.md`). $2.00/ACU is the default rate used in analytics reporting. Effective per-customer rates live in the ERP and are usually lower than list.

---

## Cost by tier at each price

Mid scenario ACUs per tier, with USD at each rate. Per-type rows for all three scenarios and all three prices are in the CSV.

| Tier | Servers | ACUs low | ACUs mid | ACUs high | Mid USD @ $1.25 | Mid USD @ $2.00 | Mid USD @ $2.50 | Share of mid ACUs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OS upgrade | 2,702 | 5,944 | 25,939 | 109,431 | $32,424 | $51,878 | $64,848 | 26.3% |
| App server / middleware | 854 | 7,515 | 30,744 | 86,468 | $38,430 | $61,488 | $76,860 | 31.1% |
| Database | 186 | 6,138 | 16,740 | 50,220 | $20,925 | $33,480 | $41,850 | 16.9% |
| Pega platform | 176 | 5,808 | 25,344 | 71,280 | $31,680 | $50,688 | $63,360 | 25.7% |
| **Grand total** | **3,918** | **25,406** | **98,767** | **317,398** | **$123,459** | **$197,534** | **$246,918** | **100%** |

---

## Cost by server type (ACUs, and USD at $2.00/ACU)

| Server type | Tier | Servers | ACUs low | ACUs mid | ACUs high | USD low | USD mid | USD high | Share of mid ACUs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RHEL7 | OS upgrade | 1,566 | 3,445 | 15,034 | 63,423 | $6,890 | $30,067 | $126,846 | 15.2% |
| Windows 2016 | OS upgrade | 1,102 | 2,424 | 10,579 | 44,631 | $4,849 | $21,158 | $89,262 | 10.7% |
| Windows 2012 | OS upgrade | 22 | 48 | 211 | 891 | $97 | $422 | $1,782 | 0.2% |
| RHEL6 | OS upgrade | 12 | 26 | 115 | 486 | $53 | $230 | $972 | 0.1% |
| **Subtotal: OS upgrade** | | **2,702** | **5,944** | **25,939** | **109,431** | **$11,889** | **$51,878** | **$218,862** | **26.3%** |
| JWS v5 | App server / middleware | 405 | 3,564 | 14,580 | 41,006 | $7,128 | $29,160 | $82,012 | 14.8% |
| JBOSS EAP v7.x | App server / middleware | 230 | 2,024 | 8,280 | 23,288 | $4,048 | $16,560 | $46,575 | 8.4% |
| Confluent Kafka | App server / middleware | 147 | 1,294 | 5,292 | 14,884 | $2,587 | $10,584 | $29,768 | 5.4% |
| MQ Mod | App server / middleware | 47 | 414 | 1,692 | 4,759 | $827 | $3,384 | $9,518 | 1.7% |
| WAS Liberty v21.x | App server / middleware | 20 | 176 | 720 | 2,025 | $352 | $1,440 | $4,050 | 0.7% |
| WAS7 | App server / middleware | 5 | 44 | 180 | 506 | $88 | $360 | $1,013 | 0.2% |
| **Subtotal: App server / middleware** | | **854** | **7,515** | **30,744** | **86,468** | **$15,030** | **$61,488** | **$172,935** | **31.1%** |
| SQL2016 | Database | 120 | 3,960 | 10,800 | 32,400 | $7,920 | $21,600 | $64,800 | 10.9% |
| SQL2017 | Database | 48 | 1,584 | 4,320 | 12,960 | $3,168 | $8,640 | $25,920 | 4.4% |
| Oracle12c | Database | 18 | 594 | 1,620 | 4,860 | $1,188 | $3,240 | $9,720 | 1.6% |
| **Subtotal: Database** | | **186** | **6,138** | **16,740** | **50,220** | **$12,276** | **$33,480** | **$100,440** | **16.9%** |
| Pega v24.1 | Pega platform | 63 | 2,079 | 9,072 | 25,515 | $4,158 | $18,144 | $51,030 | 9.2% |
| Pega v8.8 | Pega platform | 60 | 1,980 | 8,640 | 24,300 | $3,960 | $17,280 | $48,600 | 8.7% |
| Pega v24.2 | Pega platform | 33 | 1,089 | 4,752 | 13,365 | $2,178 | $9,504 | $26,730 | 4.8% |
| Pega v7.x | Pega platform | 13 | 429 | 1,872 | 5,265 | $858 | $3,744 | $10,530 | 1.9% |
| Pega v23.1 | Pega platform | 7 | 231 | 1,008 | 2,835 | $462 | $2,016 | $5,670 | 1.0% |
| **Subtotal: Pega platform** | | **176** | **5,808** | **25,344** | **71,280** | **$11,616** | **$50,688** | **$142,560** | **25.7%** |
| **Grand total** | | **3,918** | **25,406** | **98,767** | **317,398** | **$50,811** | **$197,534** | **$634,797** | **100%** |

Multiply the USD columns by 0.625 for $1.25/ACU and by 1.25 for $2.50/ACU.

---

## Sensitivity: what moves the total

Mid scenario, $2.00/ACU, one input changed at a time:

| Change | Effect on total ACUs | Effect on USD |
|---|---:|---:|
| OS tier ACUs/session 8 -> 12 | +12,970 (+13%) | +$25,939 |
| OS tier sessions/server 1.0 -> 0.5 (batch playbook) | -12,970 (-13%) | -$25,939 |
| Middleware tier ACUs/session 15 -> 20 | +10,248 (+10%) | +$20,496 |
| Pega tier sessions/server 4 -> 6 | +12,672 (+13%) | +$25,344 |
| Retry overhead 1.20 -> 1.10 | -8,231 (-8%) | -$16,461 |
| Price $2.00 -> $1.25 | 0 | -$74,075 (-37.5%) |

Price per ACU and the OS-tier assumptions are the two levers worth negotiating or measuring first. Everything else is second-order.

---

## Assumptions

All values live in the `ASSUMPTIONS` block of `vm_upgrade_cost_model.py`.

1. **Sessions per server.** One Devin session is one unit of delegated work ending in a reviewable artifact (PR, runbook, test report). OS low case assumes a per-image playbook handles two servers per session; Pega high case assumes six sessions per server (analysis, rule fixes, Java rewrites, regression, two rounds of rework).
2. **ACUs per session.** Assumed, not measured. Positioned inside the `dim_sessions` size bands named per tier. See "ACU benchmarks" for the calibration query.
3. **Retry overhead.** 10% / 20% / 35% of session spend is re-work (failed runs, rejected PRs, re-runs after environment fixes). Applied as a multiplier on ACUs, not on session count for the review-hours line.
4. **Human review effort.** Hours an engineer spends prompting, reviewing, and approving Devin's output per server. Not billed as ACUs; shown so the estimate can be compared with a fully manual program. Does not include change-window execution, CAB approvals, or application-owner UAT.
5. **Scope of Devin's work.** Devin does analysis, code and config changes, scripts, tests, and documentation. Devin does not execute the production cutover itself; that stays with the platform team and existing change process.
6. **No environment blockers priced in.** Network allowlists, credentials, and access to test environments are assumed available. Each blocker typically costs one wasted session.
7. **Inventory as given.** 3,918 servers from "Count of Server Name." Grouped by the software named; a server running both an OS due for upgrade and a middleware product is counted once, in the row the inventory placed it.
8. **Price per ACU.** List rates. Effective negotiated rate should replace $2.00 before this goes to a customer.
9. **Learning curve not modelled.** The first 5-10% of each tier will run closer to the high case while playbooks are built; the remainder trends toward low. The mid case is a program-wide average.

---

## Measurement framing (Measuring a Devin Pilot)

Track the program with the same metrics the pilot-measurement playbook uses (`usacognition/playground`, `docs/onboarding/resources/measuring-devin-pilot.md`), so results can be compared with other Devin deployments:

| Metric | Definition here | Mid-scenario target |
|---|---|---:|
| Sessions | Devin sessions started, including retries | 6,806 |
| PRs / artifacts created | One reviewable artifact per successful session | ~5,670 (sessions / 1.20) |
| ACUs consumed | Total | 98,767 |
| ACU efficiency | ACUs per server upgraded | 25.2 |
| Servers per 1K ACUs | Analog of "PRs per 1K ACUs" | 39.7 |
| Success rate | Sessions producing an accepted artifact / total sessions | 83% (1 / 1.20) |
| Review hours per 1K ACUs | Human effort intensity | 29.7 |

ROI framing: compare mid-scenario USD plus 2,929 review hours against the fully manual estimate for the same 3,918 servers. Per the playbook, present productivity gains as measured outcomes (servers upgraded, artifacts produced, ACU efficiency) rather than as a cost comparison alone, filter internal Cognition sessions from any pilot data, and use working days for throughput baselines.

Recommended checkpoint: after the first 100 servers in each tier, re-run the calibration query, replace the assumed ACUs/session with measured p50/p80, and re-issue this estimate.
