"""
preprocess_financial.py
=======================
Generates the monthly per-participant financial summary with demographic attributes
for the Resident Financial Health visualization module.

This script processes three raw data sources from the VAST Challenge 2022 dataset:
  1. Activity Logs — iteratively processed for memory efficiency (balance snapshots)
  2. Financial Journal — income (Wage) and expense transactions by category
  3. Participants — demographic attributes (age, education, household size, etc.)

Output:
  data/monthly_participant_logged_spending_demographics.csv

Usage:
  python preprocess_financial.py
"""

import pandas as pd
import numpy as np
import glob
import os
import gc
import traceback

print("Starting preprocessing for LOGGED SPENDING + DEMOGRAPHICS intermediate file...")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DATA_DIR = "data"
LOGS_DIR = os.path.join(DATA_DIR, "Activity Logs")
ATTR_DIR = os.path.join(DATA_DIR, "Attributes")
JOURNALS_DIR = os.path.join(DATA_DIR, "Journals")
FINANCIAL_JOURNAL_FILE = os.path.join(JOURNALS_DIR, "FinancialJournal.csv")
PARTICIPANTS_FILE = os.path.join(ATTR_DIR, "Participants.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "monthly_participant_logged_spending_demographics.csv")


# ──────────────────────────────────────────────
# 1. Process Activity Logs for Monthly Balances
# ──────────────────────────────────────────────
# Uses iterative file-by-file processing to handle large log files
# without loading everything into memory at once.

print("\n--- Processing Activity Logs for Balances ---")
log_file_pattern = os.path.join(LOGS_DIR, "ParticipantStatusLogs*.csv")
log_files = sorted(glob.glob(log_file_pattern))
monthly_balance_summaries_list = []
balance_cols_to_keep = ["timestamp", "participantId", "availableBalance"]

if not log_files:
    print(f"ERROR: No ParticipantStatusLogs files found in '{LOGS_DIR}'.")
else:
    print(f"Found {len(log_files)} log files. Processing sequentially...")
    for i, log_file in enumerate(log_files):
        print(f"  [{i+1}/{len(log_files)}] {os.path.basename(log_file)}")
        try:
            df_log_chunk = pd.read_csv(
                log_file,
                usecols=balance_cols_to_keep,
                parse_dates=["timestamp"],
                dtype={"participantId": "int64", "availableBalance": "float64"},
            )
            if df_log_chunk.empty or df_log_chunk["timestamp"].isnull().all():
                continue

            df_log_chunk = df_log_chunk.dropna(subset=["timestamp"])
            df_log_chunk["Month"] = df_log_chunk["timestamp"].dt.to_period("M")

            # Aggregate start/end/mean balance within this chunk
            chunk_summary = (
                df_log_chunk.sort_values("timestamp")
                .groupby(["participantId", "Month"])["availableBalance"]
                .agg(
                    chunk_start_balance="first",
                    chunk_end_balance="last",
                    chunk_mean_balance="mean",
                )
                .reset_index()
            )

            if not chunk_summary.empty:
                monthly_balance_summaries_list.append(chunk_summary)
                print(f"    → {len(chunk_summary)} participant-month entries")

            del df_log_chunk, chunk_summary
            gc.collect()

        except Exception as e:
            print(f"    ERROR: {e}")
            continue

# Combine balance data from all file chunks
if not monthly_balance_summaries_list:
    print("\nWARNING: No balance data aggregated.")
    monthly_balances_df = pd.DataFrame(
        columns=["participantId", "Month", "start_balance", "end_balance", "mean_balance"]
    )
else:
    print("\nCombining balance data across all files...")
    df_combined = pd.concat(monthly_balance_summaries_list, ignore_index=True)

    # Re-aggregate to get true first/last across file chunks for each month
    monthly_balances_df = (
        df_combined.sort_values("Month")
        .groupby(["participantId", "Month"], observed=False)
        .agg(
            start_balance=("chunk_start_balance", "first"),
            end_balance=("chunk_end_balance", "last"),
            mean_balance_approx=("chunk_mean_balance", "mean"),
        )
        .reset_index()
    )
    print(f"Monthly balance summary: {monthly_balances_df['participantId'].nunique()} participants")
    del monthly_balance_summaries_list, df_combined
    gc.collect()

monthly_balances_df["Month"] = monthly_balances_df["Month"].dt.to_timestamp()


# ──────────────────────────────────────────────
# 2. Process Financial Journal (Income + Expenses)
# ──────────────────────────────────────────────
print(f"\n--- Processing Financial Journal ---")
df_income = pd.DataFrame()
df_expenses_pivot = pd.DataFrame()
logged_expense_cols = []
logged_expense_cols_map = {}

try:
    df_financial = pd.read_csv(
        FINANCIAL_JOURNAL_FILE,
        parse_dates=["timestamp"],
        dtype={"participantId": "int64", "category": "category", "amount": "float64"},
    )
    if df_financial.empty:
        raise ValueError("Financial Journal is empty.")

    df_financial = df_financial.dropna(subset=["timestamp", "participantId"])
    df_financial["Month"] = df_financial["timestamp"].dt.to_period("M").dt.to_timestamp()

    # Separate income (Wage) from expenses
    income_mask = df_financial["category"] == "Wage"
    df_income_trans = df_financial[income_mask].copy()
    df_expense_trans = df_financial[~income_mask].copy()

    # Aggregate income per participant-month
    if not df_income_trans.empty:
        df_income = (
            df_income_trans.groupby(["participantId", "Month"])
            .agg(logged_income_total=("amount", "sum"), logged_income_count=("amount", "count"))
            .reset_index()
        )
        print(f"Logged income: {df_income.shape[0]} rows")

    # Aggregate expenses by category, then pivot into columns
    if not df_expense_trans.empty:
        df_expenses_grouped = df_expense_trans.groupby(
            ["participantId", "Month", "category"], observed=False
        ).agg(total_amount=("amount", "sum"), transaction_count=("amount", "count"))

        df_expenses_pivot = df_expenses_grouped.unstack(level="category", fill_value=0)

        # Flatten multi-level column names
        new_cols = {}
        for level0, level1 in df_expenses_pivot.columns:
            prefix = "logged_expense" if level0 == "total_amount" else "logged_count"
            new_cols[(level0, level1)] = f"{prefix}_{level1}"
        df_expenses_pivot.columns = [new_cols[col] for col in df_expenses_pivot.columns]
        df_expenses_pivot = df_expenses_pivot.reset_index()

        # Identify expense columns dynamically
        logged_expense_cols = [c for c in df_expenses_pivot.columns if c.startswith("logged_expense_")]
        logged_expense_cols_map = {c: c.replace("logged_expense_", "") for c in logged_expense_cols}

        # Calculate totals
        if logged_expense_cols:
            df_expenses_pivot["logged_expense_total"] = df_expenses_pivot[logged_expense_cols].sum(axis=1)
        logged_count_cols = [c for c in df_expenses_pivot.columns if c.startswith("logged_count_")]
        if logged_count_cols:
            df_expenses_pivot["logged_expense_count"] = df_expenses_pivot[logged_count_cols].sum(axis=1)

        print(f"Logged expenses (pivoted): {df_expenses_pivot.shape[0]} rows")

    del df_financial, df_income_trans, df_expense_trans
    gc.collect()

except FileNotFoundError:
    print(f"WARNING: Financial Journal not found at '{FINANCIAL_JOURNAL_FILE}'.")
except Exception as e:
    print(f"WARNING: Error processing Financial Journal: {e}")


# ──────────────────────────────────────────────
# 3. Load and Preprocess Demographics
# ──────────────────────────────────────────────
print(f"\n--- Processing Demographics ---")
participants_df = pd.DataFrame()

try:
    demographic_cols = [
        "participantId", "householdSize", "haveKids",
        "age", "educationLevel", "interestGroup", "joviality",
    ]
    raw = pd.read_csv(PARTICIPANTS_FILE, usecols=demographic_cols)

    # Derive age groups from birth year
    current_year = pd.Timestamp("now").year
    raw["age"] = pd.to_numeric(raw["age"], errors="coerce")
    raw["birthYear"] = current_year - raw["age"].astype("Int64")
    age_bins = [1900, 1965, 1981, 1997, current_year + 1]
    age_labels = ["Boomer+ (<1965)", "Gen X (1965-80)", "Millennial (1981-96)", "Gen Z (1997+)"]
    raw["age_group"] = pd.cut(raw["birthYear"], bins=age_bins, labels=age_labels, right=False, ordered=False)
    raw["age_group"] = raw["age_group"].astype("category").cat.add_categories("Unknown").fillna("Unknown")

    # Joviality groups
    raw["joviality"] = pd.to_numeric(raw["joviality"], errors="coerce")
    raw["joviality_group"] = pd.cut(
        raw["joviality"],
        bins=[-np.inf, 0.33, 0.66, np.inf],
        labels=["Low (0-0.33)", "Medium (0.33-0.66)", "High (0.66+)"],
        right=False, ordered=False,
    )
    raw["joviality_group"] = raw["joviality_group"].astype("category").cat.add_categories("Unknown").fillna("Unknown")

    # Household size groups
    raw["householdSize_numeric"] = pd.to_numeric(raw["householdSize"], errors="coerce").astype("Int64")
    raw["household_size_group"] = raw["householdSize_numeric"].astype(str)
    raw["household_size_group"] = (
        raw["household_size_group"]
        .replace({"5": "5+", "6": "5+", "7": "5+", "8": "5+", "<NA>": "Unknown"})
        .fillna("Unknown")
        .astype("category")
    )

    # Kids flag
    raw["haveKids"] = raw["haveKids"].astype("boolean")
    raw["haveKids_group"] = (
        raw["haveKids"].map({True: "Has Kids", False: "No Kids", pd.NA: "Unknown"}).fillna("Unknown").astype("category")
    )

    # Clean categorical columns
    raw["educationLevel"] = raw["educationLevel"].fillna("Unknown").astype("category")
    raw["interestGroup"] = raw["interestGroup"].fillna("Unknown").astype("category")

    participants_df = raw[
        [
            "participantId", "householdSize", "haveKids", "age", "educationLevel", "interestGroup", "joviality",
            "age_group", "joviality_group", "household_size_group", "haveKids_group",
        ]
    ].copy()
    print(f"Demographics processed for {len(participants_df)} participants.")
    del raw
    gc.collect()

except FileNotFoundError:
    print(f"WARNING: Participants file not found at '{PARTICIPANTS_FILE}'.")
except Exception as e:
    print(f"WARNING: Error processing demographics: {e}")


# ──────────────────────────────────────────────
# 4. Merge All Data Sources
# ──────────────────────────────────────────────
print("\n--- Merging all data sources ---")

# Use monthly balances as the base table (defines the participant × month grid)
if not monthly_balances_df.empty:
    df_merged = monthly_balances_df.copy()
elif not df_expenses_pivot.empty:
    df_merged = df_expenses_pivot[["participantId", "Month"]].drop_duplicates().copy()
elif not df_income.empty:
    df_merged = df_income[["participantId", "Month"]].drop_duplicates().copy()
else:
    print("ERROR: No data available to merge.")
    exit()

print(f"Base: {len(df_merged)} participant-months")

# Merge demographics
if not participants_df.empty:
    df_merged = pd.merge(df_merged, participants_df, on="participantId", how="left")
    print(f"After demographics: {df_merged.shape}")

# Merge logged income
if not df_income.empty:
    df_merged = pd.merge(df_merged, df_income, on=["participantId", "Month"], how="outer")
    print(f"After income: {df_merged.shape}")
else:
    df_merged[["logged_income_total", "logged_income_count"]] = 0.0

# Merge logged expenses
if not df_expenses_pivot.empty:
    df_expenses_pivot["participantId"] = df_expenses_pivot["participantId"].astype(int)
    df_expenses_pivot["Month"] = pd.to_datetime(df_expenses_pivot["Month"])
    df_merged["participantId"] = df_merged["participantId"].astype(int)
    df_merged["Month"] = pd.to_datetime(df_merged["Month"])
    df_merged = pd.merge(df_merged, df_expenses_pivot, on=["participantId", "Month"], how="outer")
    print(f"After expenses: {df_merged.shape}")
else:
    df_merged[["logged_expense_total", "logged_expense_count"]] = 0.0


# ──────────────────────────────────────────────
# 5. Post-Processing and Final Calculations
# ──────────────────────────────────────────────
print("\n--- Post-processing ---")

# Fill NaN financial columns with 0
financial_fill_cols = [
    "logged_income_total", "logged_income_count",
    "logged_expense_total", "logged_expense_count",
    "start_balance", "end_balance", "mean_balance_approx",
]
financial_fill_cols.extend(logged_expense_cols)
financial_fill_cols.extend([c.replace("expense", "count") for c in logged_expense_cols])

for col in financial_fill_cols:
    if col in df_merged.columns:
        df_merged[col] = df_merged[col].fillna(0)

# Fill NaN demographics with "Unknown"
demo_group_cols = [
    "age_group", "joviality_group", "household_size_group",
    "haveKids_group", "educationLevel", "interestGroup",
]
for col in demo_group_cols:
    if col in df_merged.columns:
        if pd.api.types.is_categorical_dtype(df_merged[col]):
            if "Unknown" not in df_merged[col].cat.categories:
                df_merged[col] = df_merged[col].cat.add_categories("Unknown")
        df_merged[col] = df_merged[col].fillna("Unknown")

# Derived metrics
df_merged["mean_balance"] = df_merged["mean_balance_approx"]
df_merged["net_logged_change"] = df_merged["logged_income_total"] - df_merged["logged_expense_total"]

# Define and select final column order
final_cols = [
    "participantId", "Month",
    # Demographics
    "age", "age_group", "educationLevel", "householdSize", "household_size_group",
    "haveKids", "haveKids_group", "interestGroup", "joviality", "joviality_group",
    # Balances
    "start_balance", "end_balance", "mean_balance",
    # Logged financials
    "logged_income_total", "logged_income_count",
    "logged_expense_total", "logged_expense_count",
    "net_logged_change",
]
final_cols.extend(sorted(logged_expense_cols))

for col in final_cols:
    if col not in df_merged.columns:
        print(f"  Adding missing column '{col}' with default value")
        df_merged[col] = 0.0 if any(k in col for k in ["total", "balance", "change", "count"]) else "Unknown"

df_final = df_merged[final_cols].copy()

# Convert count columns to int
for col in [c for c in df_final.columns if "count" in c]:
    df_final[col] = df_final[col].astype(int)

print(f"\nFinal shape: {df_final.shape}")
print(f"Columns: {df_final.columns.tolist()}")
print(df_final.head())


# ──────────────────────────────────────────────
# 6. Save Output
# ──────────────────────────────────────────────
print(f"\n--- Saving to {OUTPUT_FILE} ---")
try:
    df_final.to_csv(OUTPUT_FILE, index=False, date_format="%Y-%m-%d")
    file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Saved successfully ({file_size_mb:.2f} MB)")
except Exception as e:
    print(f"ERROR saving: {e}\n{traceback.format_exc()}")

print("\n--- Preprocessing Complete ---")
