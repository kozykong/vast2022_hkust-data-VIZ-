import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shapely import wkt
import plotly.express as px

# Load the data
print("Loading data...")
work_df = pd.read_csv("restructure_data/workers_by_company_month.csv")
employers_df = pd.read_csv("Attributes/Employers.csv")
buildings_df = pd.read_csv("Attributes/Buildings.csv")
print(f"Loaded {len(work_df)} rows from workers data")
print(f"Loaded {len(employers_df)} rows from employers data")
print(f"Loaded {len(buildings_df)} rows from buildings data")

# Print column names to verify structure
print(f"Workers columns: {work_df.columns.tolist()}")
print(f"Employers columns: {employers_df.columns.tolist()}")

# Get first month data (March 2022)
march_data = work_df[work_df['month'] == '2022-03'].copy()
print(f"Found {len(march_data)} companies in March 2022")

# Get second month data (April 2022)
april_data = work_df[work_df['month'] == '2022-04'].copy()
print(f"Found {len(april_data)} companies in April 2022")

# Prepare data for map
map_data = []

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
        map_data.append({
            'company_id': company_id,
            'original_size': march_count,
            'layoffs': layoff_count,
            'layoff_percentage': (layoff_count / march_count * 100) if march_count > 0 else 0
        })

# Convert to DataFrame
map_df = pd.DataFrame(map_data)
print(f"Found {len(map_df)} companies with layoffs")

if len(map_df) > 0:
    print("Sample layoff data:")
    print(map_df.head())
    
    # Add company size category
    def assign_category(size):
        if size >= 10:
            return "Large (10+ employees)"
        elif size >= 5:
            return "Medium (5-9 employees)"
        else:
            return "Small (<5 employees)"
    
    map_df['size_category'] = map_df['original_size'].apply(assign_category)
    
    # Extract coordinates from location column in employers_df
    print("Parsing location data...")
    # Extract coordinates using string operations
    def parse_point_coordinates(point_str):
        coords = point_str.replace('POINT (', '').replace(')', '').split()
        return float(coords[0]), float(coords[1])
    
    employers_df['x'], employers_df['y'] = zip(*employers_df['location'].apply(parse_point_coordinates))
    
    # Merge with map_df to get location data
    map_df = map_df.merge(
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
    
    # Now create the map with buildings and layoffs using Plotly
    print("Creating interactive map visualization...")
    
    # Create a Plotly figure
    fig = go.Figure()
    
    # Process buildings data for Plotly
    building_polygons = []
    for _, building in buildings_df.iterrows():
        # Parse the polygon string using shapely's wkt loader
        polygon_str = building['location']
        polygon = wkt.loads(polygon_str)
        
        # Get the exterior coordinates of the polygon
        x, y = polygon.exterior.xy
        
        # Add polygon to the figure
        fig.add_trace(go.Scatter(
            x=list(x) + [x[0]],  # Close the polygon by adding the first point at the end
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
                len=0.5,  # Make colorbar 50% of the plot height
                thickness=15,  # Make colorbar thinner
                y=0.5,  # Center it vertically
                x=0.8,  # Move colorbar even closer to the map
            ),
            line=dict(width=1, color='gray')  # Gray outline for circles
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
        title={
            'text': "Layoffs by Company from March to April 2022",
            'x': 0.55,  # Center the title horizontally
            'y': 0.9,  # Position at top
            'xanchor': 'center'  # Anchor point for centering
        },
        autosize=True,
        width=1200,
        height=800,
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
            scaleratio=1  # To maintain aspect ratio
        ),
        legend=dict(
            yanchor="bottom",
            y=0.01,  # Position at bottom
            xanchor="right",
            x=0.85  # Position at right
        )
    )
    
    # Compute buffer around data bounds to set appropriate axis ranges
    x_buffer = (map_df['x'].max() - map_df['x'].min()) * 0.1
    y_buffer = (map_df['y'].max() - map_df['y'].min()) * 0.1
    
    fig.update_xaxes(
        range=[map_df['x'].min() - x_buffer, map_df['x'].max() + x_buffer]
    )
    fig.update_yaxes(
        range=[map_df['y'].min() - y_buffer, map_df['y'].max() + y_buffer]
    )
    
    # Save the figure as HTML
    fig.write_html("layoff_map.html")
    print("Interactive map saved as layoff_map.html")
    
else:
    print("ERROR: No layoffs detected in the data") 