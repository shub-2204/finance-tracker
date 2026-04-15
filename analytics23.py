import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Work Monitoring Dashboard", layout="wide")

# -------------------------------
# LOAD DATA
# -------------------------------
@st.cache_data(show_spinner="Loading data from Google Sheet...")
def load_data():
    try:
        url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT8zjCkBHSlsiJrM2x_vqCzrozsddCahhmaoHtkLfGmDOXSL5mdaj5GsEMQcD05fG9PBpQVHWg01Tr4/pub?gid=794036391&single=true&output=csv"
        df = pd.read_csv(url)
        st.success(f"✅ Data loaded successfully! Total rows: {len(df)}")
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data: {str(e)}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# -------------------------------
# DATA CLEANING
# -------------------------------
df.columns = df.columns.str.strip()   # Remove any extra spaces in column names

date_cols = ['Work Received', 'Remarks Sent on', 'Compliance Rcvd']
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

if 'Days Pending' in df.columns:
    df['Days Pending'] = pd.to_numeric(df['Days Pending'], errors='coerce')

# -------------------------------
# SIDEBAR FILTERS
# -------------------------------
st.sidebar.header("Filters")

dept_options = sorted(df['Department'].dropna().unique().tolist())
status_options = sorted(df['Current Status'].dropna().unique().tolist())

dept = st.sidebar.multiselect("Department", dept_options)
status = st.sidebar.multiselect("Status", status_options)

# -------------------------------
# FILTERING
# -------------------------------
filtered_df = df.copy()

if dept:
    filtered_df = filtered_df[filtered_df['Department'].isin(dept)]
if status:
    filtered_df = filtered_df[filtered_df['Current Status'].isin(status)]

if filtered_df.empty:
    st.warning("No records match your filters. Showing all data.")
    filtered_df = df.copy()

# -------------------------------
# KPI METRICS
# -------------------------------
st.title("📊 Work Monitoring Dashboard")

col1, col2, col3, col4 = st.columns(4)

total = len(filtered_df)

# Count properly based on your actual data
pending_count = filtered_df['Current Status'].str.contains('Pending', case=False, na=False).sum()
returned_count = filtered_df['Current Status'].str.contains('Returned', case=False, na=False).sum()

avg_days = round(filtered_df['Days Pending'].mean(), 2) if 'Days Pending' in filtered_df.columns else 0

col1.metric("Total Work", total)
col2.metric("⏳ Pending Work", pending_count)
col3.metric("✅ Returned", returned_count)
col4.metric("Avg Days Pending", avg_days)

# -------------------------------
# FINANCE SSO ANALYSIS (Updated with correct column name)
# -------------------------------


# -------------------------------
# FINANCE SSO ANALYSIS - Improved & Colorful
# -------------------------------
st.subheader("💰 Finance SSO Analysis")

ssO_col = "Finance SSO"

if ssO_col in filtered_df.columns and not filtered_df[ssO_col].dropna().empty:
    
    # Count by Finance SSO
    sso_count = filtered_df[ssO_col].value_counts().reset_index()
    sso_count.columns = ['Finance SSO', 'Count']
    
    # === Colorful Bar Chart ===
    fig_bar = px.bar(
        sso_count, 
        x='Finance SSO', 
        y='Count',
        title="📊 Count of Work Items by Finance SSO",
        color='Count',
        color_continuous_scale='Plasma',     # Beautiful colorful gradient
        text='Count',
        height=520
    )
    
    fig_bar.update_traces(
        textposition='outside',
        textfont_size=14,
        marker_line_color='white',
        marker_line_width=2
    )
    
    fig_bar.update_layout(
        xaxis_title="Finance SSO",
        yaxis_title="Number of Work Items",
        xaxis_tickangle=-45,                    # Rotate long names
        margin=dict(t=80, b=140, l=60, r=40),   # Extra bottom margin to fix number cutting
        font=dict(size=13),
        plot_bgcolor='rgba(240,240,240,0.5)'
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)

    # === Donut Pie Chart ===
    fig_pie = px.pie(
        sso_count, 
        names='Finance SSO', 
        values='Count',
        title="🥧 Percentage Distribution by Finance SSO",
        hole=0.4,                               # Modern donut style
        color_discrete_sequence=px.colors.qualitative.Bold  # Vibrant colors for pie
    )
    st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.warning(f"⚠️ Column **'{ssO_col}'** not found or contains no data. Please check your Google Sheet.")
# -------------------------------
# DAYS PENDING BY DEPARTMENT - SIDE BY SIDE
# -------------------------------
st.subheader("📊 Days Pending by Department")

fig_dept = px.bar(
    filtered_df, 
    x='Department', 
    y='Days Pending',
    color='Current Status',
    barmode='group',          # ← Side by side instead of stacked
    title="Days Pending by Department (Side by Side View)",
    text_auto=True
)

st.plotly_chart(fig_dept, use_container_width=True)
# -------------------------------
# OTHER CHARTS
# -------------------------------
st.subheader("📈 General Charts")

if 'Department' in filtered_df.columns:
    fig_dept = px.bar(filtered_df, x='Department', y='Days Pending', 
                      color='Current Status', title="Days Pending by Department")
    st.plotly_chart(fig_dept, use_container_width=True)

fig_status = px.pie(filtered_df, names='Current Status', title="Overall Status Distribution")
st.plotly_chart(fig_status, use_container_width=True)

# Critical Cases
st.subheader("⚠️ Critical Cases Days exceeding 7")
critical_df = filtered_df[
    (filtered_df.get('Days Pending', 0) > 7) |
    (filtered_df.get('file Returned more than twice', pd.Series(dtype=str)) == 'Yes')
]

if not critical_df.empty:
    st.dataframe(critical_df, use_container_width=True)
else:
    st.success("✅ No critical cases found.")

# Full Data
st.subheader("📋 Full Data")
st.dataframe(filtered_df, use_container_width=True)