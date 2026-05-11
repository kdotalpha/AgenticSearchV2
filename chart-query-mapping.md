# Query-to-Chart Mapping Analysis

## Constraints

- **Max 3 pivots** per query (dimensions/grouping axes)
- **Unlimited value fields** per query (metrics)
- **Output**: CSV with one row per unique pivot combination, columns = pivots + values
- **Available pivots**: @ Day, @ Hour, @ Minute, @ Month, Category, Category/Resource, Resource, Use Case, Use Case Version, Use Case Response Code, Use Case Semantic Failure, Instance ID, Limit, Response Code
- **Available values**: Spend, Units, Instances, Requests, Request: Date, Request: ID, Request: Latency, Request: Full Chat, Request: Prompt, Request: Response, Request: Spend, Request: Tool Calls

---

## Minimum Queries for Maximum Chart Coverage

### Query 1: Daily Time Series by Resource

| Setting | Value |
|---------|-------|
| **Pivots** | `@ Day`, `Resource` |
| **Values** | `Spend`, `Units`, `Requests`, `Instances` |

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Line** | x=Day, y=Spend (one line per Resource) |
| **Area** | Same as line, filled |
| **Stacked Area** | Spend stacked by Resource over time |
| **Spline** | Smoothed line variant |
| **Column** | Grouped columns: x=Day, y=Spend, grouped by Resource |
| **Stacked Column** | Daily spend stacked by Resource |
| **Stacked % Column** | Percentage contribution of each Resource per day |
| **Bar** | Horizontal variant of column |
| **Stacked Bar** | Horizontal stacked |
| **Streamgraph** | Spend by Resource flowing over time |
| **Heatmap** | x=Day, y=Resource, color=Spend |
| **Pie/Donut** | Aggregate Spend by Resource (collapse time) |
| **Treemap** | Aggregate Spend by Resource (collapse time) |
| **Word Cloud** | Resource names weighted by total Spend or Requests |
| **Radar/Spider** | Resources as spokes, Spend as radial value (best with few resources) |

**Total: ~15 chart types from 1 query**

---

### Query 2: Monthly Time Series by Category and Use Case

| Setting | Value |
|---------|-------|
| **Pivots** | `@ Month`, `Category`, `Use Case` |
| **Values** | `Spend`, `Instances`, `Requests`, `Units` |

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Sunburst** | Hierarchy: Category → Use Case, value=Spend |
| **Treemap (nested)** | Same hierarchy, rectangles sized by Spend |
| **Sankey** | Flow: Category → Use Case, weight=Spend |
| **Dependency Wheel** | Category ↔ Use Case relationships weighted by Spend |
| **Line** | Monthly trend, series per Use Case (or Category) |
| **Stacked Area** | Monthly trend stacked by Category |
| **Grouped Column** | Month × Category with Use Case breakdown |
| **Heatmap** | x=Month, y=Use Case, color=Spend |
| **Pie** | Spend by Category (collapse time) |
| **Funnel** | Use Cases ordered by Spend descending (if sequential) |
| **Pyramid** | Same as funnel, inverted |

**Total: ~11 chart types from 1 query**

---

### Query 3: Instance-Level Detail by Use Case and Resource

| Setting | Value |
|---------|-------|
| **Pivots** | `Use Case`, `Instance ID`, `Resource` |
| **Values** | `Spend`, `Request: Latency` |

*Note: Requests and Units cannot be used as values when pivoting by Instance ID (Pay-i limitation).*

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Box Plot** | Group by Use Case, compute [min, q1, median, q3, max] of Spend per instance |
| **Scatter** | x=Latency, y=Spend per instance (color by Use Case) |
| **Histogram** | Distribution of Spend values across all instances |
| **Bell Curve** | Normal distribution overlay on the histogram |
| **Column Range** | Min-to-max Spend range per Use Case |
| **Area Range** | If ordered by time, shows spread of Spend |
| **Lollipop** | Average Spend per Use Case (single point per category) |

**Total: ~7 chart types from 1 query**

---

### Query 4: Hourly Pattern by Category

| Setting | Value |
|---------|-------|
| **Pivots** | `@ Hour`, `Category` |
| **Values** | `Spend`, `Requests`, `Units` |

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Polar/Radar** | 24 hours as angular axis (clock-like), Requests as radial |
| **Wind Rose** | Hour of day as angular, Category as stacked radial bars |
| **Polar Column** | Column chart wrapped around a polar axis |
| **Spline** | Smoothed intra-day pattern |
| **Line** | Hourly trend per Category |
| **Heatmap** | x=Hour, y=Category, color=Requests |
| **Column** | Hourly request volume grouped by Category |

**Total: ~7 chart types from 1 query**

---

### Query 5: Response Code Analysis by Resource

| Setting | Value |
|---------|-------|
| **Pivots** | `Response Code`, `Resource` |
| **Values** | `Requests`, `Spend` |

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Pie/Donut** | Proportion of 2xx vs 4xx vs 5xx |
| **Stacked Bar** | Error distribution per Resource |
| **Stacked % Column** | Error rate comparison across Resources |
| **Gauge (solid)** | Success rate as single KPI (% of 2xx) |
| **Bullet** | Actual error rate vs acceptable threshold |
| **Waterfall** | Total requests broken down by response code type |
| **Pareto** | Response codes sorted by frequency with cumulative % |

**Total: ~7 chart types from 1 query**

---

### Query 6: Use Case Version Comparison

| Setting | Value |
|---------|-------|
| **Pivots** | `Use Case`, `Use Case Version` |
| **Values** | `Spend`, `Units`, `Instances`, `Requests` |

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Grouped Column** | Side-by-side version comparison per Use Case |
| **Dumbbell** | Version N vs Version N+1 per Use Case (shows delta) |
| **Waterfall** | Change in Spend from one version to next |
| **Column** | Spend per version |
| **Bar** | Horizontal comparison |
| **Heatmap** | x=Version, y=Use Case, color=Spend |
| **Radar** | Multiple metrics (Spend, Requests, Units) per version |

**Total: ~7 chart types from 1 query**

---

### Query 7: Daily Time Series by Use Case and Resource

| Setting | Value |
|---------|-------|
| **Pivots** | `@ Day`, `Use Case`, `Resource` |
| **Values** | `Spend`, `Requests`, `Instances`, `Request: Latency` |

*This is the most versatile query — 3 pivots covering time, business logic, and model dimensions. Columns can be aggregated/ignored to produce simpler views (e.g., collapse Resource to get Day × Use Case).*

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Line** | x=Day, y=Spend (one line per Use Case, or per Resource) |
| **Area** | Same as line, filled |
| **Stacked Area** | Spend stacked by Use Case over time |
| **Stacked % Area** | Percentage contribution of each Use Case per day |
| **Column** | Grouped columns: x=Day, y=Requests, grouped by Use Case |
| **Stacked Column** | Daily spend stacked by Use Case×Resource |
| **Heatmap** | x=Day, y=Use Case, color=Spend (or y=Resource) |
| **Streamgraph** | Spend by Use Case flowing over time |
| **Bubble** | x=Day, y=Spend, z=Requests per Use Case (size=volume) |
| **Sankey** | Flow: Use Case → Resource, weight=Spend |
| **Dependency Wheel** | Use Case ↔ Resource relationships weighted by Spend |
| **Pareto** | Resources (or Use Cases) sorted by Spend desc + cumulative % line |
| **Radar/Spider** | Use Cases as spokes, multiple metrics as axes |
| **Lollipop** | Average Latency per Use Case or Resource (collapse time) |

**Total: ~14 chart types from 1 query**

---

### Query 8: Daily Detail with Latency (for Time-Correlated Scatter)

| Setting | Value |
|---------|-------|
| **Pivots** | `@ Day`, `Resource`, `Response Code` |
| **Values** | `Spend`, `Requests`, `Request: Latency` |

**Produces these charts:**

| Chart Type | How to Render |
|------------|---------------|
| **Scatter** | x=Day, y=Latency, color=Response Code |
| **Bubble** | x=Day, y=Latency, z=Spend, color=Resource |
| **Error Bar** | Average latency ± std dev per day per Resource |
| **Line + Error Area** | Combo: avg latency line with error band |
| **Heatmap** | x=Day, y=Resource, color=Latency |
| **Stacked Column** | Requests by Response Code over time |

**Total: ~6 chart types from 1 query**

---

## Summary: 8 Queries → ~40+ Unique Chart Types

| # | Query Pivots | Key Charts Unlocked |
|---|-------------|-------------------|
| 1 | Day + Resource | Line, Area, Column, Bar, Stacked variants, Streamgraph, Heatmap, Pie, Treemap |
| 2 | Month + Category + Use Case | Sunburst, Sankey, Dependency Wheel, nested Treemap, Funnel |
| 3 | Use Case + Instance ID + Resource | Box Plot, Scatter, Histogram, Bell Curve, Column Range |
| 4 | Hour + Category | Polar, Wind Rose, Radar (clock-pattern charts) |
| 5 | Response Code + Resource | Gauge, Bullet, Pareto, Waterfall, error-rate Pie |
| 6 | Use Case + Version | Dumbbell, version-comparison charts |
| 7 | Day + Use Case + Resource | Line, Area, Stacked, Heatmap, Bubble, Sankey, Pareto, Streamgraph, Radar |
| 8 | Day + Resource + Response Code | Scatter, Bubble, Error Bar (multi-metric time analysis) |

---

## Charts We CANNOT Support (Insufficient Data Shape)

| Chart Type | Why Not |
|------------|---------|
| **Network Graph** | No bidirectional edge/relationship data between nodes |
| **Venn / Euler Diagram** | No set membership or overlap data |
| **Geographic / Map** | No lat/long or region codes |
| **Organization Chart** | No manager/report hierarchy |
| **Vector / Windbarb** | No directional magnitude data |
| **Timeline** | No start/end timestamp pairs per event |
| **Flame Chart** | No call stack / execution trace data |
| **3D Scatter (draggable)** | Only 2 natural numeric axes available (Spend, Latency, Units = 3 but marginal) |
| **Pictorial** | Requires custom SVG shapes, not a data issue |
| **Contour** | No dense 2D spatial sampling |

---

## Charts That Are Marginal (Possible But Awkward)

| Chart Type | Issue |
|------------|-------|
| **Arc Diagram** | Same data as Sankey (Query 2) but typically needs directional sequences |
| **X-Range** | Needs start/end times per item — we only have Request: Date, not duration ranges per instance |
| **Funnel** | Works if Use Cases have a natural sequential ordering (awareness → conversion) |
| **Word Cloud** | Technically works with category/resource names weighted by spend, but adds limited insight |

---

## Data Transformation Notes

The frontend will need a transformation layer since raw CSV is always tabular. Key transforms:

1. **Aggregation** (for Pie from time-series data): Sum across time dimension
2. **Statistical computation** (for Box Plot): Compute quartiles from instance-level rows
3. **Hierarchy construction** (for Sunburst/Treemap): Build parent-child tree from flat Category + Use Case columns
4. **Flow construction** (for Sankey): Treat Category → Use Case as from → to, with Spend as weight
5. **Pivoting** (for Heatmap): Reshape rows into a matrix (x-categories × y-categories → value)
6. **Binning** (for Histogram): Group continuous Spend values into ranges
7. **Single-value extraction** (for Gauge): Compute a ratio or sum from the dataset

---

## Recommended Implementation Priority

**Phase 1 (Queries 1, 3, 5)** — Covers the bread-and-butter charts:
- Line, Area, Column, Bar, Pie, Scatter, Box Plot, Gauge

**Phase 2 (Queries 2, 4)** — Adds advanced visualizations:
- Sunburst, Sankey, Treemap, Polar/Radar, Heatmap

**Phase 3 (Queries 6, 7, 8)** — Adds comparison and use-case-level views:
- Dumbbell, Waterfall, Bubble, Error Bar, Use Case trends
