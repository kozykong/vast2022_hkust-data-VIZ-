# Resident Financial Health Module

> **Interactive dashboard + static visualizations** for exploring the financial well-being of Engagement's ~1,000 residents across demographic segments.

This module consists of two components:
- **`app.py`** — Streamlit + Altair interactive dashboard for grouped financial drilldown
- **`scatter_income_vs_expense.py`** — Matplotlib scatter plot comparing income vs. expense per participant

---

## Components

### `app.py` — Grouped Financial Drilldown (Streamlit)

Interactive dashboard that lets users filter participants by balance range, group them into quantile bins, and view average expense breakdowns by category.

**Controls**:
- **Month slider**: Select any month from the study period
- **Number of balance groups**: Adjustable quantile count (1–10)
- **Balance range slider**: Filter participants by end-of-month balance

**Chart**: Stacked bar chart (Altair) showing average expense per category within each balance quantile group. X = balance group, Y = average amount, color = expense category (Food, Shelter, Education, Recreation, etc.).

**Key implementation details**:
- `pd.qcut()` dynamically creates balance quantile groups with descriptive range labels
- Handles edge cases: duplicate bin edges (falls back to rank-based quantiles), insufficient participants for requested groups
- Expense categories are detected dynamically from column names (`total_amount_*`)
- Uses `@st.cache_data` for efficient data loading

### `scatter_income_vs_expense.py` — Income vs. Expense Scatter (Matplotlib)

Static visualization showing each participant's financial position for a target month.

**Encodings**:
- **X-axis**: Total logged income ($)
- **Y-axis**: Absolute total logged expense ($)
- **Color**: Net logged change (sequential blue — darker = higher surplus)
- **Size**: Household size
- **Diagonal line**: Income = |Expense| reference (above = surplus, below = deficit)

**Configuration**: Edit `TARGET_MONTH` at the top of the script to generate for any month (default: `2023-05`).

---

## Running

```bash
# Interactive dashboard
cd modules/resident-financial-health
streamlit run app.py

# Static scatter plot
python scatter_income_vs_expense.py
```

### File Dependencies

```
modules/resident-financial-health/
├── app.py                          # Streamlit dashboard
├── scatter_income_vs_expense.py    # Matplotlib scatter plot generator
└── data/
    └── monthly_participant_logged_spending_demographics.csv
    └── monthly_financial_summary_detailed_all_participants.csv
```

---

## Screenshots

| Spending Breakdown by Balance Group | Income vs. Expense Scatter |
|:---:|:---:|
| ![](../../images/fig4-group-comparison.png) | ![](../../images/fig5-detailed-monthly.png) |
