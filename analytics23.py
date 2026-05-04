import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

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
df.columns = df.columns.str.strip().str.replace(r'\s+', ' ', regex=True)

DAYS_COL = "Number of days pending from initial proposal"

date_cols = ['Work Received', 'Remarks Sent on', 'Compliance Rcvd']
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

if DAYS_COL in df.columns:
    df[DAYS_COL] = pd.to_numeric(df[DAYS_COL], errors='coerce')
else:
    st.error(f"Column '{DAYS_COL}' not found in the data!")
    st.stop()

# -------------------------------
# SIDEBAR FILTERS
# -------------------------------
st.sidebar.header("Filters")

dept_options = sorted(df['Department'].dropna().unique().tolist()) if 'Department' in df.columns else []
status_options = sorted(df['Current status'].dropna().unique().tolist()) if 'Current status' in df.columns else []

dept = st.sidebar.multiselect("Department", dept_options)
status = st.sidebar.multiselect("Status", status_options)
# -------------------------------
# THRESHOLD FILTER (NEW)
# -------------------------------
threshold = st.sidebar.selectbox(
    "Critical Days Threshold",
    options=[30, 45],
    index=1  # default = 45
)

# -------------------------------
# FILTERING
# -------------------------------
filtered_df = df.copy()
if dept and 'Department' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Department'].isin(dept)]
if status and 'Current status' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Current status'].isin(status)]

if filtered_df.empty:
    st.warning("No records match your filters. Showing all data.")
    filtered_df = df.copy()

# -------------------------------
# KPI METRICS
# -------------------------------
st.title("📊 Work Monitoring Dashboard")

col1, col2, col3, col4 = st.columns(4)

total = len(filtered_df)
pending_count = filtered_df['Current status'].str.contains('Pending', case=False, na=False).sum() if 'Current status' in filtered_df.columns else 0
returned_count = filtered_df['Current status'].str.contains('Returned', case=False, na=False).sum() if 'Current status' in filtered_df.columns else 0
avg_days = round(filtered_df[DAYS_COL].mean(), 2) if DAYS_COL in filtered_df.columns else 0

col1.metric("Total Work", total)
col2.metric("⏳ Pending Work", pending_count)
col3.metric("✅ Returned", returned_count)
col4.metric("Avg Days Pending", avg_days)

# -------------------------------
# FINANCE SSO ANALYSIS
# -------------------------------
st.subheader("💰 Finance SSO Analysis")
sso_col = "Finance SSO"
if sso_col in filtered_df.columns and not filtered_df[sso_col].dropna().empty:
    sso_count = filtered_df[sso_col].value_counts().reset_index()
    sso_count.columns = ['Finance SSO', 'Count']

    fig_bar = px.bar(sso_count, x='Finance SSO', y='Count', title="Count of Work Items by Finance SSO",
                     text='Count', color='Count', color_continuous_scale='Plasma')
    fig_bar.update_traces(textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

    fig_pie = px.pie(sso_count, names='Finance SSO', values='Count',
                     title="Percentage Distribution by Finance SSO", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.warning(f"Column '{sso_col}' not found or has no data.")

# -------------------------------
# OTHER CHARTS
# -------------------------------
st.subheader("📈 General Charts")

if 'Current status' in filtered_df.columns:
    fig_status = px.pie(filtered_df, names='Current status', title="Overall Status Distribution")
    st.plotly_chart(fig_status, use_container_width=True)

# -------------------------------
# CRITICAL CASES
# -------------------------------
st.subheader("⚠️ Critical Cases (Days > threshold or Returned more than twice)")

RETURNED_COL = 'file Returned more than twice'

days_mask = pd.to_numeric(filtered_df[DAYS_COL], errors='coerce').fillna(0) > threshold
returned_mask = filtered_df[RETURNED_COL].fillna('').str.strip().str.lower() == 'yes' if RETURNED_COL in filtered_df.columns else pd.Series(False, index=filtered_df.index)

critical_df = filtered_df[days_mask | returned_mask]

if not critical_df.empty:
    st.dataframe(critical_df, use_container_width=True)
else:
    st.success("✅ No critical cases found.")

# -------------------------------
# FULL DATA
# -------------------------------
st.subheader("📋 Full Data")
st.dataframe(filtered_df, use_container_width=True)


# ================================================================
# PDF GENERATION
# ================================================================

def df_to_html_table(data: pd.DataFrame) -> str:
    if data.empty:
        return "<p style='color:#888;font-style:italic;'>No records found.</p>"
    headers = "".join(f"<th>{col}</th>" for col in data.columns)
    rows = ""
    for i, (_, row) in enumerate(data.iterrows()):
        bg = "#f0f4ff" if i % 2 == 0 else "#ffffff"
        cells = "".join(
            f"<td style='background:{bg};'>{'' if pd.isna(v) else str(v)}</td>"
            for v in row
        )
        rows += f"<tr>{cells}</tr>"
    return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"


def build_html_report(filtered_df, total, pending_count, returned_count, avg_days,threshold):

    # ── Critical df (safe) ──
    d_mask = pd.to_numeric(filtered_df[DAYS_COL], errors='coerce').fillna(0) > threshold
    r_mask = (
        filtered_df[RETURNED_COL].fillna('').str.strip().str.lower() == 'yes'
        if RETURNED_COL in filtered_df.columns
        else pd.Series(False, index=filtered_df.index)
    )
    critical_df = filtered_df[d_mask | r_mask].copy()

    # ── KPI cards ──
    def kpi(label, value, bg, accent, text_color):
        return (
            f"<div class='kpi' style='background:{bg}; border-left:5px solid {accent};'>"
            f"<div class='kpi-value' style='color:{accent};'>{value}</div>"
            f"<div class='kpi-label' style='color:{text_color};'>{label}</div></div>"
        )

    kpi_row = (
        "<div class='kpi-row'>"
        + kpi("Total Work Items",  total,          "#EEF2FF", "#4F46E5", "#3730A3")
        + kpi("Pending",           pending_count,  "#FFF7ED", "#EA580C", "#9A3412")
        + kpi("Returned",          returned_count, "#F0FDF4", "#16A34A", "#166534")
        + kpi("Avg Days Pending",  avg_days,       "#FFF1F2", "#E11D48", "#9F1239")
        + "</div>"
    )

    # ── Tables ──
    if 'Current status' in filtered_df.columns:
        status_tbl = df_to_html_table(
            filtered_df['Current status'].value_counts()
            .rename_axis('Status').reset_index(name='Count')
        )
    else:
        status_tbl = "<p>No status data available.</p>"

    if 'Department' in filtered_df.columns and DAYS_COL in filtered_df.columns:
        dept_tbl = df_to_html_table(
            filtered_df.groupby('Department')[DAYS_COL]
            .agg(['mean', 'count']).round(2)
            .rename(columns={'mean': 'Avg Days Pending', 'count': 'Total Cases'})
            .sort_values('Avg Days Pending', ascending=False)
            .reset_index()
        )
    else:
        dept_tbl = "<p>No department data available.</p>"

    if 'Finance SSO' in filtered_df.columns:
        sso_tbl = df_to_html_table(
            filtered_df['Finance SSO'].value_counts()
            .rename_axis('Finance SSO').reset_index(name='Count')
        )
    else:
        sso_tbl = "<p>No Finance SSO data available.</p>"

    # ── Critical HTML ──
    if critical_df.empty:
        critical_html = "<p style='color:#16A34A; font-weight:bold;'>No critical cases found.</p>"
    else:
        critical_html = ""
        sso_list = (
            critical_df['Finance SSO'].dropna().unique().tolist()
            if 'Finance SSO' in critical_df.columns else [None]
        )
        for sso in sso_list:
            sso_data = (
                critical_df[critical_df['Finance SSO'] == sso]
                if sso is not None else critical_df
            )
            label = sso if sso else "Unknown SSO"
            critical_html += f"""
            <div class="sso-block">
              <h3 class="sso-title">Finance SSO: {label}
                <span class="sso-count">({len(sso_data)} case{'s' if len(sso_data) != 1 else ''})</span>
              </h3>
              {df_to_html_table(sso_data)}
            </div>"""

    html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    /* ── SCREEN styles (scrollable) ── */
    @media screen {{
        body {{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 10pt;
        color: #1e1e2e;
        background: #f8f9ff;
        padding: 20px;
        }}
        table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 9pt;
        table-layout: auto;        /* auto on screen = scrollable */
        }}
        .table-wrapper {{
        overflow-x: auto;          /* horizontal scroll on screen */
        width: 100%;
        }}
    }}

    /* ── PRINT styles ── */
    @media print {{
        @page {{
        size: A3 landscape;
        margin: 8mm 6mm;
        }}
        body {{
        font-size: 7.5pt;
        background: white;
        }}
        table {{
        table-layout: fixed;
        word-wrap: break-word;
        font-size: 7pt;
        }}
        .no-print {{ display: none; }}  /* hides print button when printing */
        .sso-block {{ page-break-inside: avoid; }}
        .section   {{ page-break-inside: avoid; }}
    }}

    /* ── Shared styles ── */
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    .print-btn {{
        position: fixed;
        top: 16px;
        right: 16px;
        background: #1e3a8a;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        cursor: pointer;
        z-index: 999;
    }}
    .print-btn:hover {{ background: #3b5bdb; }}

    .report-header {{
        background: #1e3a8a;
        color: white;
        padding: 18px 24px;
        border-radius: 10px;
        margin-bottom: 18px;
        text-align: center;
        border-bottom: 4px solid #f59e0b;
    }}
    .report-header h1 {{ font-size: 18pt; margin-bottom: 5px; }}
    .report-header p  {{ font-size: 9pt; opacity: 0.85; }}

    .kpi-row {{ display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }}
    .kpi {{
        flex: 1; min-width: 150px;
        border-radius: 8px; padding: 14px 16px;
        text-align: center; border: 1px solid #e2e8f0;
        border-left-width: 5px;
    }}
    .kpi-value {{ font-size: 20pt; font-weight: bold; }}
    .kpi-label {{ font-size: 8pt; margin-top: 4px; font-weight: 600; text-transform: uppercase; }}

    .section {{
        margin-top: 22px; background: white; border-radius: 8px;
        padding: 14px 16px; border: 1px solid #e2e8f0;
    }}
    .section h2 {{ font-size: 11pt; padding: 8px 14px; margin-bottom: 10px; border-radius: 6px; }}

    .section-status   h2 {{ background: #EEF2FF; color: #3730A3; border-left: 4px solid #4F46E5; }}
    .section-dept     h2 {{ background: #ECFDF5; color: #065F46; border-left: 4px solid #10B981; }}
    .section-sso      h2 {{ background: #FFF7ED; color: #9A3412; border-left: 4px solid #F97316; }}
    .section-critical h2 {{ background: #FFF1F2; color: #9F1239; border-left: 4px solid #F43F5E; }}

    thead tr th {{
        background: #1e3a8a; color: #ffffff;
        padding: 8px 10px; border: 1px solid #2d4fae;
        text-align: left; white-space: normal; font-size: 8.5pt;
    }}
    tbody tr:nth-child(odd)  td {{ background: #f0f4ff; }}
    tbody tr:nth-child(even) td {{ background: #ffffff; }}
    tbody tr td {{
        padding: 6px 10px; border: 1px solid #d0d7f0;
        vertical-align: top; word-break: break-word; color: #1e293b;
    }}
    tbody tr:hover td {{ background: #dbeafe; color: #1e3a8a; }}

    .sso-block {{
        margin-top: 16px; border: 1px solid #fecdd3;
        border-radius: 6px; padding: 10px 12px; background: #fff8f8;
    }}
    .sso-title {{ font-size: 10pt; color: #be123c; margin-bottom: 6px; }}
    .sso-count {{
        font-size: 8.5pt; color: #e11d48;
        background: #ffe4e6; padding: 2px 8px; border-radius: 20px;
    }}

    .section-critical thead tr th {{ background: #be123c; border-color: #9f1239; }}
    .section-critical tbody tr:nth-child(odd)  td {{ background: #fff1f2; }}
    .section-critical tbody tr:nth-child(even) td {{ background: #ffffff; }}

    .footer {{
        margin-top: 30px; text-align: center; font-size: 7.5pt;
        color: #94a3b8; border-top: 2px dashed #c7d2fe; padding-top: 8px;
    }}
    </style>
    </head>
    <body>

    <!-- Print button (hidden when printing) -->
    <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>

    <div class="report-header">
        <h1>Work Monitoring Dashboard - Report</h1>
        <p>Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}</p>
    </div>

    {kpi_row}

    <div class="section section-status">
        <h2>Status Breakdown</h2>
        {status_tbl}
    </div>

    <div class="section section-dept">
        <h2>Department Summary (Avg Days Pending)</h2>
        {dept_tbl}
    </div>

    <div class="section section-sso">
        <h2>Finance SSO Summary</h2>
        {sso_tbl}
    </div>

    <div class="section section-critical">
        <h2>Critical Cases (Days &gt; 45 or Returned Twice)</h2>
        {critical_html}
    </div>

    <div class="footer">Work Monitoring Dashboard - Auto-generated Report | Confidential</div>

    </body>
    </html>"""

    return html


# ── Download buttons ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📥 Download Report")

col_a, col_b = st.columns(2)

with col_a:
    if st.button("🌐 Generate Full Report HTML", use_container_width=True):
        html = build_html_report(filtered_df, total, pending_count, returned_count, avg_days,threshold)
        st.download_button(
            "⬇️ Download Full Report (HTML)",
            data=html,
            file_name=f"Work_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )
        st.success("✅ Open the file in browser → click Print button or Ctrl+P → Save as PDF")

with col_b:
    if st.button("🌐 Generate Critical Cases HTML", use_container_width=True):
        d_mask2 = pd.to_numeric(filtered_df[DAYS_COL], errors='coerce').fillna(0) > 45
        r_mask2 = (
            filtered_df[RETURNED_COL].fillna('').str.strip().str.lower() == 'yes'
            if RETURNED_COL in filtered_df.columns
            else pd.Series(False, index=filtered_df.index)
        )
        crit_only = filtered_df[d_mask2 | r_mask2].copy()
        total_c    = len(crit_only)
        pending_c  = crit_only['Current status'].str.contains('Pending', case=False, na=False).sum() if 'Current status' in crit_only.columns else 0
        returned_c = crit_only['Current status'].str.contains('Returned', case=False, na=False).sum() if 'Current status' in crit_only.columns else 0
        avg_c      = round(crit_only[DAYS_COL].mean(), 2) if not crit_only.empty else 0

        html = build_html_report(crit_only, total_c, pending_c, returned_c, avg_c)
        st.download_button(
            "⬇️ Download Critical Cases (HTML)",
            data=html,
            file_name=f"Critical_Cases_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )
        st.success("✅ Open the file in browser → click Print button or Ctrl+P → Save as PDF")
