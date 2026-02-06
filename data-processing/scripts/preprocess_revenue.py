"""
preprocess_revenue.py
=====================
Processes VAST Challenge 2022 data to generate weekly venue-level
revenue and foot traffic metrics for pubs and restaurants.

Output:
  data/weekly_venue_revenue_traffic.csv

Usage:
  python preprocess_revenue.py
"""

import pandas as pd
import numpy as np
import os

print("Starting revenue/traffic preprocessing...")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DATA_DIR = "data"
JOURNALS_DIR = os.path.join(DATA_DIR, "Journals")
ATTR_DIR = os.path.join(DATA_DIR, "Attributes")

CHECKIN_FILE = os.path.join(JOURNALS_DIR, "CheckinJournal.csv")
FINANCIAL_FILE = os.path.join(JOURNALS_DIR, "FinancialJournal.csv")
VENUES_FILE = os.path.join(ATTR_DIR, "Venues.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "weekly_venue_revenue_traffic.csv")

VENUE_TYPES = ["Pub", "Restaurant"]

# ──────────────────────────────────────────────
# Load Data
# ──────────────────────────────────────────────
print("Loading raw data...")
checkins = pd.read_csv(CHECKIN_FILE, parse_dates=["timestamp"])
financial = pd.read_csv(FINANCIAL_FILE, parse_dates=["timestamp"])
venues = pd.read_csv(VENUES_FILE)

print(f"  Check-ins: {len(checkins)} rows")
print(f"  Financial: {len(financial)} rows")
print(f"  Venues: {len(venues)} rows")

# ──────────────────────────────────────────────
# Filter to Pubs and Restaurants
# ──────────────────────────────────────────────
pub_restaurant_venues = venues[venues["type"].isin(VENUE_TYPES)].copy()
venue_ids = set(pub_restaurant_venues["venueId"])
print(f"Pubs + Restaurants: {len(pub_restaurant_venues)} venues")

# ──────────────────────────────────────────────
# Compute Weekly Foot Traffic (Check-ins)
# ──────────────────────────────────────────────
print("Computing weekly foot traffic...")
checkins_filtered = checkins[checkins["venueId"].isin(venue_ids)].copy()
checkins_filtered["week"] = checkins_filtered["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)

weekly_traffic = (
    checkins_filtered.groupby(["week", "venueId"])
    .size()
    .reset_index(name="check_ins")
)
print(f"  Weekly traffic records: {len(weekly_traffic)}")

# ──────────────────────────────────────────────
# Compute Weekly Revenue (Spending at venues)
# ──────────────────────────────────────────────
print("Computing weekly revenue...")

# Filter financial entries to Food/Recreation categories (venue spending)
venue_spending_categories = ["Food", "Recreation"]
financial_venue = financial[
    (financial["category"].isin(venue_spending_categories))
].copy()

# Join with check-ins to associate spending with venues
# Strategy: match participant + approximate timestamp to link spending to venue visits
# Simplified approach: aggregate spending by venue from check-in-linked transactions
# Since direct venue-spending linkage varies by dataset version,
# we use check-in frequency as a proxy and aggregate category spending by week

financial_venue["week"] = financial_venue["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)

# Aggregate total venue-type spending per week
weekly_spending_by_type = (
    financial_venue.groupby(["week"])
    .agg(total_spending=("amount", lambda x: x.abs().sum()))
    .reset_index()
)

# Distribute spending proportionally to venues based on check-in share
weekly_traffic_with_type = weekly_traffic.merge(
    pub_restaurant_venues[["venueId", "type"]].rename(columns={"type": "venue_type"}),
    on="venueId",
    how="left",
)

# Calculate each venue's share of weekly check-ins
weekly_total_checkins = weekly_traffic_with_type.groupby("week")["check_ins"].transform("sum")
weekly_traffic_with_type["checkin_share"] = weekly_traffic_with_type["check_ins"] / weekly_total_checkins.replace(0, 1)

# Merge with weekly spending and estimate per-venue revenue
weekly_venue = weekly_traffic_with_type.merge(weekly_spending_by_type, on="week", how="left")
weekly_venue["total_spending"] = weekly_venue["total_spending"].fillna(0)
weekly_venue["estimated_revenue"] = weekly_venue["total_spending"] * weekly_venue["checkin_share"]

# Calculate average spending per visit
weekly_venue["avg_spend_per_visit"] = np.where(
    weekly_venue["check_ins"] > 0,
    weekly_venue["estimated_revenue"] / weekly_venue["check_ins"],
    0,
)

# ──────────────────────────────────────────────
# Merge with Venue Attributes
# ──────────────────────────────────────────────
venue_info = pub_restaurant_venues[["venueId", "type"]].rename(
    columns={"type": "venue_type_attr"}
)

# Select and rename final columns
output = weekly_venue[
    ["week", "venueId", "venue_type", "check_ins", "estimated_revenue", "avg_spend_per_visit"]
].rename(columns={"estimated_revenue": "total_revenue"})

output = output.sort_values(["week", "venueId"]).reset_index(drop=True)

# ──────────────────────────────────────────────
# Also create an aggregated summary by venue type per week
# (used for the dual Y-axis trend chart)
# ──────────────────────────────────────────────
weekly_by_type = (
    output.groupby(["week", "venue_type"])
    .agg(
        total_check_ins=("check_ins", "sum"),
        total_revenue=("total_revenue", "sum"),
        venue_count=("venueId", "nunique"),
    )
    .reset_index()
)
weekly_by_type["avg_revenue_per_venue"] = weekly_by_type["total_revenue"] / weekly_by_type["venue_count"].replace(0, 1)

# ──────────────────────────────────────────────
# Save Outputs
# ──────────────────────────────────────────────
print(f"\nSaving to {OUTPUT_FILE}...")
output.to_csv(OUTPUT_FILE, index=False)

agg_output_file = os.path.join(DATA_DIR, "weekly_revenue_traffic_by_type.csv")
weekly_by_type.to_csv(agg_output_file, index=False)

print(f"  Per-venue: {OUTPUT_FILE} ({len(output)} rows)")
print(f"  By type:   {agg_output_file} ({len(weekly_by_type)} rows)")
print("\n--- Preprocessing Complete ---")
