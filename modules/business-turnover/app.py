import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shapely import wkt
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import json

print("Loading data...")
# Load all required datasets
work_df = pd.read_csv("restructure_data/workers_by_company_month.csv")
employers_df = pd.read_csv("Attributes/Employers.csv")
buildings_df = pd.read_csv("Attributes/Buildings.csv")
print(f"Loaded {len(work_df)} rows from workers data")
print(f"Loaded {len(employers_df)} rows from employers data")
print(f"Loaded {len(buildings_df)} rows from buildings data")

# Print column names to verify structure
print(f"Workers columns: {work_df.columns.tolist()}")

# Get first month data (March 2022)
march_data = work_df[work_df['month'] == '2022-03'].copy()
print(f"Found {len(march_data)} companies in March 2022")

# Get second month data (April 2022)
april_data = work_df[work_df['month'] == '2022-04'].copy()
print(f"Found {len(april_data)} companies in April 2022")

# Prepare data for visualizations
layoff_data = []

# Calculate layoffs between March and April
for _, company in march_data.iterrows():
    company_id = company['employerId']
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
        layoff_data.append({
            'company_id': company_id,
            'original_size': march_count,
            'layoffs': layoff_count,
            'layoff_percentage': (layoff_count / march_count * 100) if march_count > 0 else 0
        })

# Convert to DataFrame
layoff_df = pd.DataFrame(layoff_data)
print(f"Found {len(layoff_df)} companies with layoffs")

if len(layoff_df) == 0:
    print("ERROR: No layoffs detected in the data")
    exit(1)

print("Sample layoff data:")
print(layoff_df.head())

# Add company size category
def assign_category(size):
    if size >= 10:
        return "Large (10+ employees)"
    elif size >= 5:
        return "Medium (5-9 employees)"
    else:
        return "Small (<5 employees)"

layoff_df['size_category'] = layoff_df['original_size'].apply(assign_category)

# Extract coordinates from location column in employers_df
print("Parsing location data...")
# Extract coordinates using string operations
def parse_point_coordinates(point_str):
    coords = point_str.replace('POINT (', '').replace(')', '').split()
    return float(coords[0]), float(coords[1])

employers_df['x'], employers_df['y'] = zip(*employers_df['location'].apply(parse_point_coordinates))

# Merge with layoff_df to get location data
map_df = layoff_df.merge(
    employers_df[['employerId', 'x', 'y', 'buildingId']], 
    left_on='company_id', 
    right_on='employerId', 
    how='left'
)

# Use buildingId as name
map_df['name'] = map_df['buildingId'].fillna(map_df['company_id']).astype(str)

# Check for missing location data
missing_locations = map_df[map_df['x'].isna() | map_df['y'].isna()]
if len(missing_locations) > 0:
    print(f"Warning: {len(missing_locations)} companies have missing location data")
    # Drop companies with missing locations
    map_df = map_df.dropna(subset=['x', 'y'])
    print(f"{len(map_df)} companies remain with valid location data")

# Function to create the layoff map
def create_layoff_map():
    # Create a Plotly figure
    fig = go.Figure()
    
    # Process buildings data for Plotly
    for _, building in buildings_df.iterrows():
        # Parse the polygon string using shapely's wkt loader
        polygon_str = building['location']
        polygon = wkt.loads(polygon_str)
        
        # Get the exterior coordinates of the polygon
        x, y = polygon.exterior.xy
        
        # Add polygon to the figure
        fig.add_trace(go.Scatter(
            x=list(x) + [x[0]],  # Close the polygon
            y=list(y) + [y[0]],
            fill="toself",
            fillcolor='rgba(0, 0, 0, 0)',  # Transparent fill
            line=dict(color='rgba(80, 80, 80, 1)', width=1),  # Darker line for buildings
            mode='lines',
            hoverinfo='skip',
            showlegend=False
        ))
    
    # Add employer points with layoff information
    fig.add_trace(go.Scatter(
        x=map_df['x'],
        y=map_df['y'],
        mode='markers',
        marker=dict(
            size=map_df['layoffs'].apply(lambda x: max(15, x*3)),
            color=map_df['layoffs'],
            colorscale='Reds',
            colorbar=dict(
                title="Layoffs",
                len=0.5,
                thickness=15,
                y=0.5,
                x=0.88,
            ),
            line=dict(width=1, color='gray')
        ),
        text=map_df.apply(
            lambda row: f"ID: {row['company_id']}<br>" +
                        f"Original Size: {row['original_size']}<br>" +
                        f"Layoffs: {row['layoffs']}<br>" +
                        f"Layoff %: {row['layoff_percentage']:.1f}%",
            axis=1
        ),
        hoverinfo='text',
        name='Employers with Layoffs'
    ))
    
    # Set layout
    fig.update_layout(
        autosize=True,
        height=700,
        showlegend=True,
        hovermode='closest',
        paper_bgcolor='white',
        plot_bgcolor='white',
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.10,
            xanchor="right",
            x=0.90,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
    )
    
    # Compute buffer around data bounds to set appropriate axis ranges
    x_buffer = (map_df['x'].max() - map_df['x'].min()) * 0.01
    y_buffer = (map_df['y'].max() - map_df['y'].min()) * 0.01
    
    fig.update_xaxes(range=[map_df['x'].min() - x_buffer, map_df['x'].max() + x_buffer])
    fig.update_yaxes(range=[map_df['y'].min() - y_buffer, map_df['y'].max() + y_buffer])
    
    return fig

# Function to create the layoff treemap
def create_layoff_treemap():
    # Create the main figure
    fig = go.Figure()
    
    # Create data for hierarchical treemap (layoff count)
    labels = ["All Companies"]  # Root node
    parents = [""]  # Root has no parent
    values = [layoff_df['layoffs'].sum()]  # Sum of all layoffs
    
    # Add category nodes
    for category in sorted(layoff_df['size_category'].unique()):
        labels.append(category)
        parents.append("All Companies")
        values.append(layoff_df[layoff_df['size_category'] == category]['layoffs'].sum())
    
    # Add company nodes with their parents as categories
    for _, company in layoff_df.iterrows():
        labels.append(str(company['company_id']))
        parents.append(company['size_category'])
        values.append(company['layoffs'])
    
    # Create customdata for hovering
    # First calculate aggregated data for categories
    category_data = {}
    for category in layoff_df['size_category'].unique():
        category_companies = layoff_df[layoff_df['size_category'] == category]
        category_data[category] = {
            'total_original_size': category_companies['original_size'].sum(),
            'total_layoffs': category_companies['layoffs'].sum(),
            'avg_layoff_pct': (category_companies['layoffs'].sum() / category_companies['original_size'].sum() * 100)
        }
    
    # Start with data for root node (total of all companies)
    custom_sizes = [layoff_df['original_size'].sum()]
    custom_layoffs = [layoff_df['layoffs'].sum()]
    custom_layoff_pct = [(layoff_df['layoffs'].sum() / layoff_df['original_size'].sum() * 100)]
    
    # Add data for category nodes
    for category in sorted(layoff_df['size_category'].unique()):
        custom_sizes.append(category_data[category]['total_original_size'])
        custom_layoffs.append(category_data[category]['total_layoffs'])
        custom_layoff_pct.append(category_data[category]['avg_layoff_pct'])
    
    # Add company-specific data
    for _, company in layoff_df.iterrows():
        custom_sizes.append(company['original_size'])
        custom_layoffs.append(company['layoffs'])
        custom_layoff_pct.append(company['layoff_percentage'])
    
    # Create color array for all nodes
    color_array = [-1] * (len(layoff_df['size_category'].unique()) + 1)
    
    # Add company-specific size as color values
    for _, company in layoff_df.iterrows():
        color_array.append(company['original_size'])
    
    # Create line width array to only show borders on categories
    line_width_array = []
    line_width_array.append(1)  # Root node
    for _ in range(len(layoff_df['size_category'].unique())):
        line_width_array.append(1)  # Category nodes
    for _ in range(len(layoff_df)):
        line_width_array.append(0)  # Company nodes
    
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
            colors=color_array,
            colorscale='Blues',
            line=dict(
                width=line_width_array,
                color='gray'
            ),
            colorbar=dict(
                title="Company<br>Size",
                thickness=15,
                len=0.3,
                x=0.82,
                y=1.13,  # Move it higher
                yanchor='top',  # Anchor to top
                orientation='h',
                tickvals=[min(1, min(layoff_df['original_size'])), 
                          max(layoff_df['original_size'])],
                ticktext=["Small", "Large"]
            ),
            cmin=min(1, min(layoff_df['original_size'])),
            cmid=5,
            cmax=max(layoff_df['original_size'])
        ),
        branchvalues="total"
    ))
    
    # Add much larger top margin to prevent overlap with the color scale
    fig.update_layout(
        margin=dict(t=150, l=10, r=10, b=10)
    )
    
    return fig

# Function to create summary statistics
def create_summary_stats():
    # Using the original March data for total count (including companies without layoffs)
    total_companies = len(march_data)
    total_original_workers = march_data['worker_count'].sum()
    
    # Total layoffs calculation remains the same
    total_layoffs = layoff_df['layoffs'].sum()
    
    # This now reflects the true percentage across all companies
    avg_layoff_pct = (total_layoffs / total_original_workers) * 100
    
    # Count layoff companies by size category
    size_counts = layoff_df['size_category'].value_counts().to_dict()
    
    # Count of companies that had layoffs (for comparison)
    companies_with_layoffs = len(layoff_df)
    
    return {
        'total_companies': total_companies,
        'companies_with_layoffs': companies_with_layoffs,
        'total_original_workers': total_original_workers,
        'total_layoffs': total_layoffs,
        'avg_layoff_pct': avg_layoff_pct,
        'size_counts': size_counts
    }

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Create the app layout
app.layout = html.Div([
    html.H1("Layoff Dashboard - March to April 2022", style={'textAlign': 'center', 'margin': '20px'}),
    
    html.Div([
        # Summary statistics at the top
        html.Div([
            html.Div([
                html.H4("Companies with Layoffs / Total"),
                html.H2(id="companies-ratio", style={'color': '#C41E3A'})
            ], className='stat-box'),
            
            html.Div([
                html.H4("Total Workers (March 2022)"),
                html.H2(id="total-workers", style={'color': '#1E3AC4'})
            ], className='stat-box'),
            
            html.Div([
                html.H4("Total Workers Laid Off"),
                html.H2(id="total-layoffs", style={'color': '#C41E3A'})
            ], className='stat-box'),
            
            html.Div([
                html.H4("Overall Layoff Percentage"),
                html.H2(id="avg-layoff-pct", style={'color': '#C41E3A'})
            ], className='stat-box'),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'margin': '20px 0'}),
        
        # Visualization tabs
        dcc.Tabs([
            dcc.Tab(label='Map View', children=[
                html.Div([
                    dcc.Graph(
                        id='layoff-map',
                        figure=create_layoff_map(),
                        config={'responsive': True},
                        style={'height': '900px', 'width': '100%'}
                    )
                ], style={'width': '100%', 'padding': '0px 0px'})
            ]),
            
            dcc.Tab(label='Treemap View', children=[
                html.Div([
                    dcc.Graph(
                        id='layoff-treemap',
                        figure=create_layoff_treemap(),
                        config={'responsive': True},
                        style={'height': '700px', 'width': '100%'}
                    )
                ], style={'width': '100%', 'padding': '0px 0px'})
            ]),
        ], style={'width': '100%'}),
        
        # Store component to hold the summary stats
        dcc.Store(
            id='summary-stats',
            data=create_summary_stats()
        )
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'})
])

# Callback to update summary statistics
@app.callback(
    [Output('companies-ratio', 'children'),
     Output('total-workers', 'children'),
     Output('total-layoffs', 'children'),
     Output('avg-layoff-pct', 'children')],
    [Input('summary-stats', 'data')]
)
def update_summary_stats(data):
    return (
        f"{data['companies_with_layoffs']:,} / {data['total_companies']:,}",
        f"{data['total_original_workers']:,}",
        f"{data['total_layoffs']:,}",
        f"{data['avg_layoff_pct']:.1f}%"
    )

# Add custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Layoff Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                background-color: #f7f7f7;
            }
            .stat-box {
                background-color: white;
                border-radius: 5px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                flex: 1;
                margin: 0 10px;
            }
            .stat-box h4 {
                margin: 0 0 10px 0;
                font-weight: normal;
                color: #555;
            }
            .stat-box h2 {
                margin: 0;
                font-size: 24px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Run the app
if __name__ == '__main__':
    print("Starting Dash server...")
    app.run(debug=True)
    print("Dashboard is running at http://127.0.0.1:8050/")
