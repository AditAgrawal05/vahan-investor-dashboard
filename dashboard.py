import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- Page Configuration ---
st.set_page_config(
    page_title="Vahan Vehicle Registration Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    /* Main title */
    .stApp h1 {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5; /* A nice blue */
    }
    /* Metric labels */
    .st-emotion-cache-1g6gooi p {
        font-size: 1.1rem;
        color: #424242;
    }
    /* Metric values */
    .st-emotion-cache-ocqkz7 {
        font-size: 2rem;
    }
    /* Sidebar styling */
    .st-emotion-cache-16txtl3 {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)


# --- Data Loading and Caching ---
@st.cache_data
def load_and_process_data():
    """
    Loads data from the new, cleaner CSVs, calculates YoY and QoQ metrics.
    """
    try:
        # Load the new, simplified yearly data by manufacturer
        yearly_df = pd.read_csv('vahan_manufacturer_data_clean.csv', header=0)
        monthly_df = pd.read_csv('vahan_monthly_data.csv', header=0)

        # --- Data Cleaning & Preparation for Yearly Data ---
        yearly_df['Date'] = pd.to_datetime(yearly_df['Date'])
        yearly_df['Year'] = yearly_df['Date'].dt.year
        yearly_df['Manufacturer'] = yearly_df['Manufacturer'].str.upper().str.strip()
        
        # --- Data Cleaning & Preparation for Monthly Data ---
        monthly_df.rename(columns={'Maker Maker': 'Manufacturer'}, inplace=True)
        monthly_df['Manufacturer'] = monthly_df['Manufacturer'].str.upper().str.strip()
        
        # Melt monthly data to long format
        id_vars = ['Manufacturer', 'Year']
        month_cols = ['Month Wise JAN', 'Month Wise FEB', 'Month Wise MAR', 'Month Wise APR', 
                      'Month Wise MAY', 'Month Wise JUN', 'Month Wise JUL', 'Month Wise AUG', 
                      'Month Wise SEP', 'Month Wise OCT', 'Month Wise NOV', 'Month Wise DEC']
        
        for col in month_cols:
            if col not in monthly_df.columns:
                monthly_df[col] = 0
        
        monthly_long_df = pd.melt(monthly_df, id_vars=id_vars, value_vars=month_cols,
                                  var_name='Month', value_name='Registrations')
        monthly_long_df['Month'] = monthly_long_df['Month'].str.replace('Month Wise ', '')

        # Map months to quarters
        month_to_quarter_map = {
            'JAN': 1, 'FEB': 1, 'MAR': 1, 'APR': 2, 'MAY': 2, 'JUN': 2,
            'JUL': 3, 'AUG': 3, 'SEP': 3, 'OCT': 4, 'NOV': 4, 'DEC': 4
        }
        monthly_long_df['Quarter'] = monthly_long_df['Month'].map(month_to_quarter_map)
        
        # --- Calculate QoQ Growth ---
        quarterly_totals = monthly_long_df.groupby(['Year', 'Quarter', 'Manufacturer'])['Registrations'].sum().reset_index()
        quarterly_totals.sort_values(['Manufacturer', 'Year', 'Quarter'], inplace=True)
        
        quarterly_totals['Prev_Q_Reg'] = quarterly_totals.groupby('Manufacturer')['Registrations'].shift(1)
        quarterly_totals['QoQ_Growth'] = ((quarterly_totals['Registrations'] - quarterly_totals['Prev_Q_Reg']) / quarterly_totals['Prev_Q_Reg'].replace(0, np.nan)) * 100
        quarterly_totals['QoQ_Growth'] = quarterly_totals['QoQ_Growth'].fillna(0).round(2)

        # --- Calculate YoY Growth ---
        # Pivot the yearly data to have years as columns for easy YoY calculation
        yearly_pivot = yearly_df.pivot_table(index=['Manufacturer', 'Category'], columns='Year', values='Registrations', aggfunc='sum').reset_index()
        yearly_pivot.columns.name = None
        
        # FIX: Filter columns to only sort integers (years) to prevent TypeError
        year_columns = sorted([col for col in yearly_pivot.columns if isinstance(col, int)])
        
        # Calculate YoY for all available year pairs
        for year in year_columns:
            if year - 1 in yearly_pivot.columns:
                prev_year = year - 1
                
                # Set a threshold to avoid misleading percentages from a low base
                MIN_BASE_UNITS = 100 
                
                # Calculate growth only for manufacturers who meet the threshold
                growth_values = ((yearly_pivot[year] - yearly_pivot[prev_year]) / yearly_pivot[prev_year].replace(0, np.nan)) * 100
                
                # Set growth to 0 for any manufacturer below the minimum base
                yearly_pivot[f'YoY_Growth_{year}'] = np.where(yearly_pivot[prev_year] < MIN_BASE_UNITS, 0, growth_values)
                
                yearly_pivot[f'YoY_Growth_{year}'] = yearly_pivot[f'YoY_Growth_{year}'].fillna(0).round(2)

        return yearly_pivot, quarterly_totals

    except FileNotFoundError:
        st.error("Error: Make sure `vahan_manufacturer_data_clean.csv` and `vahan_monthly_data.csv` are in the same directory.")
        return None, None
    except Exception as e:
        import traceback
        st.error(f"An error occurred during data processing: {e}")
        st.text(traceback.format_exc())
        return None, None

# --- Load Data ---
yearly_data, quarterly_data = load_and_process_data()

# --- Main Application ---
if yearly_data is not None and quarterly_data is not None:
    
    st.title("Vehicle Registration Insights for Investors")
    st.markdown("An interactive dashboard to analyze Year-over-Year (YoY) and Quarter-over-Quarter (QoQ) growth trends in the Indian auto market.")

    # --- Sidebar Filters ---
    st.sidebar.header("Dashboard Filters")
    
    yearly_years = [col for col in yearly_data.columns if isinstance(col, int)]
    quarterly_years = quarterly_data['Year'].unique()
    all_years = sorted(list(set(yearly_years) | set(quarterly_years)), reverse=True)

    selected_year = st.sidebar.selectbox("Select Year", options=all_years)
    
    available_quarters = sorted(quarterly_data[quarterly_data['Year'] == selected_year]['Quarter'].unique())
    if not available_quarters:
        st.sidebar.warning("No quarterly data available for the selected year.")
        selected_quarter = None
    else:
        selected_quarter = st.sidebar.selectbox("Select Quarter", options=available_quarters, index=len(available_quarters)-1)

    categories = sorted(yearly_data['Category'].unique())
    selected_category = st.sidebar.selectbox("Select Vehicle Category", options=categories)
    
    # --- Filter Data based on selections ---
    filtered_yearly_data = yearly_data[yearly_data['Category'] == selected_category].copy()
    
    if selected_quarter:
        filtered_quarterly_data = quarterly_data[
            (quarterly_data['Year'] == selected_year) & 
            (quarterly_data['Quarter'] == selected_quarter)
        ].copy()
    else:
        filtered_quarterly_data = pd.DataFrame()

    # --- Key Metrics Display ---
    st.header(f"📈 Performance Snapshot: {selected_category} - Q{selected_quarter if selected_quarter else 'N/A'} {selected_year}")
    
    total_regs_yoy_current = filtered_yearly_data[selected_year].sum() if selected_year in filtered_yearly_data else 0
    prev_year = selected_year - 1
    total_regs_yoy_prev = filtered_yearly_data[prev_year].sum() if prev_year in filtered_yearly_data else 0

    total_regs_qoq_current = filtered_quarterly_data['Registrations'].sum() if not filtered_quarterly_data.empty else 0
    total_regs_qoq_prev = filtered_quarterly_data['Prev_Q_Reg'].sum() if not filtered_quarterly_data.empty else 0
    
    overall_yoy = ((total_regs_yoy_current - total_regs_yoy_prev) / total_regs_yoy_prev) * 100 if total_regs_yoy_prev > 0 else 0
    overall_qoq = ((total_regs_qoq_current - total_regs_qoq_prev) / total_regs_qoq_prev) * 100 if total_regs_qoq_prev > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label=f"Total Registrations ({selected_year})", value=f"{int(total_regs_yoy_current):,}")
    col2.metric(label=f"Overall YoY Growth (vs {prev_year})", value=f"{overall_yoy:.2f}%")
    col3.metric(label=f"Overall Q{selected_quarter} QoQ Growth", value=f"{overall_qoq:.2f}%")

    st.markdown("---")

    # --- Visualizations ---
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader(f"YoY Growth by Manufacturer ({selected_category})")
        yoy_col_name = f'YoY_Growth_{selected_year}'
        if yoy_col_name in filtered_yearly_data.columns:
            # Filter out the 0-growth entries for a cleaner chart
            chart_data = filtered_yearly_data[filtered_yearly_data[yoy_col_name] != 0]
            fig_yoy = px.bar(
                chart_data.sort_values(yoy_col_name, ascending=False).head(15),
                x='Manufacturer', y=yoy_col_name,
                title=f'Top 15 Manufacturers by YoY Growth ({selected_year} vs {prev_year})',
                labels={yoy_col_name: 'YoY Growth (%)', 'Manufacturer': 'Manufacturer'},
                color=yoy_col_name, color_continuous_scale=px.colors.diverging.RdYlGn,
                color_continuous_midpoint=0
            )
            st.plotly_chart(fig_yoy, use_container_width=True)
        else:
            st.info(f"Year-over-Year growth data is not available for {selected_year}.")

    with col_b:
        st.subheader(f"QoQ Growth by Manufacturer (All Categories)")
        if not filtered_quarterly_data.empty:
            fig_qoq = px.bar(
                filtered_quarterly_data.sort_values('QoQ_Growth', ascending=False).head(15),
                x='Manufacturer', y='QoQ_Growth',
                title=f'Top 15 Manufacturers by QoQ Growth (Q{selected_quarter} {selected_year})',
                labels={'QoQ_Growth': 'QoQ Growth (%)', 'Manufacturer': 'Manufacturer'},
                color='QoQ_Growth', color_continuous_scale=px.colors.diverging.Tealrose,
                color_continuous_midpoint=0
            )
            st.plotly_chart(fig_qoq, use_container_width=True)
        else:
            st.info("No quarterly data to display for the selected period.")

    # --- Market Share Analysis ---
    if selected_year in filtered_yearly_data.columns:
        st.subheader(f"Market Share by Manufacturer ({selected_category} - {selected_year})")
        market_share_data = filtered_yearly_data[[selected_year, 'Manufacturer']].copy()
        market_share_data.rename(columns={selected_year: 'Registrations'}, inplace=True)
        
        fig_market_share = px.pie(
            market_share_data, names='Manufacturer', values='Registrations',
            title=f'Market Share by Manufacturer in {selected_year}', hole=0.4
        )
        fig_market_share.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_market_share, use_container_width=True)

    # --- Detailed Data View ---
    with st.expander("View Detailed Data Tables"):
        st.subheader("Yearly Data with YoY Growth (by Manufacturer)")
        st.dataframe(filtered_yearly_data)
        
        st.subheader("Quarterly Data with QoQ Growth (by Manufacturer)")
        st.dataframe(filtered_quarterly_data)

else:
    st.warning("Data could not be loaded. Please check the file paths and content.")