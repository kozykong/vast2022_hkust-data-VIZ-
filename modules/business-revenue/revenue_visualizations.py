"""
revenue_visualizations.py
=========================
Generates two interactive Plotly visualizations for the Business Revenue module:

  1. Animated scatter plot — Weekly Revenue vs. Foot Traffic per venue
     (X: check-ins, Y: revenue, Size: avg spending per visit, Color: venue type)
     Includes a timeline slider and play button for week-by-week animation.

  2. Dual Y-axis line chart — Weekly trends of total spending and check-ins
     by venue type (Pub vs. Restaurant).

Outputs:
  revenue_vs_traffic_animated.html
  weekly_trends_by_venue_type.html

Usage:
  python revenue_visualizations.py
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

print("Generating Business Revenue visualizations...")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DATA_DIR = "data"
VENUE_DATA_FILE = os.path.join(DATA_DIR, "weekly_venue_revenue_traffic.csv")
TYPE_DATA_FILE = os.path.join(DATA_DIR, "weekly_revenue_traffic_by_type.csv")


# ──────────────────────────────────────────────
# Load Data
# ──────────────────────────────────────────────
print("Loading preprocessed data...")
df_venue = pd.read_csv(VENUE_DATA_FILE, parse_dates=["week"])
df_type = pd.read_csv(TYPE_DATA_FILE, parse_dates=["week"])

df_venue["week_str"] = df_venue["week"].dt.strftime("%Y-%m-%d")
df_type["week_str"] = df_type["week"].dt.strftime("%Y-%m-%d")

print(f"  Per-venue data: {len(df_venue)} rows, {df_venue['venueId'].nunique()} venues")
print(f"  By-type data: {len(df_type)} rows")


# ──────────────────────────────────────────────
# Visualization 1: Animated Scatter Plot
# Revenue vs. Foot Traffic per Venue (by Week)
# ──────────────────────────────────────────────
print("\nCreating animated scatter plot...")

# Aggregate per venue per week for cleaner animation
df_anim = df_venue.copy()
df_anim["avg_spend_per_visit"] = df_anim["avg_spend_per_visit"].clip(lower=1)

fig_scatter = px.scatter(
    df_anim,
    x="check_ins",
    y="total_revenue",
    size="avg_spend_per_visit",
    color="venue_type",
    animation_frame="week_str",
    hover_name="venueId",
    hover_data={
        "check_ins": True,
        "total_revenue": ":.2f",
        "avg_spend_per_visit": ":.2f",
        "venue_type": True,
        "week_str": False,
    },
    labels={
        "check_ins": "Number of Check-ins (Foot Traffic)",
        "total_revenue": "Total Spending (Revenue)",
        "avg_spend_per_visit": "Avg Spending per Visit",
        "venue_type": "Venue Type",
    },
    title="Weekly Revenue vs. Foot Traffic Correlation for Pubs and Restaurants",
    color_discrete_map={"Pub": "#636EFA", "Restaurant": "#EF553B"},
    size_max=40,
)

fig_scatter.update_layout(
    xaxis_title="Number of Check-ins (Foot Traffic)",
    yaxis_title="Total Spending (Revenue)",
    height=700,
    template="plotly_white",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
)

# Fix axis ranges across all animation frames for consistent comparison
max_checkins = df_anim["check_ins"].quantile(0.98) * 1.1
max_revenue = df_anim["total_revenue"].quantile(0.98) * 1.1
fig_scatter.update_xaxes(range=[0, max(max_checkins, 100)])
fig_scatter.update_yaxes(range=[0, max(max_revenue, 100)])

# Slow down animation speed
fig_scatter.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 500
fig_scatter.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 300

output_scatter = "revenue_vs_traffic_animated.html"
fig_scatter.write_html(output_scatter)
print(f"  Saved: {output_scatter}")


# ──────────────────────────────────────────────
# Visualization 2: Dual Y-Axis Weekly Trends
# Total Spending + Check-ins by Venue Type
# ──────────────────────────────────────────────
print("\nCreating dual Y-axis weekly trend chart...")

fig_trends = make_subplots(specs=[[{"secondary_y": True}]])

colors = {"Pub": "#636EFA", "Restaurant": "#EF553B"}

for venue_type in ["Pub", "Restaurant"]:
    df_vt = df_type[df_type["venue_type"] == venue_type].sort_values("week")

    # Revenue line (left Y-axis)
    fig_trends.add_trace(
        go.Scatter(
            x=df_vt["week"],
            y=df_vt["total_revenue"],
            name=f"{venue_type} Spending",
            line=dict(color=colors[venue_type], width=2),
            mode="lines",
            hovertemplate=f"{venue_type} Revenue: $%{{y:,.0f}}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Check-ins line (right Y-axis, dashed)
    fig_trends.add_trace(
        go.Scatter(
            x=df_vt["week"],
            y=df_vt["total_check_ins"],
            name=f"{venue_type} Check-ins",
            line=dict(color=colors[venue_type], width=2, dash="dash"),
            mode="lines",
            hovertemplate=f"{venue_type} Check-ins: %{{y:,}}<extra></extra>",
        ),
        secondary_y=True,
    )

fig_trends.update_layout(
    title={
        "text": "Weekly Total Spending and Check-ins by Venue Type",
        "x": 0.5,
        "xanchor": "center",
        "font": dict(size=18),
    },
    height=600,
    template="plotly_white",
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5,
    ),
    margin=dict(l=80, r=80, t=100, b=60),
)

fig_trends.update_xaxes(title_text="Week")
fig_trends.update_yaxes(title_text="Total Spending (Revenue)", secondary_y=False)
fig_trends.update_yaxes(title_text="Total Check-ins (Foot Traffic)", secondary_y=True)

output_trends = "weekly_trends_by_venue_type.html"
fig_trends.write_html(output_trends)
print(f"  Saved: {output_trends}")

print("\n--- Done ---")
