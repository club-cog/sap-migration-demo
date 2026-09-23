# SAP BusinessObjects → Power BI Migration Playbook

> **Purpose**: Reusable playbook for Devin to migrate SAP BusinessObjects reporting content to Power BI.
> Designed for batch execution across many reports and universes.

---

## Scope

This playbook covers migration of **BusinessObjects reporting content**:

| Source (BusinessObjects)                  | Target (Power BI)                                   | Pattern     |
|-------------------------------------------|-----------------------------------------------------|-------------|
| Universe (`.unv` / `.unx`)                | Semantic model (dataset) + relationships            | Model       |
| Web Intelligence (Webi) report            | Power BI report (pages/visuals)                     | Report      |
| Crystal Reports                           | Paginated report (or standard report where appropriate) | Report  |
| Derived tables / universe SQL             | Power Query (M) + DAX                               | Model       |
| Universe objects (dimensions/measures/details) | Model columns / DAX measures                   | Model       |
| Report filters / prompts                  | Slicers / report & query parameters                 | Report      |
| CMC folder security / row restrictions    | Row-Level Security (RLS) roles                      | Security    |

**Out of scope** (requires BI/functional analysts):
- Data source / ETL re-platforming
- CMC platform administration
- Scheduling / publication infrastructure (Publications)
- Auditing configuration
- Redesign of the underlying data warehouse

---

## Pre-Migration Checklist

Before starting migration of any universe or report:

- [ ] Source universe and report are exported and accessible (`.unv`/`.unx`, `.wid`/`.rpt`)
- [ ] Business owner has confirmed the report is still in use
- [ ] Target Power BI architecture is defined (workspace, gateway, dataset strategy, deployment pipeline)
- [ ] Data source dependencies are mapped (which tables/views the universe reads)
- [ ] Sample report outputs are available for comparison (exported PDF/Excel with known prompt values)
- [ ] Acceptance criteria defined (value-for-value equivalence)

---

## Migration Steps

### Step 1: Analyze the BusinessObjects Source

Read the universe and report definitions and identify:

1. **Connection & tables**: Universe connection, source tables/views, derived tables, aliases
2. **Objects**: Dimensions, measures, details — with their SQL `SELECT` and `WHERE` definitions
3. **Joins & contexts**: Join conditions, cardinalities, contexts resolving loops, shortcut joins
4. **Prompts & filters**: `@Prompt` definitions, predefined conditions, report-level filters
5. **Report structure**: Queries, blocks (tables/crosstabs/charts), sections, breaks, report variables
6. **Drill hierarchies**: Custom navigation paths / hierarchies defined in the universe
7. **Security**: CMC folder/object access, universe row restrictions, object-level restrictions

Document these in a structured format before building anything in Power BI.

### Step 2: Design the Power BI Target

Map each BusinessObjects concept to its Power BI equivalent:

| BusinessObjects Concept     | Power BI Equivalent                       |
|-----------------------------|-------------------------------------------|
| Universe                    | Semantic model (dataset)                  |
| Dimension object            | Model column                              |
| Measure object              | DAX measure                               |
| Detail object               | Related column (same table or 1:1 lookup) |
| Condition / Filter object   | Slicer / query filter                     |
| Prompt (`@Prompt`)          | Report / query parameter                  |
| Derived table               | Power Query query                         |
| Context / join path         | Model relationship (active/inactive)      |
| Alias table                 | Duplicated / referenced query             |
| Section / Break in Webi     | Visual grouping / matrix rows             |
| `@Select` / `@Where`        | M / DAX expression                        |
| Report variable             | DAX measure or calculated column          |
| Drill hierarchy             | Model hierarchy                           |
| Report-level security       | RLS role                                  |

### Step 3: Build the Semantic Model

For each universe table (including derived tables):

```powerquery
// Power Query: maps to universe table SALES_FACT
let
    Source = Sql.Database("dw-server", "SalesDW"),
    Sales  = Source{[Schema = "dbo", Item = "SALES_FACT"]}[Data],
    Typed  = Table.TransformColumnTypes(Sales, {
        {"ORDER_DATE", type date},
        {"REVENUE",    Currency.Type},
        {"QUANTITY",   Int64.Type}
    })
in
    Typed
```

**Rules**:
- One query per universe table / derived table
- Recreate each universe join as a model relationship with the same cardinality
- Resolve contexts with inactive relationships + `USERELATIONSHIP` rather than duplicating tables where possible
- Set data types explicitly (dates, currency, whole numbers) — do not rely on inference
- Add query descriptions referencing the source universe table name

### Step 4: Implement Measures & Logic in DAX

Translate universe measures and report variables to DAX:

- Each measure object → one DAX measure
- Preserve the same object name (spaces allowed in DAX measure names)
- Preserve the aggregation function (`SUM`, `COUNT`, `AVG`, `MIN`, `MAX`) and projection aggregation behavior
- Add a measure description referencing the universe object for traceability

**Critical**: Do NOT "improve" the business logic during migration.
The goal is **value-for-value equivalence**, not optimization.
Model simplification and performance tuning come in a separate phase after validation.

### Step 5: Build Report Pages & Visuals

For each Webi or Crystal report:

1. **Pages**: One page per report tab (Webi) or report section layout (Crystal)
2. **Blocks**: Table block → table visual; crosstab → matrix; chart → equivalent chart type
3. **Sections / breaks**: Matrix row groups or one visual per section value
4. **Prompts**: Slicers for user-driven filters; query/report parameters for mandatory prompts
5. **Formatting**: Match number formats, sort order, column order, conditional formatting (alerters)

Page naming convention:
```
<Report Name> — <Tab Name>   (e.g. "Sales by Region — Summary")
```

### Step 6: Validate and Review

- [ ] Every measure reconciles to source report totals for the sample prompt values
- [ ] Every universe object used by the report has a target column/measure
- [ ] Row counts match between Webi block and Power BI visual
- [ ] Prompt / filter parity — same values produce same results
- [ ] RLS roles reproduce universe row restrictions and folder security
- [ ] Business logic matches 1:1 (no accidental "improvements")
- [ ] Descriptions reference original universe objects for traceability

---

## Migration Patterns by Object Type

### Pattern A: Universe → Semantic Model

```
BusinessObjects Flow:           Power BI Flow:
─────────────────────           ──────────────
Connection        ─────────►    Data source (gateway-enabled)
    │                               │
    ▼                               ▼
Tables / Derived  ─────────►    Power Query queries
    │                               │
    ▼                               ▼
Joins + Contexts  ─────────►    Model relationships (active/inactive)
    │                               │
    ▼                               ▼
Dimension objects ─────────►    Model columns + hierarchies
    │                               │
    ▼                               ▼
Measure objects   ─────────►    DAX measures
    │                               │
    ▼                               ▼
Row restrictions  ─────────►    RLS roles
```

### Pattern B: Webi Report → Power BI Report

```
BusinessObjects Flow:           Power BI Flow:
─────────────────────           ──────────────
Prompts           ─────────►    Slicers / parameters
    │                               │
    ▼                               ▼
Query panel       ─────────►    Semantic model fields
    │                               │
    ▼                               ▼
Report variables  ─────────►    DAX measures
    │                               │
    ▼                               ▼
Sections + Breaks ─────────►    Matrix groups / visual per section
    │                               │
    ▼                               ▼
Blocks (table,    ─────────►    Visuals (table, matrix, chart)
 crosstab, chart)
    │                               │
    ▼                               ▼
Alerters          ─────────►    Conditional formatting
```

### Pattern C: Crystal Report → Paginated Report

```
BusinessObjects Flow:           Power BI Flow:
─────────────────────           ──────────────
Parameter fields  ─────────►    Report parameters
    │                               │
    ▼                               ▼
Database fields   ─────────►    Dataset query (DAX / SQL)
    │                               │
    ▼                               ▼
Formula fields    ─────────►    Expressions / dataset columns
    │                               │
    ▼                               ▼
Groups            ─────────►    Tablix row groups
    │                               │
    ▼                               ▼
Page header/footer ────────►    Page header / footer
    │                               │
    ▼                               ▼
Export (PDF/XLS)  ─────────►    Paginated report export
```

---

## Common BusinessObjects → Power BI Translations

### Universe Measure → DAX Measure

```sql
-- Universe object: Sales\Revenue (measure, projection = Sum)
SUM(@Select(Sales\Revenue))
```

```dax
// DAX
Revenue = SUM ( 'Sales'[Revenue] )
```

### @Prompt → Parameter

```sql
-- Universe condition
SALES_FACT.REGION IN @Prompt('Select Region', 'A', 'Geography\Region', Multi, Constrained)
```

```powerquery
// Power Query parameter "Region" (Type = Text, List of values from Geography query)
Filtered = Table.SelectRows(Sales, each List.Contains(Region, [REGION]))
```

For user-driven prompts, prefer a **slicer** on `'Geography'[Region]` rather than a query parameter,
so the model is loaded once and filtered interactively.

### Universe SQL Filter → Power Query / DAX

```sql
-- Universe @Where: exclude cancelled orders
SALES_FACT.STATUS <> 'X'
```

```powerquery
// Power Query (filter step, applied at load)
ActiveOrders = Table.SelectRows(Sales, each [STATUS] <> "X")
```

```dax
// DAX (filter in measure, applied at query time)
Revenue (Active) =
CALCULATE ( SUM ( 'Sales'[Revenue] ), 'Sales'[STATUS] <> "X" )
```

Use the Power Query step when the filter applied to **every** object in the universe;
use the DAX form when it was a **condition object** applied per-report.

### Row Restriction → RLS Role

```sql
-- Universe row restriction for group "EMEA_Sales"
SALES_FACT.REGION IN ('DE', 'FR', 'UK')
```

```dax
// RLS role "EMEA Sales" — table filter on 'Geography'
'Geography'[Region] IN { "DE", "FR", "UK" }
```

---

## Quality Checklist

Before marking any migrated report as complete:

- [ ] All measures reconcile to source report totals
- [ ] Every universe object used has a target column/measure
- [ ] Prompts / filters reproduced (slicers or parameters)
- [ ] RLS matches original security (test with "View as role")
- [ ] No unintended logic changes
- [ ] Visuals match original layout (blocks, sections, sort, formats)
- [ ] Descriptions reference original universe objects / report blocks
- [ ] No hardcoded connection strings that should be parameters
- [ ] Performance is acceptable for expected data volumes
