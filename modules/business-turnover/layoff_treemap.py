import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import ast

# Load the data
print("Loading data...")
df = pd.read_csv("restructure_data/workers_by_company_month.csv")
print(f"Loaded {len(df)} rows")

# Print column names to verify structure
print(f"Columns: {df.columns.tolist()}")

# Get first month data (March 2022)
march_data = df[df['month'] == '2022-03'].copy()
print(f"Found {len(march_data)} companies in March 2022")

# Get second month data (April 2022)
april_data = df[df['month'] == '2022-04'].copy()
print(f"Found {len(april_data)} companies in April 2022")

# Prepare data for treemap
treemap_data = []

# Convert worker counts from the "worker_count" column directly
for _, company in march_data.iterrows():
    company_id = company['employerId']
    # Get worker count directly from the worker_count column (not 'count')
    march_count = company['worker_count']
    
    # Find if company exists in April
    april_company = april_data[april_data['employerId'] == company_id]
    if len(april_company) > 0:
        april_count = april_company.iloc[0]['worker_count']
        layoff_count = max(0, march_count - april_count)  # Prevent negative values
    else:
        # Company doesn't exist in April, all workers laid off
        layoff_count = march_count
    
    # Only include companies with layoffs
    if layoff_count > 0:
        treemap_data.append({
            'company_id': company_id,
            'original_size': march_count,
            'layoffs': layoff_count,
            'layoff_percentage': (layoff_count / march_count * 100) if march_count > 0 else 0
        })

# Convert to DataFrame
treemap_df = pd.DataFrame(treemap_data)
print(f"Found {len(treemap_df)} companies with layoffs")

if len(treemap_df) > 0:
    print("Sample layoff data:")
    print(treemap_df.head())
    
    # Add company size category
    def assign_category(size):
        if size >= 10:
            return "Large (10+ employees)"
        elif size >= 5:
            return "Medium (5-9 employees)"
        else:
            return "Small (<5 employees)"
    
    treemap_df['size_category'] = treemap_df['original_size'].apply(assign_category)
    
    # Count companies in each category
    category_counts = treemap_df['size_category'].value_counts()
    print("\nCompanies by size category:")
    for category, count in category_counts.items():
        print(f"{category}: {count} companies")
    
    # Create the main figure
    fig = go.Figure()
    
    # Create data for hierarchical treemap (layoff count)
    labels = ["All Companies"]  # Root node
    parents = [""]  # Root has no parent
    values = [treemap_df['layoffs'].sum()]  # Sum of all layoffs
    
    # Add category nodes
    for category in sorted(treemap_df['size_category'].unique()):
        labels.append(category)
        parents.append("All Companies")
        values.append(treemap_df[treemap_df['size_category'] == category]['layoffs'].sum())
    
    # Add company nodes with their parents as categories
    for _, company in treemap_df.iterrows():
        labels.append(str(company['company_id']))
        parents.append(company['size_category'])
        values.append(company['layoffs'])
    
    # Create customdata for hovering
    # First calculate aggregated data for categories
    category_data = {}
    for category in treemap_df['size_category'].unique():
        category_companies = treemap_df[treemap_df['size_category'] == category]
        category_data[category] = {
            'total_original_size': category_companies['original_size'].sum(),
            'total_layoffs': category_companies['layoffs'].sum(),
            'avg_layoff_pct': (category_companies['layoffs'].sum() / category_companies['original_size'].sum() * 100)
        }
    
    # Start with data for root node (total of all companies)
    custom_sizes = [treemap_df['original_size'].sum()]
    custom_layoffs = [treemap_df['layoffs'].sum()]
    custom_layoff_pct = [(treemap_df['layoffs'].sum() / treemap_df['original_size'].sum() * 100)]
    
    # Add data for category nodes
    for category in sorted(treemap_df['size_category'].unique()):
        custom_sizes.append(category_data[category]['total_original_size'])
        custom_layoffs.append(category_data[category]['total_layoffs'])
        custom_layoff_pct.append(category_data[category]['avg_layoff_pct'])
    
    # Add company-specific data
    for _, company in treemap_df.iterrows():
        custom_sizes.append(company['original_size'])
        custom_layoffs.append(company['layoffs'])
        custom_layoff_pct.append(company['layoff_percentage'])
    
    # Create color array for all nodes
    # Start with a default value for root and category nodes
    # We'll use a value outside our data range to ensure they receive a neutral color
    color_array = [-1] * (len(treemap_df['size_category'].unique()) + 1)
    
    # Add company-specific size as color values
    for _, company in treemap_df.iterrows():
        color_array.append(company['original_size'])
    
    # Create line width array to only show borders on categories
    # First create an array with the same length as labels
    line_width_array = []
    # Root node has border
    line_width_array.append(1)  # Changed from 0 to 1 to add gray outline to "All Companies"
    # Category nodes have gray border
    for _ in range(len(treemap_df['size_category'].unique())):
        line_width_array.append(1)
    # Company nodes have no border
    for _ in range(len(treemap_df)):
        line_width_array.append(0)
    
    # Add the treemap (sized by layoff count)
    fig.add_trace(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        customdata=np.column_stack([custom_sizes, custom_layoffs, custom_layoff_pct]),
        hovertemplate='<b>%{label}</b><br>' +
                      '<b>Original Size:</b> %{customdata[0]}<br>' +
                      '<b>Layoffs:</b> %{customdata[1]}<br>' +
                      '<b>Layoff %:</b> %{customdata[2]:.1f}%<extra></extra>',
        marker=dict(
            colors=color_array,  # Use company size to determine color
            colorscale='Blues',  # Use Blues colorscale
            line=dict(
                width=line_width_array,  # Apply different line widths
                color='gray'  # Set line color to gray
            ),
            colorbar=dict(
                title="Company<br>Size",
                thickness=20,
                len=0.6,
                x=1.02,
                y=0.5,
                tickvals=[min(1, min(treemap_df['original_size'])), 
                          max(treemap_df['original_size'])],
                ticktext=["Small", "Large"]
            ),
            # Set range to prevent root/category nodes from affecting color scale
            cmin=min(1, min(treemap_df['original_size'])),
            cmid=5,  # Medium company threshold
            cmax=max(treemap_df['original_size'])
        ),
        branchvalues="total"  # To ensure values add up correctly
    ))
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'Company Layoffs from March to April 2022',
            'y': 0.95,  # Lower the title position slightly
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        width=1200,
        height=800,
        margin=dict(t=70, l=25, r=25, b=25),  # Increased top margin
        coloraxis_colorbar=dict(
            title="Company Size"
        )
    )
    
    # Save as HTML
    fig.write_html("layoff_treemap.html")
    print("HTML file saved.")
else:
    print("ERROR: No layoffs detected in the data")
