# Design Decisions

This document explains **why** each visualization was chosen, what alternatives were considered, and the interaction and color strategies employed across FinancialView.

---

## Module 1: Business Turnover

### Monthly Working Population — Line Chart

| Aspect | Decision |
|--------|----------|
| **Chart type** | Line chart with markers |
| **Why** | Time-series with continuous monthly data — line charts naturally encode temporal progression and make trends (upward, downward, stable) immediately readable |
| **Alternatives considered** | Bar chart (harder to see trend direction), area chart (works but implies volume rather than count), small multiples by employer (too many employers) |
| **Enhancements** | Dashed trend line for projection; orange markers on significant changes (e.g., 13% drop); secondary bar chart overlay for month-over-month change magnitude |

### Geographical Layoff Distribution — Map View

| Aspect | Decision |
|--------|----------|
| **Chart type** | Point map with color-intensity encoding |
| **Why** | Layoff concentration is inherently spatial — a map answers "where are layoffs happening?" in a way no bar chart can |
| **Alternatives considered** | Choropleth (requires defined regions; Engagement's data is point-based), bar chart by region (loses spatial context), heat map overlay (smoothing may misrepresent discrete employer locations) |
| **Encoding** | Circle size and color darkness both scale with layoff count — redundant encoding improves readability |

### Layoffs by Employer Size — Treemap

| Aspect | Decision |
|--------|----------|
| **Chart type** | Treemap with hierarchical grouping |
| **Why** | Shows part-to-whole relationships across a hierarchy (All Companies → Size Category → Individual Employers) in a compact space |
| **Alternatives considered** | Grouped bar chart (works but doesn't show hierarchy as intuitively), sunburst chart (harder to read labels), stacked bar (doesn't convey individual employer variation within size groups) |
| **Color strategy** | Gradient by company size category — darker = larger company — enables instant size-group identification |

---

## Module 2: Resident Financial Health (Dash/Plotly)

### Group Comparison — Trend Line + Box Plot

**Trend Line Chart**

| Aspect | Decision |
|--------|----------|
| **Chart type** | Multi-line chart (one line per demographic group) |
| **Why** | Direct visual comparison of how different groups evolve over the same time period — crossing or diverging lines immediately signal inequality shifts |
| **Encoding** | X = month, Y = mean of selected metric, color = demographic category |
| **Interaction** | Dropdown selectors for demographic attribute (Education Level, Age Group, etc.) and financial metric (Balance, Income, Expense, Net Change) |

**Distribution Box Plot**

| Aspect | Decision |
|--------|----------|
| **Chart type** | Box plot (one per demographic category) |
| **Why** | Box plots show median, spread, and outliers — essential for understanding whether a group's "average" is representative or if there's high variance |
| **Alternatives considered** | Violin plot (richer but harder to compare across many groups), histogram (need separate panels per group), strip/swarm plot (too many points overlap) |
| **Complementarity** | The line chart shows "how the average moves over time"; the box plot shows "how spread out individuals are within each group" — together they give both the signal and the noise |

### Detailed Monthly View — Scatter Plot + Stacked Bar

**Income vs. Expense Scatter Plot**

| Aspect | Decision |
|--------|----------|
| **Chart type** | Scatter plot with multi-dimensional encoding |
| **Why** | Each dot is one participant in one month — the scatter reveals the joint distribution of income and expense, which no aggregation can capture |
| **Encoding** | X = total logged expense, Y = total logged income, color = net change (diverging scale centered at 0), size = household size |
| **Key design element** | Diagonal reference line where income = expense. Points above: surplus. Points below: deficit. This single line makes the entire chart interpretable at a glance |
| **Alternatives considered** | Parallel coordinates (harder with 1,000 participants), paired bar chart per participant (doesn't scale), histogram of net change (loses the two-variable relationship) |

**Spending Breakdown Stacked Bar**

| Aspect | Decision |
|--------|----------|
| **Chart type** | Stacked bar chart |
| **Why** | Shows composition — how total average spending decomposes into Food, Shelter, Recreation, Education, RentAdjustment — and total magnitude simultaneously |
| **Grouping** | Bars grouped by balance quantile range, revealing whether spending composition differs by wealth level |
| **Alternatives considered** | Pie chart (poor for comparison across groups), 100% stacked bar (loses magnitude information), small multiples of individual bar charts (takes more space) |

---

## Module 3: Business Revenue

### Revenue vs. Foot Traffic — Animated Scatter Plot

| Aspect | Decision |
|--------|----------|
| **Chart type** | Animated bubble chart with timeline scrubber |
| **Why** | Shows the correlation between two continuous variables (check-ins and revenue) while the animation reveals how this relationship evolves week by week |
| **Encoding** | X = number of check-ins, Y = total revenue, size = average spending per visit, color = venue type (Pub vs. Restaurant) |
| **Interaction** | Timeline bar for week selection + play button for automatic animation — lets users either explore specific weeks or watch the full trajectory |
| **Alternatives considered** | Static scatter with color = time (cluttered), small multiples by week (too many panels), connected scatter plot (lines between weeks become tangled with multiple venues) |

### Weekly Trends — Dual Y-Axis Line Chart

| Aspect | Decision |
|--------|----------|
| **Chart type** | Dual Y-axis line chart |
| **Why** | Revenue and foot traffic have different scales but we want to see if they move in parallel — dual axes align the time dimension while preserving each metric's natural scale |
| **Encoding** | Left Y = revenue, right Y = foot traffic, X = week, color = venue type, line style differentiates metric |
| **Known trade-off** | Dual Y-axis charts can be misleading if scales are manipulated — we kept scales honest and included both axis labels clearly |
| **Alternatives considered** | Normalized/indexed chart (loses absolute magnitude), separate panels (harder to see correlation visually), scatter of revenue vs. traffic aggregated weekly (loses temporal order) |

---

## Cross-Cutting Design Decisions

### Color Strategy

| Context | Approach |
|---------|----------|
| Demographic categories | Qualitative palette (distinct hues) — e.g., Bachelors = blue, Graduate = green |
| Sequential quantitative data | Single-hue gradient (e.g., layoff intensity: white → dark red) |
| Diverging quantitative data | Diverging palette centered at zero (e.g., net change: red = deficit, blue = surplus) |
| Venue type distinction | Two-color scheme (Pub = blue, Restaurant = red) |

### Interaction Design

All interactive elements serve the principle of **progressive disclosure** — the dashboard starts with an overview and lets users drill down:

1. **Dropdown selectors** (Module 2): Choose demographic attribute and financial metric → overview updates
2. **Month slider** (Module 2): Select a specific month → detailed view updates
3. **Timeline bar + animation** (Module 3): Scrub through weeks or auto-play → scatter plot updates
4. **Hover tooltips** (all modules): Details on demand for individual data points

### Technology Choice: Dash + Plotly vs. D3.js

| Factor | Dash + Plotly | D3.js |
|--------|:---:|:---:|
| Python ecosystem integration | ✅ Native | ❌ Requires separate backend |
| Interactivity (dropdowns, callbacks) | ✅ Built-in | ⚠️ Manual DOM manipulation |
| Statistical charts (box plots) | ✅ One-liner | ⚠️ Manual implementation |
| Custom animation control | ⚠️ Limited | ✅ Full control |
| Deployment simplicity | ✅ Single Python process | ⚠️ Needs web server |
| Learning curve for data scientists | ✅ Low (Pythonic) | ⚠️ Steeper (JS + SVG) |

**Decision**: Dash + Plotly for the Resident Financial Health module because the team's primary skill set is Python, the required chart types (line, box, scatter, stacked bar) are all first-class citizens in Plotly Express, and the callback system handles the multi-dropdown interactivity with minimal code.

Tableau was used for the Business Turnover and Revenue modules because those visualizations benefited from Tableau's native map rendering and animation capabilities.
