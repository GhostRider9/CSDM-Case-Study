import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


st.markdown("## Allocate Remaining Supply for Superman Plus in Wk4 ")

# Sample Data
@st.cache_data
def load_data():
    # Table 1: Total Cumulative Supply
    df_supply = pd.DataFrame({
        "Week": ["Jan Wk2", "Jan Wk3", "Jan Wk4", "Jan Wk5"],
        "Total_Cum_Supply": [230, 270, 320, 380]
    })

    # Table 2: Jan Wk1 Build
    actual_build = {
        "Program": ["Superman", "Superman_Plus", "Superman_Mini"],
        "Jan_Wk1_Build": [70, 70, 60]
    }

    # Table 3: Demand Forecast
    df_demand = pd.DataFrame({
        "Week": ["Jan Wk2", "Jan Wk3", "Jan Wk4", "Jan Wk5"],
        "Superman": [85, 100, 110, 120],
        "Superman_Plus": [85, 120, 150, 175],
        "Superman_Mini": [40, 60, 70, 75]
    })

    # Table 4: Channel Demand Ask
    df_channels = pd.DataFrame({
        "Channel": ["Online Store", "Retail Store", "Parter-AMR", "Parter-Europe", "Parter-PAC"],
        "Jan Wk2": [20, 15, 20, 5, 25],
        "Jan Wk3": [30, 25, 25, 10, 30],
        "Jan Wk4": [40, 30, 30, 15, 35],
        "Jan Wk5": [50, 35, 35, 15, 40]
    }).set_index("Channel")

    return df_supply, actual_build, df_demand, df_channels

df_supply, actual_build, df_demand, df_channels = load_data()

# Sidebar: Protect PAC in Jan Wk4?
protect_pac = st.sidebar.checkbox("Protect PAC Reseller Partner in Jan Wk4", value=True)

# Compute remaining supply after prioritizing Superman/Superman Mini
df_allocation = pd.merge(df_supply, df_demand[['Week', 'Superman', 'Superman_Mini']], on='Week')
df_allocation['Prioritized_Demand'] = df_allocation['Superman'] + df_allocation['Superman_Mini']
df_allocation['Remaining_For_SupermanPlus'] = df_allocation['Total_Cum_Supply'] - df_allocation['Prioritized_Demand']
df_allocation['Gap'] = df_allocation['Remaining_For_SupermanPlus'] - df_demand['Superman_Plus']

# Display Remaining Supply
st.subheader("📦 Remaining Supply Available for Superman Plus")
st.markdown("""
Prioritized_Demand: Superman + Superman Mini Demand
GAP: Remaining_For_SupermanPlus - Superman_Plus demand""")
st.dataframe(df_allocation[['Week', 'Total_Cum_Supply', 'Prioritized_Demand', 'Remaining_For_SupermanPlus', 'Gap']])

# Visualization: Supply vs Demand
supply_vals = df_allocation['Remaining_For_SupermanPlus'].tolist()
weeks = df_allocation['Week'].tolist()
demand_vals = [df_channels[wk].sum() for wk in weeks]

viz_data = pd.DataFrame({
    "Week": weeks * 2,
    "Value": supply_vals + demand_vals,
    "Type": ["Supply"] * len(supply_vals) + ["Demand"] * len(demand_vals)
})

fig = px.bar(viz_data, x="Week", y="Value", color="Type", barmode="group",
             title="📦 Supply vs Demand for Superman Plus by Week",
             labels={"Value": "Units", "Week": "Week"})
st.plotly_chart(fig)

# Weekly Allocation Logic
allocation_result = {}

for wk in weeks:
    supply_available = df_allocation[df_allocation['Week'] == wk]['Remaining_For_SupermanPlus'].values[0]
    total_demand = df_channels[wk].sum()
    channel_demands = df_channels[wk]

    if supply_available >= total_demand:
        alloc = channel_demands.to_dict()
    else:
        # Step 1: Raw proportional allocation with floor rounding
        raw_alloc = (channel_demands / total_demand) * supply_available
        floored_alloc = raw_alloc.apply(np.floor).astype(int)
        remainder = raw_alloc - floored_alloc

        # Step 2: Distribute the remaining units based on largest remainders
        remaining_units = int(supply_available - floored_alloc.sum())
        alloc = floored_alloc.to_dict()

        # Sort channels by descending remainder
        top_ups = remainder.sort_values(ascending=False).head(remaining_units).index
        for ch in top_ups:
            alloc[ch] += 1

        # Step 3: Protect Parter-PAC in Jan Wk4
        if protect_pac and wk == 'Jan Wk4':
            pac_ask = df_channels.loc['Parter-PAC', wk]
            if alloc['Parter-PAC'] < pac_ask:
                shortage = pac_ask - alloc['Parter-PAC']
                alloc['Parter-PAC'] = pac_ask

                # Reduce from others to keep total within supply
                others = [ch for ch in alloc if ch != 'Parter-PAC']
                others_sorted = sorted(others, key=lambda ch: alloc[ch], reverse=True)

                for ch in others_sorted:
                    reducible = min(alloc[ch], shortage)
                    alloc[ch] -= reducible
                    shortage -= reducible
                    if shortage <= 0:
                        break

    allocation_result[wk] = alloc


# Convert allocation result into DataFrame and calculate diff matrix
alloc_df = pd.DataFrame(allocation_result).T
alloc_df.index.name = "Channel"
diff_df = (alloc_df - df_channels.T).reset_index()

# Display Allocation Change using AgGrid
st.subheader("📊 Final Allocations Change to Channels (Editable)")
st.markdown("Reduce channel supply proportionally if there is a supply gap, except for protected channel.")
gb = GridOptionsBuilder.from_dataframe(diff_df)
gb.configure_grid_options(enableRangeSelection=True)
gb.configure_selection(selection_mode="single", use_checkbox=False)
gb.configure_column("Channel", pinned=True)
for col in alloc_df.columns:
    gb.configure_column(col, editable=True)
gb.configure_side_bar()
gb.configure_grid_options(domLayout='autoHeight')
grid_options = gb.build()

response = AgGrid(
    diff_df,
    gridOptions=grid_options,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=True,
    theme='alpine',
    update_mode=GridUpdateMode.MODEL_CHANGED,
    fit_columns_on_grid_load=True,
    height=300,
)

updated_diff_df = pd.DataFrame(response.data)
updated_alloc_df = df_channels.T + updated_diff_df.set_index('Channel')
# Show final allocation summary
if updated_diff_df is not None:
    st.subheader("✅ Updated Allocation Summary")
    st.dataframe(updated_alloc_df)

# Download button for allocation
@st.cache_data
def convert_df_to_csv(_df):
    return _df.to_csv(index=False).encode('utf-8')


st.download_button(
    label="📥 Download Allocation CSV",
    data = convert_df_to_csv(updated_alloc_df),
    file_name='superman_plus_allocation.csv',
    mime='text/csv'
)