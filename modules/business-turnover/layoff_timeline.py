import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# Read the data
df = pd.read_csv("restructure_data/work.csv")

# Convert date to datetime and extract month-year
df['date'] = pd.to_datetime(df['date'])
df['month_year'] = df['date'].dt.strftime('%Y-%m')

# Count unique workers per month
monthly_workers = df.groupby('month_year')['participantId'].nunique().reset_index()
monthly_workers.columns = ['month_year', 'worker_count']

# Calculate month-over-month change
monthly_workers['previous'] = monthly_workers['worker_count'].shift(1)
monthly_workers['change'] = monthly_workers['worker_count'] - monthly_workers['previous']
monthly_workers['pct_change'] = (monthly_workers['change'] / monthly_workers['previous'] * 100).round(1)

# Sort by date for proper timeline
monthly_workers['date'] = pd.to_datetime(monthly_workers['month_year'] + '-01')
monthly_workers = monthly_workers.sort_values('date')

# Create figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add area chart for total workers
fig.add_trace(
    go.Scatter(
        x=monthly_workers['month_year'],
        y=monthly_workers['worker_count'],
        fill='tozeroy',
        name='Total Workers',
        line=dict(width=2, color='rgba(55, 128, 191, 0.7)'),
        fillcolor='rgba(55, 128, 191, 0.2)'
    )
)

# Add bar chart for monthly changes
fig.add_trace(
    go.Bar(
        x=monthly_workers['month_year'],
        y=monthly_workers['change'],
        name='Monthly Change',
        marker_color=monthly_workers['change'].apply(
            lambda x: 'rgba(255, 50, 50, 0.6)' if x < 0 else 'rgba(50, 200, 50, 0.6)'
        )
    ),
    secondary_y=True
)

# Add markers for significant events
significant_months = monthly_workers[monthly_workers['pct_change'].abs() > 5]
fig.add_trace(
    go.Scatter(
        x=significant_months['month_year'],
        y=significant_months['worker_count'],
        mode='markers+text',
        marker=dict(
            size=12,
            symbol='circle',
            color='rgba(255, 182, 0, 0.9)',
            line=dict(width=2, color='rgba(0, 0, 0, 0.5)')
        ),
        text=significant_months['pct_change'].apply(lambda x: f"{x:+.1f}%"),
        textposition="top center",
        name='Significant Changes',
        hoverinfo='text',
        hovertext=significant_months.apply(
            lambda row: f"Date: {row['month_year']}<br>Workers: {row['worker_count']}<br>Change: {row['change']} ({row['pct_change']}%)",
            axis=1
        )
    )
)

# Calculate and add trendline
x_numeric = np.arange(len(monthly_workers))
z = np.polyfit(x_numeric, monthly_workers['worker_count'], 1)
p = np.poly1d(z)
fig.add_trace(
    go.Scatter(
        x=monthly_workers['month_year'],
        y=p(x_numeric),
        mode='lines',
        line=dict(color='rgba(0, 0, 0, 0.5)', width=2, dash='dash'),
        name='Trend'
    )
)

# Update layout
fig.update_layout(
    title={
        'text': 'Working Population Timeline (18-Month Period)',
        'y':0.95,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': dict(size=24)
    },
    legend=dict(
        x=0.01,
        y=0.99,
        bgcolor='rgba(255, 255, 255, 0.8)',
        bordercolor='rgba(0, 0, 0, 0.3)',
        borderwidth=1
    ),
    hovermode="x unified",
    plot_bgcolor='rgba(240, 240, 240, 0.8)',
    xaxis=dict(
        title='Month',
        tickangle=-45,
        gridcolor='white',
        showgrid=True
    ),
    yaxis=dict(
        title='Total Number of Workers',
        gridcolor='white',
        showgrid=True
    ),
    yaxis2=dict(
        title='Monthly Change',
        gridcolor='white',
        showgrid=False,
        overlaying='y',
        side='right'
    ),
    margin=dict(l=80, r=80, t=100, b=80),
    height=700,
    template='plotly_white'
)

# Add annotations for context
year_months = sorted(monthly_workers['month_year'].unique())
if len(year_months) >= 3:
    quarter_points = [year_months[0], year_months[len(year_months)//2], year_months[-1]]
    annotations = [
        dict(
            x=quarter,
            y=monthly_workers[monthly_workers['month_year']==quarter]['worker_count'].values[0],
            xref="x", yref="y",
            text=f"Q{i+1}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            font=dict(size=12)
        ) for i, quarter in enumerate(quarter_points)
    ]
    fig.update_layout(annotations=annotations)

# Add hover template
fig.update_traces(
    hovertemplate="<b>%{x}</b><br>Workers: %{y}<extra></extra>",
    selector=dict(name='Total Workers')
)

fig.update_traces(
    hovertemplate="<b>%{x}</b><br>Change: %{y}<extra></extra>",
    selector=dict(name='Monthly Change')
)

# Save the interactive HTML
fig.write_html("layoff_timeline_interactive.html")