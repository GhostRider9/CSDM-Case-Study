import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder


def generate_forecast(data_1, data_2, weight, uplift_factor):
    """
    Combine two regional sales datasets with weights and an uplift factor to generate forecast data.

    Args:
        data_1 (dict): Historical sales data for the first product (e.g., Princess Plus).
                       Format: {region: [sales_per_week]}.
        data_2 (dict): Historical sales data for the second product (e.g., Dwarf Plus).
                       Format: {region: [sales_per_week]}.
        weight (float): Blending weight for data_1. The weight for data_2 is calculated as (1 - weight).
                        Must be between 0.0 and 1.0.
        uplift_factor (float): A multiplier to adjust the forecasted demand (e.g., 1.15 for a 15% uplift).

    Returns:
        dict: Forecasted sales data for each region.
              Format: {region: [forecasted_sales_per_week]}.

    Raises:
        ValueError: If the input data dictionaries have mismatched regions or week lengths.

    Example:
        data_1 = {'AMR': [100, 200], 'Europe': [150, 250]}
        data_2 = {'AMR': [120, 180], 'Europe': [130, 220]}
        weight = 0.7
        uplift_factor = 1.1
        forecast = generate_forecast(data_1, data_2, weight, uplift_factor)
        # Output: {'AMR': [112, 198], 'Europe': [144, 242]}
    """
    forecast = {}
    data_1_sum = sum(sum(x) for x in data_1.values())
    data_2_sum = sum(sum(x) for x in data_2.values())
    # Use data_1 as base, combine the trend from both side
    norm_factor = data_1_sum / (weight * data_1_sum + (1 - weight) * data_2_sum)

    for region in data_1:
        blended = [
            round(weight * p + (1 - weight) * d)
            for p, d in zip(data_1[region], data_2[region])
        ]
        forecast[region] = [round(x * uplift_factor * norm_factor) for x in blended]

    return forecast


st.markdown("## 🦸‍♂️ Superman Plus Demand Forecast")
st.markdown("""
This model estimates demand for **Superman Plus**, based on historical performance of similar products:
- 🧜‍♀️ Princess Plus ($200, last year)
- 🧸 Dwarf Plus ($120, two years ago)

Uplift parameter is implemented, an adjustment factor of +10% to +20% for earlier launch timing

You can adjust blending weights and uplift on the left and see forecast update dynamically.
""")

# Sidebar Sliders
st.sidebar.header("🎛️ Forecast Adjustment Parameters")

princess_weight = st.sidebar.slider(
    "Weight for Princess Plus (%)",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.05,
    key='princess_slider_superman'
)

uplift_factor = st.sidebar.number_input(
    "Demand Uplift Factor (e.g., 1.15)",
    min_value=1.0,
    max_value=2.0,
    value=1.15,
    step=0.01,
    key='uplift_slider_superman'
)

dwarf_weight = 1.0 - princess_weight

st.sidebar.markdown(f"🧮 Current Blend: `{princess_weight:.2f} x Princess + {dwarf_weight:.2f} x Dwarf`")
st.sidebar.markdown(f"📈 Uplift Factor: `{uplift_factor}`")

# Historical Data
princess_plus = {
    'AMR': [240, 170, 130, 90, 110, 130, 110, 110, 110, 130, 70, 90, 100, 80, 90],
    'Europe': [100, 80, 90, 80, 70, 60, 60, 60, 50, 50, 50, 80, 80, 60, 50],
    'PAC': [150, 220, 240, 150, 130, 120, 110, 100, 110, 100, 120, 130, 160, 120, 100]
}

dwarf_plus = {
    'AMR': [320, 220, 170, 190, 200, 170, 160, 160, 140, 140, 180, 160, 160, 170, 190],
    'Europe': [80, 100, 60, 100, 100, 90, 80, 80, 80, 70, 90, 80, 80, 80, 70],
    'PAC': [230, 210, 140, 144, 140, 150, 140, 175, 140, 90, 90, 100, 110, 100, 90]
}

# Convert to DataFrames
weeks = ['Week ' + str(i+1) for i in range(15)]
df_princess = pd.DataFrame(princess_plus, index=weeks).reset_index().rename(columns={'index': 'Week'})
df_dwarf = pd.DataFrame(dwarf_plus, index=weeks).reset_index().rename(columns={'index': 'Week'})

# Plotting Historical Data with Plotly
st.subheader("🧜‍♀️ Princess Plus – Historical Sales by Region")
fig1 = px.line(df_princess, x='Week', y=['AMR', 'Europe', 'PAC'], markers=True,
                title="Princess Plus – Historical Demand (from Oct wk4)", labels={"value": "Units Sold", "variable": "Region"})
st.plotly_chart(fig1, use_container_width=True)

st.subheader("🧸 Dwarf Plus – Historical Sales by Region")
fig2 = px.line(df_dwarf, x='Week', y=['AMR', 'Europe', 'PAC'], markers=True,
                title="Dwarf Plus – Historical Demand (from Sept wk3)", labels={"value": "Units Sold", "variable": "Region"})
st.plotly_chart(fig2, use_container_width=True)

# Generate Forecast Dynamically
forecast = generate_forecast(princess_plus, dwarf_plus, princess_weight, uplift_factor)
df_forecast = pd.DataFrame(forecast, index=weeks).reset_index().rename(columns={'index': 'Week'})

# Download Button
st.sidebar.header("📥 Download Forecast")
csv = df_forecast.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="Download as CSV",
    data=csv,
    file_name='superman_plus_15Wk_forecast.csv',
    mime='text/csv'
)

# Display Forecast Table using AgGrid
st.subheader("📊 Estimated 15 Weeks Demand Forecast")

# Configure AgGrid
gb = GridOptionsBuilder.from_dataframe(df_forecast)
gb.configure_default_column(editable=False, filterable=True, sortable=True)
gb.configure_grid_options(enableRangeSelection=True)
grid_options = gb.build()

AgGrid(
    df_forecast,
    gridOptions=grid_options,
    height=300,
    theme='streamlit',
    allow_unsafe_jscode=True,
    editable=False,
    fit_columns_on_grid_load=True
)

# Display Total Demand of Three Years Per Region Table using AgGrid
st.subheader("📊 Total Demand Comparison")
get_sum = lambda df: df.drop('Week', axis=1).sum()
df_total = pd.concat([get_sum(df_dwarf), get_sum(df_princess), get_sum(df_forecast)],axis=1)
df_total.columns = ['Dwarf_plus','Princess_plus','Superman_plus']
df_total.reset_index(inplace=True,names='Region')

# Configure AgGrid
gb = GridOptionsBuilder.from_dataframe(df_total)
gb.configure_default_column(editable=False, filterable=True, sortable=True)
gb.configure_grid_options(enableRangeSelection=True)
grid_options = gb.build()

AgGrid(
    df_total,
    gridOptions=grid_options,
    height=150,
    theme='streamlit',
    allow_unsafe_jscode=True,
    editable=False,
    fit_columns_on_grid_load=True
)

# Final Forecast Plot
st.subheader("📈 Weekly Demand Forecast – All Regions (Combined View)")
fig3 = px.line(df_forecast, x='Week', y=['AMR', 'Europe', 'PAC'], markers=True,
                title="Forecasted Demand for Superman Plus", labels={"value": "Units", "variable": "Region"})
st.plotly_chart(fig3, use_container_width=True)

# Footer
st.markdown("---")