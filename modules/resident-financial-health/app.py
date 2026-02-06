import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import traceback # Keep for debugging if needed

# --- Page Configuration ---
st.set_page_config(
    page_title="Grouped Financial Drilldown",
    layout="wide"
)

# --- Load and Prepare Data ---
@st.cache_data
def load_data(filepath):
    """Loads and preprocesses the monthly summary CSV."""
    try:
        df = pd.read_csv(filepath, parse_dates=['Month'])
        df['Month'] = pd.to_datetime(df['Month'])
        if df.empty:
            st.error("Error: Loaded DataFrame is empty.")
            return None
        print("Data loaded successfully.") # Console log

        # Define expected numeric columns + find expense cols
        numeric_cols = [
            'participantId', 'end_balance', 'net_monthly_change', 'total_amount_Income',
            'total_amount_Expense'
        ]
        expense_amount_cols = [col for col in df.columns if col.startswith('total_amount_') and col not in ['total_amount_Income', 'total_amount_Expense']]
        numeric_cols.extend(expense_amount_cols)

        # Coerce columns to numeric, initialize if missing
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                print(f"Warning: Column '{col}' not found. Initializing to 0.0")
                df[col] = 0.0 # Initialize missing numeric columns

        # Fill NaNs resulting from coercion with 0
        # Important to do AFTER coercion
        df.fillna(0.0, inplace=True)

        # Make participantId string for categorical use if needed
        df['participantId_str'] = df['participantId'].astype(str)
        return df
    except FileNotFoundError:
        st.error(f"Error: Could not find file '{filepath}'. Ensure it's in the 'data' subdirectory relative to the script.")
        return None
    except Exception as e:
        st.error(f"An error occurred loading or processing CSV: {e}")
        return None

data_root = 'data'
csv_file_path = f'{data_root}/monthly_financial_summary_detailed_all_participants.csv'
df = load_data(csv_file_path)

if df is None:
    st.stop()

# --- Get Unique Values for Widgets and Categories ---
try:
    participants = sorted(df['participantId'].unique()) # Needed if adding participant selector later
    months = sorted(df['Month'].unique())
    if not months: raise ValueError("No valid months found.")
    month_labels = [pd.Timestamp(m).strftime('%Y-%m') for m in months]

    # Identify expense category columns and create clean names map
    expense_amount_cols = [col for col in df.columns if col.startswith('total_amount_') and col not in ['total_amount_Income', 'total_amount_Expense']]
    expense_cols_map = {col: col.replace('total_amount_', '') for col in expense_amount_cols} # Map for melting later

except Exception as e:
     st.error(f"Error preparing widget data or identifying categories: {e}")
     st.stop()


# --- Sidebar Widgets ---
st.sidebar.header("Controls")
selected_month_label = st.sidebar.select_slider(
    "Select Month:",
    options=month_labels,
    value=month_labels[-1] if month_labels else None # Default to last available month
)

# Add slider for number of groups (quantiles)
num_groups = st.sidebar.slider(
    "Number of Balance Groups (Quantiles):",
    min_value=1,
    max_value=10, # Limit to avoid tiny groups
    value=10, # Default to 10 as in the image (changed from 4)
    step=1
)


if selected_month_label is None: st.stop()
selected_month = months[month_labels.index(selected_month_label)]

# --- Filter Data Based on Selected Month ---
df_month = df[df['Month'] == selected_month].copy()
if df_month.empty:
    st.warning(f"No data available for {selected_month_label}")
    st.stop()


# --- Main Panel ---
# Removed title for cleaner look matching image structure more closely
# st.title(f"Grouped Financial Drilldown for {selected_month_label}")

# --- Display Histogram (Removed as not in user's focus for this fix) ---
# st.header("Distribution of End of Month Balance")
# ... (histogram code omitted for brevity) ...

# --- Streamlit Sliders for Filtering ---
st.header("Filter Participants by Balance")

min_balance_overall = float(df_month['end_balance'].min())
max_balance_overall = float(df_month['end_balance'].max())
if max_balance_overall == min_balance_overall: max_balance_overall += 1.0 # Handle edge case
step_val = max(1.0, (max_balance_overall - min_balance_overall) / 100)

selected_min_balance, selected_max_balance = st.slider(
    "Select End Balance Range:",
    min_value=min_balance_overall,
    max_value=max_balance_overall,
    value=(min_balance_overall, max_balance_overall), # Default to full range
    step= step_val,
    format="$%.0f" # Format display values
)

# --- Filter DataFrame based on Slider Values ---
df_filtered = df_month[
    (df_month['end_balance'] >= selected_min_balance) &
    (df_month['end_balance'] <= selected_max_balance)
].copy() # Create a copy

num_filtered = len(df_filtered)
st.write(f"Processing {num_filtered} participants with balance between {selected_min_balance:,.0f} and {selected_max_balance:,.0f}.")


# --- Grouping and Aggregation within Filtered Data ---
st.header(f"Average Expense Breakdown by Balance Group ({num_groups} Quantiles)")

if num_filtered < num_groups:
    st.warning(f"Not enough participants ({num_filtered}) in the selected range to create {num_groups} distinct groups.")
elif num_filtered > 0 and expense_amount_cols: # Check we have participants and expense columns
    try:
        # --- Create Quantile Groups ---
        # Use pd.qcut to create bins based on quantiles
        # Handle potential duplicate edges by adding a small jitter if needed or using rank
        try:
            df_filtered['Balance Group'], quantile_bins = pd.qcut(
                df_filtered['end_balance'], q=num_groups, labels=False, retbins=True, duplicates='drop'
            )
        except ValueError as e:
             # If 'drop' doesn't work due to too many duplicates at boundaries, try ranking first
             if 'Bin edges must be unique' in str(e):
                 st.info("Duplicate bin edges encountered, using rank-based quantiles.")
                 df_filtered['Balance Group'] = pd.qcut(df_filtered['end_balance'].rank(method='first'), q=num_groups, labels=False, duplicates='drop')
                 # Re-calculate approximate bins for labels if possible (might be less precise)
                 min_b, max_b = df_filtered['end_balance'].min(), df_filtered['end_balance'].max()
                 quantile_bins = np.linspace(min_b, max_b, num_groups + 1) # Approximate bins
             else:
                 raise e # Re-raise other ValueErrors


        # Create descriptive labels, handling potential inconsistencies
        actual_num_groups = df_filtered['Balance Group'].nunique()
        if actual_num_groups != len(quantile_bins) - 1:
             st.warning(f"Could only create {actual_num_groups} distinct groups instead of {num_groups} due to data distribution. Labels might be approximate.")
             # Fallback label generation if bins don't match groups
             group_labels = [f"Group {i+1}" for i in range(actual_num_groups)]
             label_map = {i: f"Group {i+1}" for i in sorted(df_filtered['Balance Group'].unique())}

        else:
            # Original label generation when bins match groups
            group_labels = [f"Group {i+1} (${quantile_bins[i]:,.0f} - ${quantile_bins[i+1]:,.0f})" for i in range(len(quantile_bins) - 1)]
            label_map = {i: label for i, label in enumerate(group_labels)}

        # Map integer labels to descriptive labels
        df_filtered['Balance Group Label'] = df_filtered['Balance Group'].map(label_map)
        grouping_col = 'Balance Group Label'
        # Define sort order based on the generated labels (important for Altair)
        # Ensure sorting happens correctly even if fallback labels were used
        sort_order = sorted(df_filtered[grouping_col].unique(), key=lambda x: int(x.split(' ')[1].split('(')[0]))


        # --- Aggregate Average Expenses per Group ---
        cols_to_agg = [grouping_col] + expense_amount_cols
        if grouping_col in df_filtered.columns:
            df_agg = df_filtered[cols_to_agg].groupby(grouping_col, observed=False).mean().reset_index() # Use observed=False

            # --- Melt/Fold Data for Stacking ---
            df_melted = pd.melt(
                df_agg, id_vars=[grouping_col], value_vars=expense_amount_cols,
                var_name='Expense Column', value_name='Average Amount'
            )
            df_melted['Category'] = df_melted['Expense Column'].map(expense_cols_map)

            # Calculate positive magnitude for plotting/filtering
            # Using abs() is correct here, assuming expenses are negative but should be plotted positive
            df_melted['Avg Spending Magnitude'] = df_melted['Average Amount'].abs()

            # Filter out tiny values if needed (e.g., floating point noise)
            df_melted_filtered = df_melted[df_melted['Avg Spending Magnitude'] > 1e-9].copy()

            # --- Create Stacked Bar Chart ---
            if not df_melted_filtered.empty:
                chart_stacked_bar = alt.Chart(df_melted_filtered).mark_bar().encode(
                    # X-axis Configuration: Apply visibility improvements
                    x=alt.X(
                        grouping_col,
                        title='Balance Group within Selection', # Or 'Balance Group (Quantile Range)'
                        sort=sort_order, # Use the defined sort order
                        axis=alt.Axis(
                            labelAngle=-60,         # Steeper angle
                            labelOverlap='greedy',  # Strategy to avoid overlap
                            labelLimit=150          # Max label width in pixels (optional)
                        )
                    ),
                    # Y-axis: Use the positive magnitude
                    y=alt.Y('Avg Spending Magnitude', title='Average Amount Spent ($)', type='quantitative'),
                    # Color stacks by Category
                    color=alt.Color('Category', title='Expense Category', type='nominal', scale=alt.Scale(scheme='category10')),
                    # Order stacks (optional, default is alphabetical by color legend)
                    order=alt.Order('Category', sort='ascending'),
                    # Tooltip using magnitude
                    tooltip=[
                        alt.Tooltip(grouping_col, title='Balance Group', type='nominal'),
                        alt.Tooltip('Category', title='Expense Category', type='nominal'),
                        alt.Tooltip('Avg Spending Magnitude', format='$,.2f', title='Avg. Amount ($)', type='quantitative')
                    ]
                ).properties(
                    title=f"Average Expense Breakdown by Balance Group (n={actual_num_groups})" # Use actual groups count
                )
                st.altair_chart(chart_stacked_bar, use_container_width=True)
            else:
                st.info("No non-zero average expense data to display for the selected groups.")
        else:
            st.error(f"Grouping column '{grouping_col}' not found after creating groups.")

    except ValueError as ve:
        st.warning(f"Could not create {num_groups} distinct balance groups for the selected range. Try adjusting the balance filter range or reducing the number of groups. Error: {ve}")
        st.error(traceback.format_exc()) # Show traceback for ValueError during debugging
    except Exception as e:
         st.error(f"Error creating grouped stacked bar chart: {e}")
         st.error(traceback.format_exc())

elif not expense_amount_cols:
     st.warning("No detailed expense columns found in the data file to create breakdown.")
else: # num_filtered is 0
    st.info("No participants match the selected balance range.")


st.markdown("---")
st.caption("Dashboard using Streamlit sliders for filtering and grouping.")