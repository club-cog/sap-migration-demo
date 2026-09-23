# BusinessObjects → Power BI Pre-Migration Prerequisites Checklist

Expands the **Pre-Migration Checklist** in
[businessobjects-powerbi-playbook.md](businessobjects-powerbi-playbook.md) with scope confirmation
and per-report analysis prerequisites. Work through this before building anything in Power BI for a
universe or report.

---

## 1. Source & ownership

- [ ] Source universe (`.unv`/`.unx`) and report (`.wid`/`.rpt`) are exported and accessible
- [ ] Business owner has confirmed the report is still in use

## 2. Target definition

- [ ] Target Power BI architecture is defined (workspace, gateway, dataset strategy, deployment pipeline)
- [ ] Decision recorded: shared semantic model vs. per-report dataset
- [ ] Decision recorded: standard report vs. paginated report (for Crystal sources)

## 3. Dependencies & data

- [ ] Data source dependencies are mapped (which tables/views the universe reads)
- [ ] Source database is reachable from the gateway (or import path agreed)
- [ ] Sample report outputs are available for comparison (with the prompt values used)

## 4. Acceptance

- [ ] Acceptance criteria defined (value-for-value equivalence on sample outputs)

## 5. Scope confirmation (in vs. out)

Confirm the item falls into reporting-content migration scope — universes, Webi reports, Crystal
Reports, derived tables, universe objects, prompts/filters, folder/row security — and is not one of
the out-of-scope items that need BI/functional analysts:

- [ ] Not data source / ETL re-platforming or data warehouse redesign
- [ ] Not CMC platform administration, Publications/scheduling, or auditing configuration

## 6. Analysis inputs gathered (per report)

Document these from the universe and report before building in Power BI:

- [ ] Connection & tables (source tables/views, derived tables, aliases)
- [ ] Objects (dimensions, measures, details with SELECT/WHERE definitions)
- [ ] Joins & contexts (conditions, cardinalities, loop resolution)
- [ ] Prompts & filters (`@Prompt` definitions, condition objects, report filters)
- [ ] Report structure (queries, blocks, sections, breaks, report variables)
- [ ] Drill hierarchies
- [ ] Security (folder access, row restrictions, object restrictions)
