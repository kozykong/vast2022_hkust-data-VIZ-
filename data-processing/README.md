# Data Processing Pipeline

This directory contains the Python preprocessing scripts that transform raw VAST Challenge 2022 data into module-specific intermediate CSVs.

---

## Pipeline Overview

```
Raw VAST Data                    Preprocessing Scripts              Module-Ready CSVs
─────────────                    ──────────────────────             ─────────────────
Activity Logs ──┐
                ├──► preprocess_turnover.py ──────► monthly_employment.csv
Employer Attrs ─┘                                   employer_layoffs.csv

Activity Logs ──┐
Financial Jrnl ─┤
                ├──► preprocess_financial.py ─────► monthly_participant_logged_
Participant     │                                   spending_demographics.csv
  Attrs ────────┘

Check-in Jrnl ──┐
Financial Jrnl ─┤
                ├──► preprocess_revenue.py ───────► weekly_venue_revenue_traffic.csv
Venue Attrs ────┘
```

---

## Scripts

### `preprocess_turnover.py`

Processes employment dynamics for Module 1 (Business Turnover).

**Input files**:
- `ActivityLogs.csv` — participant status updates (includes `currentJob` field)
- `Employers.csv` — employer metadata (company size, location)
- `Jobs.csv` — job role attributes

**Logic**:
1. Extract monthly snapshots of each participant's employment status from activity logs
2. Count total employed participants per month → `monthly_employment.csv`
3. Detect job-loss events (participant transitions from employed → unemployed)
4. Aggregate layoffs per employer per month, join with employer attributes → `employer_layoffs.csv`

**Output schema — `monthly_employment.csv`**:

| Column | Type | Description |
|--------|------|-------------|
| `month` | date | Year-month |
| `total_workers` | int | Count of employed participants |
| `monthly_change` | int | Absolute change from previous month |
| `pct_change` | float | Percentage change from previous month |

**Output schema — `employer_layoffs.csv`**:

| Column | Type | Description |
|--------|------|-------------|
| `month` | date | Year-month of layoff event |
| `employer_id` | int | Employer identifier |
| `employer_name` | str | Company name |
| `company_size` | str | Small / Medium / Large |
| `location_x` | float | Employer x-coordinate |
| `location_y` | float | Employer y-coordinate |
| `layoff_count` | int | Number of participants laid off |

---

### `preprocess_financial.py`

Generates the core dataset for Module 2 (Resident Financial Health).

**Input files**:
- `FinancialJournal.csv` — transaction records with category and amount
- `Participants.csv` — demographic attributes
- `ActivityLogs.csv` — account balance snapshots

**Logic**:
1. Parse Financial Journal entries; classify as income (`category == 'Wage'`) or expense (all other categories)
2. Aggregate per participant per month:
   - Total logged income (sum of Wage entries)
   - Total logged expense (sum of non-Wage entries, absolute value)
   - Net logged change (income − expense)
   - Per-category spending (Food, Shelter, Education, Recreation, RentAdjustment)
3. Extract end-of-month account balance from Activity Logs
4. Join with Participant Attributes (education level, age group, household size, interest group)
5. Derive balance quantile ranges for the spending breakdown chart

**Output schema — `monthly_participant_logged_spending_demographics.csv`**:

| Column | Type | Description |
|--------|------|-------------|
| `participantId` | int | Participant identifier |
| `month` | date | Year-month |
| `total_logged_income` | float | Sum of Wage entries |
| `total_logged_expense` | float | Sum of non-Wage entries (absolute) |
| `net_logged_change` | float | Income − expense |
| `avg_balance` | float | End-of-month account balance |
| `expense_food` | float | Food category spending |
| `expense_shelter` | float | Shelter category spending |
| `expense_education` | float | Education category spending |
| `expense_recreation` | float | Recreation category spending |
| `expense_rentadjustment` | float | Rent adjustment |
| `education_level` | str | HighSchoolOrCollege / Bachelors / Graduate / Low |
| `age_group` | str | Demographic age bucket |
| `household_size` | int | Number of household members |
| `interest_group` | str | Participant interest category |
| `balance_quantile` | str | Derived balance range label |

---

### `preprocess_revenue.py`

Prepares venue-level revenue and foot traffic data for Module 3 (Business Revenue).

**Input files**:
- `CheckinJournal.csv` — venue visit records
- `FinancialJournal.csv` — spending at venues
- `Venues.csv` — venue metadata (type: Pub, Restaurant, etc.)

**Logic**:
1. Filter venues to Pub and Restaurant types
2. Count check-ins per venue per week → foot traffic
3. Sum spending at each venue per week → revenue
4. Calculate average spending per visit (revenue / foot traffic)
5. Join with venue attributes

**Output schema — `weekly_venue_revenue_traffic.csv`**:

| Column | Type | Description |
|--------|------|-------------|
| `week` | date | Week start date |
| `venue_id` | int | Venue identifier |
| `venue_name` | str | Venue name |
| `venue_type` | str | Pub / Restaurant |
| `check_ins` | int | Number of check-ins (foot traffic) |
| `total_revenue` | float | Sum of spending at venue |
| `avg_spend_per_visit` | float | Revenue / check-ins |

---

## Running the Pipeline

```bash
cd data-processing

# Install dependencies
pip install -r requirements.txt

# Run each script (assumes raw VAST data is in ../data/raw/)
python scripts/preprocess_turnover.py
python scripts/preprocess_financial.py
python scripts/preprocess_revenue.py
```

### Requirements

```
pandas>=2.0.0
numpy>=1.24.0
```

---

## Data Quality Notes

- **Missing job entries**: Some participants have gaps in activity logs where their employment status is ambiguous. These are treated as "unchanged from last known status."
- **Negative expense values**: RentAdjustment entries can be negative (credits). These are preserved as-is in the per-category columns but the `total_logged_expense` uses absolute values of actual spending categories.
- **Temporal alignment**: Activity log timestamps are snapped to month-end for joining with monthly Financial Journal aggregations.
