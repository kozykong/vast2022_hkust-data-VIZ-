# Requirements Analysis

This document maps the VAST Challenge 2022 (Challenge 3: Economic) analytical questions to concrete design requirements that drive the FinancialView system.

---

## Challenge Context

The city of Engagement, Ohio has received an urban renewal grant and is preparing for rapid growth. City planners need a comprehensive understanding of the current economic state to allocate resources effectively. The dataset covers ~1,000 volunteer residents over a 15-month period (early 2022 – mid 2023) and includes activity logs, static attributes, and event-based journals.

---

## Question-to-Requirement Mapping

### Q1: What is the state of the local businesses?

**Focus**: Employer turnover and layoff patterns.

| Requirement ID | Requirement | Rationale |
|:-:|---|---|
| DR1.1 | Visualize monthly changes in overall workforce size | Need to see the macro trend — is employment growing, shrinking, or stable? |
| DR1.2 | Identify specific layoff events and their magnitude | Discrete shocks (like a 13% drop) require explicit visual markers, not just smooth trend lines |
| DR1.3 | Analyze layoffs by employer characteristics (size, location) | Layoffs hitting large vs. small companies have different policy implications; geography matters for targeted intervention |

**Data sources**: Activity Logs (current job field), Employer Attributes (company size, location), Job Attributes.

**Derived metrics**:
- Monthly total employed count (from activity log snapshots)
- Month-over-month change (absolute and percentage)
- Layoff count per employer per month (participants whose job status changes to unemployed)

---

### Q2: How do residents' logged incomes compare to their logged expenses?

**Focus**: Financial health and stability across demographic segments.

| Requirement ID | Requirement | Rationale |
|:-:|---|---|
| DR2.1 | Track key financial metrics over the 15-month period | Longitudinal view reveals whether residents are getting better or worse off |
| DR2.2 | Compare financial metrics across demographic segments | Education level, age group, etc. may reveal inequality patterns that uniform averages would hide |
| DR2.3 | Monthly participant-level income vs. expense inspection | Aggregate averages mask individual distress — need to see the scatter of outcomes |
| DR2.4 | Visualize average spending composition by category | Knowing that "Shelter" dominates spending tells planners where affordability pressure is highest |

**Data sources**: Financial Journal (category, amount), Participant Attributes (education level, age group, household size), Activity Logs (account balance).

**Derived metrics** (monthly, per participant):
- Total logged income: sum of "Wage" entries in Financial Journal
- Total logged expense: sum of all non-Wage entries
- Net logged change: income − expense
- Average per-category spending: mean across participants for each expense category (Food, Shelter, Education, Recreation, RentAdjustment)
- Account balance: from Activity Logs snapshot

**Key preprocessing output**: `monthly_participant_logged_spending_demographics.csv` — one row per participant per month, with all metrics and demographic attributes joined.

---

### Q3: How are local businesses (pubs, restaurants) performing?

**Focus**: Revenue trends and foot traffic correlation.

| Requirement ID | Requirement | Rationale |
|:-:|---|---|
| DR3.1 | Correlate foot traffic (check-ins) with revenue per venue | Tests the hypothesis that fewer visits = less revenue, and quantifies the relationship |
| DR3.2 | Show weekly trends in revenue and foot traffic by venue type | Weekly granularity captures short-term dynamics; venue type segmentation reveals which sectors are hit hardest |
| DR3.3 | Support temporal exploration (animation, timeline scrubbing) | The relationship changes over time — static snapshots miss the declining trajectory |

**Data sources**: Check-in Journal (venue ID, timestamp), Financial Journal (venue-linked spending), Venue Attributes (venue type: Pub, Restaurant).

**Derived metrics** (weekly, per venue):
- Foot traffic: count of check-ins
- Revenue: sum of spending at that venue
- Average spending per visit: revenue / foot traffic

---

## Requirements Validation

| Requirement | Module | Visualization | Status |
|:-:|---|---|:-:|
| DR1.1 | Business Turnover | Monthly workers line chart | ✅ |
| DR1.2 | Business Turnover | Significant change markers on line chart | ✅ |
| DR1.3 | Business Turnover | Layoff map (geography) + treemap (employer size) | ✅ |
| DR2.1 | Resident Financial Health | Monthly trend line chart (Group Comparison view) | ✅ |
| DR2.2 | Resident Financial Health | Box plot distribution + color-coded demographic groups | ✅ |
| DR2.3 | Resident Financial Health | Income vs. Expense scatter plot (Detailed Monthly view) | ✅ |
| DR2.4 | Resident Financial Health | Stacked bar chart of average spending breakdown | ✅ |
| DR3.1 | Business Revenue | Animated scatter plot (check-ins vs. revenue) | ✅ |
| DR3.2 | Business Revenue | Dual Y-axis weekly trend line chart | ✅ |
| DR3.3 | Business Revenue | Timeline bar with play animation | ✅ |
