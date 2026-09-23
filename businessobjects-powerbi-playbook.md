# SAP BusinessObjects → Power BI Migration Playbook

> **Purpose**: Reusable playbook for Devin to migrate SAP BusinessObjects reporting content to Power BI.
> Designed for batch execution across many reports and universes.

---

## Scope

This playbook covers migration of **reporting content** built on SAP BusinessObjects:

| Source (BusinessObjects)                    | Target (Power BI)                                  | Pattern    |
|---------------------------------------------|----------------------------------------------------|------------|
| Universe (`.unv` / `.unx`)                  | Semantic model (dataset) + relationships           | Model      |
| Web Intelligence (Webi) report              | Power BI report (pages / visuals)                  | Report     |
| Crystal Reports                             | Paginated report (or standard report where fit)    | Report     |
| Derived tables / universe SQL               | Power Query (M) + DAX                              | Model      |
| Universe objects (dimensions / measures)    | Model columns / DAX measures                       | Model      |
| Report filters / prompts                    | Slicers / report & query parameters                | Report     |
| CMC folder security / row restrictions      | Row-Level Security (RLS) roles                     | Security   |

**Out of scope** (requires BI / functional analysts):
- Data source / ETL re-platforming
- CMC platform administration
- Scheduling and publication infrastructure (Publications)
- Auditing configuration
- Redesign of the underlying data warehouse

---

## Pre-Migration Checklist

Before starting migration of any universe or report:

- [ ] Source universe / report is exported and accessible (`.unv` / `.unx`, `.wid`, `.rpt`)
- [ ] Business owner has confirmed the report is still in use
- [ ] Target Power BI architecture is defined (workspace, gateway, dataset strategy, deployment pipeline)
- [ ] Data source dependencies are mapped (which tables / views the universe reads)
- [ ] Sample report outputs are available for comparison (exported PDF / Excel with known prompt values)
- [ ] Acceptance criteria defined (value-for-value equivalence)

---

## Migration Steps

### Step 1: Analyze the BusinessObjects Source

Read the universe and report definitions and identify:

1. **Connection & tables**: Universe connection, tables / views used, derived tables and their SQL
2. **Objects**: Dimensions, details, measures — including SELECT / WHERE clauses and aggregation functions
3. **Joins & contexts**: Join definitions, cardinalities, contexts, aggregate awareness
4. **Prompts & filters**: `@Prompt` definitions, predefined conditions, report-level filters, defaults
5. **Report structure**: Tabs, blocks (tables / crosstabs / charts), sections, breaks, report variables
6. **Drill hierarchies**: Universe hierarchies and drill paths used in the report
7. **Security**: Row restrictions, object restrictions, CMC folder access

Document these in a structured format before building anything in Power BI.

### Step 2: Design the Power BI Target

Map each BusinessObjects concept to its Power BI equivalent:

| BusinessObjects Concept     | Power BI Equivalent                          |
|-----------------------------|----------------------------------------------|
| Universe                    | Semantic model (dataset)                     |
| Dimension object            | Model column                                 |
| Measure object              | DAX measure                                  |
| Detail object               | Related column (same or related table)       |
| Condition / Filter          | Slicer / query filter                        |
| Prompt (`@Prompt`)          | Report / query parameter                     |
| Derived table               | Power Query query                            |
| Context / join path         | Model relationship                           |
| Section / Break in Webi     | Visual grouping / matrix                     |
| `@Select` / `@Where`        | M / DAX expression                           |
| Report variable             | Calculated column / DAX measure              |
| Hierarchy                   | Model hierarchy                              |
| Report-level security       | RLS role                                     |

### Step 3: Build the Semantic Model

For each universe table (or derived table):

```
// Power Query (M) — maps to universe table SALES_FACT
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
- Import via Power Query; set explicit data types for every column
- Define relationships to mirror universe joins (cardinality and direction)
- Name tables and columns after the universe objects users already know
- Add descriptions referencing the source universe object name

### Step 4: Implement Measures & Logic in DAX

Translate universe measure objects and report variables to DAX:

- Each universe measure → one DAX measure
- Preserve the aggregation function (SUM, COUNT, AVG, MIN, MAX) and projection behavior
- Reproduce `@Where` clauses as `CALCULATE` filters
- Add descriptions mapping to the universe object for traceability

**Critical**: Do NOT "improve" the business logic during migration.
The goal is **value-for-value equivalence**, not optimization.
Optimizations come in a separate phase after migration is validated.

### Step 5: Build Report Pages & Visuals

For each Webi tab / Crystal section, build a Power BI page that matches:

1. **Layout**: One page per report tab; blocks → table / matrix / chart visuals
2. **Prompts**: `@Prompt` values → slicers or parameters with the same defaults
3. **Sections / breaks**: Matrix row groups or visual grouping
4. **Formatting**: Number formats, sort order, conditional formatting (alerters)
5. **Drill**: Model hierarchies wired to visual drill-down

Visual naming convention:
```
<ReportName> / <TabName> / <BlockName>
```

### Step 6: Validate and Review

- [ ] Every measure reconciles to the source report totals for the sample prompt values
- [ ] Every universe object used by the report has a target column / measure
- [ ] Prompts / filters produce the same result set as the original
- [ ] RLS roles reproduce the original row restrictions (test with representative users)
- [ ] Business logic matches 1:1 (no accidental "improvements")
- [ ] Descriptions reference original universe / report objects for traceability

---

## Migration Patterns by Object Type

### Pattern A: Webi Report → Power BI Report

```
BusinessObjects Flow:           Power BI Flow:
────────────────────            ──────────────
Prompts (@Prompt)  ─────────►   Slicers / Parameters
    │                               │
    ▼                               ▼
Query Panel        ─────────►   Semantic model query
    │                               │
    ▼                               ▼
Report Variables   ─────────►   DAX measures / calculated columns
    │                               │
    ▼                               ▼
Sections / Breaks  ─────────►   Matrix groups / visual grouping
    │                               │
    ▼                               ▼
Blocks (tables,    ─────────►   Table / Matrix / Chart visuals
 crosstabs, charts)
    │                               │
    ▼                               ▼
Report Tabs        ─────────►   Report Pages
```

### Pattern B: Universe → Semantic Model

```
BusinessObjects Flow:           Power BI Flow:
────────────────────            ──────────────
Connection         ─────────►   Data source + gateway
    │                               │
    ▼                               ▼
Tables / Derived   ─────────►   Power Query queries
 tables
    │                               │
    ▼                               ▼
Joins / Contexts   ─────────►   Model relationships
    │                               │
    ▼                               ▼
Dimensions /       ─────────►   Model columns / hierarchies
 Details
    │                               │
    ▼                               ▼
Measures           ─────────►   DAX measures
    │                               │
    ▼                               ▼
Row restrictions   ─────────►   RLS roles
```

### Pattern C: Crystal Report → Paginated Report

```
BusinessObjects Flow:           Power BI Flow:
────────────────────            ──────────────
Parameter fields   ─────────►   Report parameters
    │                               │
    ▼                               ▼
Database expert /  ─────────►   Dataset query (SQL / DAX)
 SQL command
    │                               │
    ▼                               ▼
Formula fields     ─────────►   Report expressions
    │                               │
    ▼                               ▼
Groups / Running   ─────────►   Tablix groups / aggregate expressions
 totals
    │                               │
    ▼                               ▼
Page header /      ─────────►   Page header / footer
 footer
    │                               │
    ▼                               ▼
Export (PDF/Excel) ─────────►   Paginated export (PDF/Excel)
```

---

## Common BusinessObjects → Power BI Translations

### Universe Measure

```sql
-- Universe object: Sales\Revenue (measure)
SUM(@Select(Sales\Revenue Amount))
```

```dax
// DAX
Revenue = SUM('Sales'[Revenue])
```

### Prompt

```sql
-- Universe filter
@Select(Time\Year) = @Prompt('Select year:', 'N', 'Time\Year', mono, constrained)
```

```
// Power Query parameter (single value, constrained to list)
SelectedYear = 2024 meta [IsParameterQuery = true, Type = "Number", List = {2022, 2023, 2024}]

// Applied as a query step
Filtered = Table.SelectRows(Sales, each [Year] = SelectedYear)
```

In the report layer, a single-select slicer on `'Time'[Year]` gives the same behavior for interactive use.

### Universe SQL Filter (`@Where`)

```sql
-- Universe object: Sales\Net Revenue (measure with WHERE)
SELECT: SUM(SALES_FACT.REVENUE)
WHERE:  SALES_FACT.ORDER_STATUS <> 'CANCELLED'
```

```
// Power Query filter step
Filtered = Table.SelectRows(Sales, each [ORDER_STATUS] <> "CANCELLED")
```

```dax
// DAX equivalent (keeps cancelled rows in the model for other measures)
Net Revenue =
CALCULATE(
    SUM('Sales'[Revenue]),
    'Sales'[Order Status] <> "CANCELLED"
)
```

---

## Quality Checklist

Before marking any migrated report as complete:

- [ ] All measures reconcile to source report totals (value-for-value)
- [ ] Every universe object used has a target column / measure
- [ ] Prompts / filters are reproduced with the same defaults and constraints
- [ ] RLS matches the original row / folder security
- [ ] No unintended logic changes (aggregation, filters, join paths)
- [ ] Visuals match the original layout (tabs, blocks, sections, sort order)
- [ ] Descriptions reference original universe / report object names
- [ ] No hardcoded values that should be parameters
- [ ] Performance is acceptable for expected data volumes
