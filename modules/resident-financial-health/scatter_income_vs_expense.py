"""
scatter_income_vs_expense.py
============================
Generates a scatter plot comparing each participant's total logged income
against their absolute logged expense for a selected month.

Encodings:
  - X-axis: Total Logged Income ($)
  - Y-axis: Absolute Total Logged Expense ($)
  - Color: Net Logged Change (sequential blue — darker = higher surplus)
  - Size: Household Size
  - Diagonal line: Income = |Expense| reference

Output:
  income_vs_abs_expense_scatter_blue_{MONTH}.png

Usage:
  python scatter_income_vs_expense.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import os
import traceback

print("Generating Income vs. Absolute Expense Scatter Plot...")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DATA_FILE = os.path.join("data", "monthly_participant_logged_spending_demographics.csv")
TARGET_MONTH = "2023-05"
FIXED_AXIS_LIMIT = 20000

# Color encoding
COLOR_VAR = "net_logged_change"
CMAP_NAME = "Blues"
COLORBAR_MIN = -5000
COLORBAR_MAX = 25000

OUTPUT_FILENAME = f"income_vs_abs_expense_scatter_blue_{TARGET_MONTH}.png"

# ──────────────────────────────────────────────
# Load and Filter Data
# ──────────────────────────────────────────────
print(f"Loading data from {DATA_FILE}...")
try:
    df = pd.read_csv(DATA_FILE)
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    df = df.dropna(subset=["Month"])
    print(f"Loaded: {df.shape}")
except FileNotFoundError:
    print(f"ERROR: File not found at {DATA_FILE}.")
    exit()

print(f"Filtering for {TARGET_MONTH}...")
df_month = df[df["Month"] == pd.Timestamp(TARGET_MONTH)].copy()
if df_month.empty:
    print(f"ERROR: No data for {TARGET_MONTH}.")
    exit()
print(f"Found {len(df_month)} records.")

# Prepare numeric columns and drop NaNs
required_cols = ["logged_income_total", "logged_expense_total", COLOR_VAR, "householdSize"]
for col in required_cols:
    df_month[col] = pd.to_numeric(df_month[col], errors="coerce")

df_plot = df_month.dropna(subset=required_cols).copy()
print(f"Valid rows for plotting: {len(df_plot)}")

df_plot["abs_logged_expense"] = df_plot["logged_expense_total"].abs()
df_plot["householdSize"] = df_plot["householdSize"].astype(float).clip(lower=1.0)

# ──────────────────────────────────────────────
# Create Scatter Plot
# ──────────────────────────────────────────────
print("Creating plot...")
try:
    fig, ax = plt.subplots(figsize=(12, 8))

    x_data = df_plot["logged_income_total"]
    y_data = df_plot["abs_logged_expense"]
    color_data = df_plot[COLOR_VAR]
    size_data = df_plot["householdSize"] * 25

    # Color mapping: sequential blue with fixed range
    norm = mcolors.Normalize(vmin=COLORBAR_MIN, vmax=COLORBAR_MAX)
    cmap = cm.get_cmap(CMAP_NAME)

    scatter = ax.scatter(
        x_data, y_data,
        c=color_data, s=size_data,
        cmap=cmap, norm=norm,
        alpha=0.7, edgecolors="grey", linewidth=0.5,
        label="Participants (Size=HH Size)",
    )

    # Colorbar
    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label(f'{COLOR_VAR.replace("_", " ").title()} ($)', fontsize=10)

    # Reference line: Income = |Expense|
    ax.plot(
        [0, FIXED_AXIS_LIMIT], [0, FIXED_AXIS_LIMIT],
        color="black", linestyle="--", alpha=0.7, zorder=5,
        label="Income = |Expense|",
    )

    # Axis limits and formatting
    ax.set_xlim(0, FIXED_AXIS_LIMIT)
    ax.set_ylim(0, FIXED_AXIS_LIMIT)
    ax.set_xlabel("Total Logged Income ($)", fontsize=11)
    ax.set_ylabel("Absolute Total Logged Expense ($)", fontsize=11)
    ax.set_title(
        f"Logged Income vs. Absolute Expense for {TARGET_MONTH}\n"
        f'(Color: {COLOR_VAR.replace("_", " ").title()}, Size: Household Size)',
        fontsize=14,
    )

    formatter = mtick.FormatStrFormatter("$%.0f")
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)
    plt.xticks(rotation=30, ha="right")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    # Save
    print(f"Saving to {OUTPUT_FILENAME}...")
    fig.savefig(OUTPUT_FILENAME, dpi=150)
    print("Saved successfully.")

except Exception as e:
    print(f"ERROR: {e}")
    print(traceback.format_exc())

print("\n--- Done ---")
