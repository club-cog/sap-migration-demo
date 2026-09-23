# BusinessObjects → Power BI Pre-Migration Prerequisites Checklist

Expands the **Pre-Migration Checklist** in
[businessobjects-powerbi-playbook.md](businessobjects-powerbi-playbook.md) with scope confirmation
and per-report analysis prerequisites. Work through this before building anything in Power BI for a
BusinessObjects universe or report.

---

## 1. Source & ownership

- [ ] Source universe / report is exported and accessible (`.unv` / `.unx`, `.wid`, `.rpt`)
- [ ] Business owner has confirmed the report is still in use

## 2. Target definition

- [ ] Target Power BI architecture is defined (workspace, gateway, dataset strategy, deployment pipeline)

## 3. Dependencies & data

- [ ] Data source dependencies are mapped (which tables / views the universe reads)
- [ ] Sample report outputs are available for comparison (exported PDF / Excel with known prompt values)

## 4. Acceptance

- [ ] Acceptance criteria defined (value-for-value equivalence)

## 5. Scope confirmation (in vs. out)

Confirm the item falls into reporting-content migration scope — universes, Webi reports, Crystal
Reports, derived tables, universe objects, prompts / filters, row restrictions — and is not one of
the out-of-scope items that need BI / functional analysts:

- [ ] Not data source / ETL re-platforming or data warehouse redesign
- [ ] Not CMC platform administration, Publications / scheduling, or auditing configuration

## 6. Analysis inputs gathered (per report)

Document these from the universe and report before building in Power BI:

- [ ] Connection & tables (universe connection, tables / views, derived tables and their SQL)
- [ ] Objects (dimensions, details, measures with SELECT / WHERE and aggregation)
- [ ] Joins & contexts (cardinalities, contexts, aggregate awareness)
- [ ] Prompts & filters (`@Prompt` definitions, predefined conditions, report filters, defaults)
- [ ] Report structure (tabs, blocks, sections, breaks, report variables)
- [ ] Drill hierarchies (universe hierarchies and drill paths used)
- [ ] Security (row restrictions, object restrictions, CMC folder access)
