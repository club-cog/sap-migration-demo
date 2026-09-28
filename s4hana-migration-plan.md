# S/4HANA Migration Plan — Acme Retail Corp (ECC 6.0 → S/4HANA)

> Phased plan for converting the legacy ECC 6.0 system to SAP S/4HANA, grounded in the custom objects
> in [`abap_source/`](abap_source/) and the rewrite pattern already established in
> [`python_target/`](python_target/) and [`tests/`](tests/). Method and scope boundaries follow
> [`migration-playbook.md`](migration-playbook.md), [`pre-migration-checklist.md`](pre-migration-checklist.md)
> and [`README.md`](README.md).

**Strategy in one line:** brownfield system conversion of ECC to S/4HANA, keeping the S/4 core clean
(Clean Core). Custom Z-logic moves out of the ERP into external Python services (playbook Patterns A/B/C),
and whatever ABAP stays behind is fixed to pass ATC.

---

## 1. Current State Assessment

### 1.1 Custom object inventory

| Object | Object type | Integration pattern | Key S/4HANA compatibility issues | Disposition | Python service / tests |
|---|---|---|---|---|---|
| `Z_INVENTORY_REPORT` ([`z_inventory_report.abap`](abap_source/z_inventory_report.abap)) — created 2009, last transport `DEVK900412` | Executable report (`REPORT`) | ALV report (`CL_SALV_TABLE`, selection screen `S_WERKS/S_LGORT/S_MATKL/S_MTART`, `P_STALE`) | • Reads `MARD-LABST/INSME/SPEME` directly (`FORM fetch_inventory_data`, L79–101). In S/4 these are no longer stored in MARD; they are computed from `MATDOC` through the compatibility view (MM-IM data model simplification item).<br>• Last-GR lookup joins `MSEG`⋈`MKPF` (`BWART='101'`, L126–131). Both tables are replaced by `MATDOC`, and the compatibility views make this aggregation slow.<br>• `MATNR` is extended to 40 characters (material number field length extension), which affects `ty_inventory` and `lt_matnr`.<br>• Stock value is a placeholder (`total_stock * 10`, L185) and does not read `MBEW`/ACDOCA valuation.<br>• ALV GUI output is not Fiori/ABAP Cloud–released (`CL_SALV_*`). | **Rewrite-externally** (Pattern A: ALV→FastAPI). The ECC copy is ATC-remediated only far enough to run during the parallel run, then **retired**. | [`python_target/inventory_report/`](python_target/inventory_report/) (`calculate_stock_status`, `filter_by_status`, `generate_inventory_report`) / [`tests/test_inventory_report.py`](tests/test_inventory_report.py) (17 tests) |
| `Z_RFC_VENDOR_LOOKUP` ([`z_rfc_vendor_lookup.abap`](abap_source/z_rfc_vendor_lookup.abap)) — created 2011, last transport `DEVK901055` | RFC-enabled function module | RFC (called by the procurement portal and EDI middleware) | • Reads vendor master `LFA1`/`LFB1` (L91–108). In S/4 the vendor is a **Business Partner** kept in sync through CVI, so `LFA1` is only valid if CVI mapping exists, and XK0x maintenance is gone.<br>• Authorization uses `F_LFA1_BUK` (L77). Under BP maintenance, BP authorization objects (`B_BUPA_*`) also apply, so the auth concept needs review.<br>• Exported types `ZS_VENDOR_DETAIL` / `ZTT_PO_HISTORY` (L20–21) are DDIC objects **that are not in the repo** and must be extracted.<br>• Uses classic `EXCEPTIONS` plus return codes; RFC is not a released/Clean Core interface.<br>• `EKKO`/`EKPO` PO history (L131+) is still valid, but `MATNR` is now 40 characters. | **Rewrite-externally** (Pattern B: RFC→REST), with the data source repointed to released S/4 APIs (BP + purchase order). The RFC is **retired** after consumers are repointed. | [`python_target/vendor_lookup/`](python_target/vendor_lookup/) (`lookup_vendor`, `calculate_po_aggregates`) / [`tests/test_vendor_lookup.py`](tests/test_vendor_lookup.py) (9 tests) |
| `Z_IDOC_ORDER_SYNC` ([`z_idoc_order_sync.abap`](abap_source/z_idoc_order_sync.abap)) — created 2013, last transport `DEVK901388` | Function module (IDoc inbound process code) | IDoc (`ORDERS05` inbound, `MESTYP='ORDERS'`, status `64`→`51/53`) | • Classic `TABLES` parameters (`IDOC_CONTRL/IDOC_DATA/IDOC_STATUS`, L20–24; BAPI call L212–223) are obsolete and not permitted in ABAP Cloud.<br>• `ORDERS05` still runs on S/4, but it is a legacy EDI interface rather than the strategic API/event path.<br>• Partner numbers in `E1EDKA1` (`AG/WE/RE/RG`, `FORM parse_partner_segment` L297–323) must resolve to **customer BPs** after CVI.<br>• `MATNR` 40-character extension affects `E1EDP19` material mapping (L348+).<br>• `ty_order_header-doc_type` is typed as `bsad-auart` (L29). `BSAD` is an FI index table that becomes a compatibility view in S/4, so retype it to data element `AUART`.<br>• Creates orders via `BAPI_SALESORDER_CREATEFROMDAT2`. It still exists but is not released for Clean Core. | **Rewrite-externally** (Pattern C: IDoc→event-driven) calling the released S/4 Sales Order API. **Fallback:** remediate-in-S/4 (retype, BP-aware partner mapping) for trading partners that cannot leave `ORDERS05` before go-live. | [`python_target/order_sync/`](python_target/order_sync/) (`parse_idoc_to_order`, `validate_order`, `process_single_order`, `process_order_batch`) / [`tests/test_order_sync.py`](tests/test_order_sync.py) (15 tests) |

### 1.2 Observed gaps in the existing rewrite (must close before cutover)

| Gap | Where | Impact |
|---|---|---|
| No HTTP layer yet: services are "FastAPI-ready" but `fastapi` is not in [`requirements.txt`](requirements.txt) | `python_target/*/service.py` | Phase 2 must add routers and deployment |
| Data access is injected dicts/lists, not live S/4 reads | `lookup_vendor(vendor_data, po_data)`, `generate_inventory_report` | Phase 2/4 must bind to S/4 APIs or CDS views (MATDOC-based) |
| `AuthorizationError` is defined but never raised (the service assumes middleware) | [`vendor_lookup/service.py`](python_target/vendor_lookup/service.py) | `F_LFA1_BUK` equivalence must be proven at the API gateway |
| Order creation is simulated (`_create_order_in_target_system` returns a random ID) | [`order_sync/service.py`](python_target/order_sync/service.py) | Phase 2 must replace it with a real S/4 Sales Order API call plus commit/rollback semantics |
| Stock valuation is a placeholder (`* 10` USD) in both ABAP and Python | `Z_INVENTORY_REPORT` L185 | Business decision needed: keep equivalence or source valuation from S/4 |

---

## 2. Phased Roadmap

### Phase 0 — Assessment & Readiness

| Activity | Output | Repo grounding |
|---|---|---|
| **SAP Readiness Check** on ECC production | Readiness report: simplification items, add-ons, custom code volume, sizing | Confirms the scope of the 3 Z-objects plus the rest of the "hundreds" ([`README.md`](README.md)) |
| **Simplification Item Check** (`/SDF/RC_START_CHECK`) | Blocking vs. warning items for the target release | Expected hits: MM-IM data model (MARD/MSEG/MKPF→MATDOC), Business Partner/CVI, material number field length |
| **ATC with the S/4HANA readiness check variant** (remote ATC / Custom Code Migration app) | Findings list per object | Run on all objects in `abap_source/`; expect findings at `Z_INVENTORY_REPORT` L79–131, `Z_RFC_VENDOR_LOOKUP` L91–108, `Z_IDOC_ORDER_SYNC` L29, L20–24 |
| **Usage analysis** (SCMON/UPL) | Used/unused Z-objects, which drive retirement decisions | Fulfils "business owner confirmed in use" ([`pre-migration-checklist.md`](pre-migration-checklist.md) §1) |
| **CVI scoping** | Customer/vendor→BP mapping design, number ranges, BP groupings, data cleansing backlog | Vendors read by `Z_RFC_VENDOR_LOOKUP`; sold-to/ship-to/bill-to/payer in `Z_IDOC_ORDER_SYNC` |
| **DDIC extraction** | Missing structures exported | `ZS_VENDOR_DETAIL`, `ZTT_PO_HISTORY` (not in repo) |

**Exit criteria:** every object has a disposition (§1.1), CVI plan approved, simplification items have owners.

### Phase 1 — Target Architecture & Sandbox

| Decision / activity | Options → recommendation | Repo grounding |
|---|---|---|
| Deployment | On-prem / RISE private cloud / public cloud → **RISE private cloud** (brownfield conversion supported, allows remediated classic ABAP during transition) | Functional consultant decision per [`README.md`](README.md) "What consultants handle" |
| Clean Core boundary | Keep in S/4: standard processes and configuration. Move out: custom reporting and integration logic → Python services | 3/3 Z-objects go external (§1.1) |
| Integration replacement design | RFC → REST via API gateway; IDoc → message queue + event consumer; ALV → JSON API + dashboard | Playbook Patterns A/B/C ([`migration-playbook.md`](migration-playbook.md) §Migration Patterns) |
| S/4 data access contract | Released OData/CDS only; no direct table reads | Replaces `SELECT` blocks in all three ABAP sources |
| Sandbox conversion | Copy of production, converted with SUM/DMO (trial run) | Produces MATDOC/BP data for Phase 2 test fixtures |

**Exit criteria:** architecture approved, sandbox converted, API contracts agreed for inventory, vendor/PO and sales order.

### Phase 2 — Custom Code Remediation & Rewrite

| Workstream | Scope | Pattern | Proof of equivalence |
|---|---|---|---|
| Remediate retained ABAP | Only objects kept in S/4: interim `Z_INVENTORY_REPORT` (parallel run), fallback `Z_IDOC_ORDER_SYNC` (retype `bsad-auart`, 40-character `MATNR`, BP-aware partners) | ATC-clean against the S/4 variant | ATC zero priority-1/2 findings |
| ALV → FastAPI | `Z_INVENTORY_REPORT` → `inventory_report` | Pattern A | [`tests/test_inventory_report.py`](tests/test_inventory_report.py): thresholds, stale override, status filter |
| RFC → REST | `Z_RFC_VENDOR_LOOKUP` → `vendor_lookup` | Pattern B | [`tests/test_vendor_lookup.py`](tests/test_vendor_lookup.py): aggregates, date filter, `UP TO n ROWS`, not-found |
| IDoc → event-driven | `Z_IDOC_ORDER_SYNC` → `order_sync` | Pattern C | [`tests/test_order_sync.py`](tests/test_order_sync.py): 5 segment types, validation rules, batch results |
| Close the §1.2 gaps | FastAPI routers, S/4 API adapters, auth middleware, real order creation | — | New adapter tests follow the `test_<function>_<scenario>` convention ([`migration-playbook.md`](migration-playbook.md) Step 5) |
| Scale to the remaining inventory | Every other Z-object that survives Phase 0 | Same playbook, run in parallel | One `tests/test_<object>.py` per object; playbook Quality Checklist |

**Rule (from the playbook):** no logic "improvements" during rewrite. Changes to logic (e.g., real valuation instead of `* 10`) go into a separate post-validation change.

**Exit criteria:** `pytest tests/ -v` green, with S/4 sandbox data added as test fixtures, and ATC clean for retained ABAP.

### Phase 3 — Technical Conversion

| Step | Detail | Dependency |
|---|---|---|
| Pre-checks | Simplification Item Check in the SUM pre-processing phase; must be free of blocking items | Phase 0 |
| **CVI business partner conversion (mandatory)** | All customers/vendors converted to BP in ECC **before** SUM (vendors for `Z_RFC_VENDOR_LOOKUP`, customers for `Z_IDOC_ORDER_SYNC` partners) | Blocker; see §3 |
| **SUM with DMO** | Single-step release upgrade, Unicode check, and database migration to **SAP HANA** | Sizing from Readiness Check |
| Application data migration | MM-IM migration of `MSEG/MKPF` history into `MATDOC`; Finance migration to ACDOCA | Feeds the Phase 4 reconciliation |
| Custom code adaptation (SPDD/SPAU, post-conversion ATC) | Retained ABAP only | Phase 2 remediation |
| Rehearsals | ≥2 mock conversions with timed runbook | Cutover window sizing |

### Phase 4 — Integration & Data Cutover

| Activity | Detail | Repo grounding |
|---|---|---|
| Endpoint repointing | Procurement portal and EDI middleware move from RFC `Z_RFC_VENDOR_LOOKUP` to the REST `vendor_lookup` endpoint. EDI partners send to the message queue instead of `ORDERS05` port. Report users move from the transaction to the dashboard. | Callers named in the `Z_RFC_VENDOR_LOOKUP` header; `Z_IDOC_ORDER_SYNC` header |
| **MATDOC-based inventory reconciliation** | Compare ECC `MARD` (LABST+INSME+SPEME per MATNR/WERKS/LGORT) and last-GR (`MSEG` `BWART=101`) against S/4 MATDOC-derived stock and the `inventory_report` output. Tolerance: 0 quantity variance, identical traffic-light status. | `FORM fetch_inventory_data`, `calculate_stock_status`; `InventoryItem.total_stock` |
| Vendor/BP reconciliation | Every LFA1 vendor has a BP, and `lookup_vendor` returns the same totals (`total_po_value`, `open_po_count`) as the ECC RFC | `calculate_po_aggregates` |
| Order parallel run | Replay a production `ORDERS05` sample through `parse_idoc_to_order` → `process_order_batch`; compare with the ECC-created `VBAK/VBAP` and status `51/53` outcomes | `sample_idoc_segments` fixture in `tests/test_order_sync.py` |
| **Parallel-run sign-off** | Business owners sign per object; any variance becomes a defect that must be fixed before go-live | [`pre-migration-checklist.md`](pre-migration-checklist.md) §4 Acceptance |

### Phase 5 — Go-Live & Hypercare

| Activity | Detail |
|---|---|
| Cutover | Final delta conversion, freeze, then switch integration endpoints; rollback plan = re-enable ECC RFC/IDoc ports |
| Monitoring | API latency/error rates for the 3 services; queue depth and failed-message rate for `order_sync` (replaces BD87/WE02 monitoring of status 51); inventory status drift checks |
| Hypercare (4–6 weeks) | Daily defect triage; equivalence tests rerun on production data snapshots |
| ECC decommission & archive | Retire `Z_INVENTORY_REPORT`, `Z_RFC_VENDOR_LOOKUP`, `Z_IDOC_ORDER_SYNC` (and the fallback copy once partners have moved). Archive ECC data (ILM / read-only legacy store) for audit retention, then shut down ECC. |

---

## 3. Dependencies & Risks

| # | Risk / dependency | Affected objects | Mitigation | Owner |
|---|---|---|---|---|
| R1 | **CVI/BP conversion is a hard blocker**: SUM will not convert without it, and bad vendor/customer data stalls CVI | `Z_RFC_VENDOR_LOOKUP` (LFA1/LFB1), `Z_IDOC_ORDER_SYNC` (E1EDKA1 partners) | Start cleansing in Phase 0; CVI in ECC production well before SUM; reconcile BP↔LIFNR/KUNNR mapping | Functional (MDG/FI) |
| R2 | **Moved/aggregated inventory fields**: MARD stock quantities and MSEG/MKPF now come from `MATDOC`, so direct reads rely on compatibility views (slower, read-only) | `Z_INVENTORY_REPORT` L79–131; `inventory_report` data feed | Python service reads released MATDOC-based stock CDS/API; Phase 4 reconciliation; do not keep the ABAP version beyond the parallel run | Dev + MM consultant |
| R3 | Material number extended to 40 characters | All three (MATNR in types, IDoc E1EDP19, RFC PO history) | ATC field-length checks; Pydantic models carry no length constraint today, so add contract tests for 40-character values | Dev |
| R4 | **Residual ~20% out of scope for Devin**: IMG configuration, pricing procedures, output determination, workflows, authorization roles | Pricing/conditions behind `BAPI_SALESORDER_CREATEFROMDAT2` (`order_conditions_in`); `F_LFA1_BUK` → role design | Assign SAP functional consultants per [`migration-playbook.md`](migration-playbook.md) "Out of scope" and [`README.md`](README.md) "What consultants handle (the 20%)" | Functional consultants |
| R5 | Missing DDIC source | `ZS_VENDOR_DETAIL`, `ZTT_PO_HISTORY` | Extract in Phase 0 before any interface contract is frozen | Dev |
| R6 | EDI partners unable to leave `ORDERS05` by go-live | `Z_IDOC_ORDER_SYNC` | Remediate-in-S/4 fallback (§1.1); middleware converts IDoc→JSON so partners can migrate gradually | Integration |
| R7 | Rewrite not yet production-wired (§1.2) | All three Python services | Phase 2 gap-closure workstream with exit criteria | Dev |

---

## 4. Traceability

| Phase | Repo artefacts it acts on | Specific anchors |
|---|---|---|
| 0 Assessment | `abap_source/*.abap`, [`pre-migration-checklist.md`](pre-migration-checklist.md) | ATC targets: `Z_INVENTORY_REPORT` `FORM fetch_inventory_data`; `Z_RFC_VENDOR_LOOKUP` LFA1/LFB1 selects + `F_LFA1_BUK`; `Z_IDOC_ORDER_SYNC` `TABLES` interface + `bsad-auart` |
| 1 Architecture | [`migration-playbook.md`](migration-playbook.md) Scope + Patterns A/B/C; [`README.md`](README.md) "The Three Migrations" | Dispositions in §1.1 |
| 2 Remediation & Rewrite | `python_target/inventory_report/`, `python_target/vendor_lookup/`, `python_target/order_sync/`, `tests/`, [`requirements.txt`](requirements.txt) | `calculate_stock_status`, `lookup_vendor`, `parse_idoc_to_order`, `process_order_batch`; 41 tests (17 + 9 + 15) |
| 3 Technical Conversion | Data behind `abap_source/*` (MARD/MSEG/MKPF, LFA1/LFB1, KNA1 partners) | CVI for vendors/customers; MATDOC migration |
| 4 Integration & Cutover | `tests/*` fixtures reused as reconciliation harness | `InventoryItem`, `calculate_po_aggregates`, `sample_idoc_segments` |
| 5 Go-Live & Decommission | `abap_source/*` (retirement list) | `DEVK900412`, `DEVK901055`, `DEVK901388` = last ECC transports to archive |
