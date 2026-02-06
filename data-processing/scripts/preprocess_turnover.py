"""
preprocess_turnover.py
======================
Processes raw VAST Challenge 2022 Activity Logs to generate employment
dynamics datasets for the Business Turnover visualization module.

This script produces two intermediate datasets:
  1. workers_by_company_month.csv — worker count per employer per month
  2. work.csv — flat table of participant × date employment records

These are consumed by the layoff_timeline.py, layoff_map.py, layoff_treemap.py,
and the combined app.py dashboard.

Usage:
  python preprocess_turnover.py
"""

import pandas as pd
import numpy as np
import glob
import os
import gc

print("Starting employment/turnover preprocessing...")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DATA_DIR = "data"
LOGS_DIR = os.path.join(DATA_DIR, "Activity Logs")
ATTR_DIR = os.path.join(DATA_DIR, "Attributes")
OUTPUT_DIR = os.path.join(DATA_DIR, "restructure_data")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# 1. Load Activity Logs (iteratively for memory)
# ──────────────────────────────────────────────
print("\n--- Loading Activity Logs ---")
log_pattern = os.path.join(LOGS_DIR, "ParticipantStatusLogs*.csv")
log_files = sorted(glob.glob(log_pattern))

if not log_files:
    print(f"ERROR: No log files found in {LOGS_DIR}")
    exit(1)

print(f"Found {len(log_files)} log files.")

cols_to_keep = ["timestamp", "participantId", "currentEmployer"]
all_chunks = []

for i, f in enumerate(log_files):
    print(f"  [{i+1}/{len(log_files)}] {os.path.basename(f)}")
    try:
        chunk = pd.read_csv(f, usecols=cols_to_keep, parse_dates=["timestamp"])
        chunk = chunk.dropna(subset=["timestamp"])
        all_chunks.append(chunk)
    except Exception as e:
        print(f"    ERROR: {e}")
        continue

df_logs = pd.concat(all_chunks, ignore_index=True)
del all_chunks
gc.collect()

print(f"Total log entries: {len(df_logs)}")

# ──────────────────────────────────────────────
# 2. Extract Employment Records
# ──────────────────────────────────────────────
print("\n--- Extracting employment records ---")

# A participant is employed if currentEmployer is not NaN
df_logs["date"] = df_logs["timestamp"].dt.date
df_logs["month"] = df_logs["timestamp"].dt.to_period("M").astype(str)

# For each participant per day, take the last known employment status
df_daily = (
    df_logs.sort_values("timestamp")
    .groupby(["participantId", "date"])
    .agg(currentEmployer=("currentEmployer", "last"))
    .reset_index()
)

# Filter to employed records only (non-null employer)
df_employed = df_daily[df_daily["currentEmployer"].notna()].copy()
df_employed["employerId"] = df_employed["currentEmployer"].astype(int)
df_employed["date"] = pd.to_datetime(df_employed["date"])

# Save flat employment records (used by layoff_timeline.py)
work_output = os.path.join(OUTPUT_DIR, "work.csv")
df_employed[["participantId", "date", "employerId"]].to_csv(work_output, index=False)
print(f"Saved: {work_output} ({len(df_employed)} rows)")

# ──────────────────────────────────────────────
# 3. Aggregate Workers per Company per Month
# ──────────────────────────────────────────────
print("\n--- Aggregating workers by company-month ---")

df_employed["month"] = df_employed["date"].dt.to_period("M").astype(str)

# Count unique workers per employer per month
workers_by_company = (
    df_employed.groupby(["employerId", "month"])["participantId"]
    .nunique()
    .reset_index()
    .rename(columns={"participantId": "worker_count"})
)

# Save (used by layoff_map.py, layoff_treemap.py, app.py)
company_output = os.path.join(OUTPUT_DIR, "workers_by_company_month.csv")
workers_by_company.to_csv(company_output, index=False)
print(f"Saved: {company_output} ({len(workers_by_company)} rows)")
print(f"  Unique employers: {workers_by_company['employerId'].nunique()}")
print(f"  Month range: {workers_by_company['month'].min()} to {workers_by_company['month'].max()}")

print("\n--- Turnover Preprocessing Complete ---")
