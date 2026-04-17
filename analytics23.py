import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import io
import tempfile
import os

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
df.columns = df.columns.str.strip()

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
pending_count = filtered_df['Current Status'].str.contains('Pending', case=False, na=False).sum()
returned_count = filtered_df['Current Status'].str.contains('Returned', case=False, na=False).sum()
avg_days = round(filtered_df['Days Pending'].mean(), 2) if 'Days Pending' in filtered_df.columns else 0

col1.metric("Total Work", total)
col2.metric("⏳ Pending Work", pending_count)
col3.metric("✅ Returned", returned_count)
col4.metric("Avg Days Pending", avg_days)

# -------------------------------
# FINANCE SSO ANALYSIS
# -------------------------------
st.subheader("💰 Finance SSO Analysis")

ssO_col = "Finance SSO"

if ssO_col in filtered_df.columns and not filtered_df[ssO_col].dropna().empty:
    sso_count = filtered_df[ssO_col].value_counts().reset_index()
    sso_count.columns = ['Finance SSO', 'Count']

    fig_bar = px.bar(
        sso_count,
        x='Finance SSO',
        y='Count',
        title="📊 Count of Work Items by Finance SSO",
        color='Count',
        color_continuous_scale='Plasma',
        text='Count',
        height=520
    )
    fig_bar.update_traces(textposition='outside', textfont_size=14,
                          marker_line_color='white', marker_line_width=2)
    fig_bar.update_layout(xaxis_title="Finance SSO", yaxis_title="Number of Work Items",
                          xaxis_tickangle=-45, margin=dict(t=80, b=140, l=60, r=40),
                          font=dict(size=13), plot_bgcolor='rgba(240,240,240,0.5)')
    st.plotly_chart(fig_bar, use_container_width=True)

    fig_pie = px.pie(sso_count, names='Finance SSO', values='Count',
                     title="🥧 Percentage Distribution by Finance SSO",
                     hole=0.4, color_discrete_sequence=px.colors.qualitative.Bold)
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.warning(f"⚠️ Column **'{ssO_col}'** not found or contains no data.")

# -------------------------------
# DAYS PENDING BY DEPARTMENT
# -------------------------------
st.subheader("📊 Days Pending by Department")

fig_dept = px.bar(filtered_df, x='Department', y='Days Pending',
                  color='Current Status', barmode='group',
                  title="Days Pending by Department (Side by Side View)", text_auto=True)
st.plotly_chart(fig_dept, use_container_width=True)

# -------------------------------
# OTHER CHARTS
# -------------------------------
st.subheader("📈 General Charts")

if 'Department' in filtered_df.columns:
    fig_dept2 = px.bar(filtered_df, x='Department', y='Days Pending',
                       color='Current Status', title="Days Pending by Department")
    st.plotly_chart(fig_dept2, use_container_width=True)

fig_status = px.pie(filtered_df, names='Current Status', title="Overall Status Distribution")
st.plotly_chart(fig_status, use_container_width=True)

# -------------------------------
# CRITICAL CASES
# -------------------------------
st.subheader("⚠️ Critical Cases Days exceeding 7")
critical_df = filtered_df[
    (filtered_df.get('Days Pending', 0) > 45) |
    (filtered_df.get('file Returned more than twice', pd.Series(dtype=str)) == 'Yes')
]

if not critical_df.empty:
    st.dataframe(critical_df, use_container_width=True)
else:
    st.success("✅ No critical cases found.")

# -------------------------------
# FULL DATA
# -------------------------------
st.subheader("📋 Full Data")
st.dataframe(filtered_df, use_container_width=True)


# ================================
# PDF DOWNLOAD SECTION
# ================================
st.markdown("---")
st.subheader("📥 Download Report as PDF")


def generate_pdf(filtered_df, total, pending_count, returned_count, avg_days):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ---- Title ----
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_fill_color(30, 30, 100)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "Work Monitoring Dashboard Report", ln=True, align="C", fill=True)
    pdf.ln(4)

    # ---- Date ----
    from datetime import datetime
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}", ln=True, align="R")
    pdf.ln(4)

    # ---- KPI Summary ----
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 100)
    pdf.cell(0, 10, "Summary Metrics", ln=True)
    pdf.set_draw_color(30, 30, 100)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    kpis = [
        ("Total Work Items", str(total)),
        ("Pending Work", str(pending_count)),
        ("Returned", str(returned_count)),
        ("Avg Days Pending", str(avg_days)),
    ]

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(0, 0, 0)
    for label, value in kpis:
        pdf.set_fill_color(240, 240, 255)
        pdf.cell(100, 9, f"  {label}", border=1, fill=True)
        pdf.set_fill_color(220, 235, 255)
        pdf.cell(90, 9, f"  {value}", border=1, ln=True, fill=True)
    pdf.ln(6)

    # ---- Status Breakdown ----
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 100)
    pdf.cell(0, 10, "Status Breakdown", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    status_counts = filtered_df['Current Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(30, 30, 100)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 9, "Status", border=1, fill=True)
    pdf.cell(60, 9, "Count", border=1, ln=True, fill=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    for i, row in status_counts.iterrows():
        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(130, 8, f"  {str(row['Status'])}", border=1, fill=True)
        pdf.cell(60, 8, f"  {str(row['Count'])}", border=1, ln=True, fill=True)
    pdf.ln(6)

    # ---- Department Summary ----
    if 'Department' in filtered_df.columns and 'Days Pending' in filtered_df.columns:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 30, 100)
        pdf.cell(0, 10, "Department Summary (Avg Days Pending)", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        dept_summary = (
            filtered_df.groupby('Department')['Days Pending']
            .mean().round(2).reset_index()
            .sort_values('Days Pending', ascending=False)
        )

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(30, 30, 100)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 9, "Department", border=1, fill=True)
        pdf.cell(60, 9, "Avg Days Pending", border=1, ln=True, fill=True)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        for i, row in dept_summary.iterrows():
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(130, 8, f"  {str(row['Department'])}", border=1, fill=True)
            pdf.cell(60, 8, f"  {str(row['Days Pending'])}", border=1, ln=True, fill=True)
        pdf.ln(6)

    # ---- Finance SSO Summary ----
    ssO_col = "Finance SSO"
    if ssO_col in filtered_df.columns and not filtered_df[ssO_col].dropna().empty:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 30, 100)
        pdf.cell(0, 10, "Finance SSO Summary", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        sso_count = filtered_df[ssO_col].value_counts().reset_index()
        sso_count.columns = ['Finance SSO', 'Count']

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(30, 30, 100)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 9, "Finance SSO", border=1, fill=True)
        pdf.cell(60, 9, "Count", border=1, ln=True, fill=True)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        for i, row in sso_count.iterrows():
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(130, 8, f"  {str(row['Finance SSO'])}", border=1, fill=True)
            pdf.cell(60, 8, f"  {str(row['Count'])}", border=1, ln=True, fill=True)
        pdf.ln(6)

    # ---- Critical Cases ----
    critical_df = filtered_df[filtered_df.get('Days Pending', pd.Series(dtype=float)) > 45]

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 10, f"Critical Cases (Days Pending > 45): {len(critical_df)}", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    if not critical_df.empty:
        cols_to_show = ['Department', 'Current Status', 'Days Pending', 'Finance SSO']
        cols_to_show = [c for c in cols_to_show if c in critical_df.columns]
        col_width = 190 // len(cols_to_show)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(180, 0, 0)
        pdf.set_text_color(255, 255, 255)
        for col in cols_to_show:
            pdf.cell(col_width, 9, col[:20], border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        for i, row in critical_df[cols_to_show].head(30).iterrows():
            fill = i % 2 == 0
            pdf.set_fill_color(255, 230, 230) if fill else pdf.set_fill_color(255, 255, 255)
            for col in cols_to_show:
                pdf.cell(col_width, 8, str(row[col])[:20], border=1, fill=True)
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 150, 0)
        pdf.cell(0, 9, "  No critical cases found.", ln=True)

    # ---- Footer ----
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Work Monitoring Dashboard — Auto-generated Report", align="C")

    return bytes(pdf.output())


if st.button("📄 Generate & Download PDF Report"):
    with st.spinner("Generating PDF..."):
        try:
            pdf_bytes = generate_pdf(filtered_df, total, pending_count, returned_count, avg_days)
            st.download_button(
                label="⬇️ Click here to Download PDF",
                data=pdf_bytes,
                file_name="work_monitoring_report.pdf",
                mime="application/pdf"
            )
            st.success("✅ PDF ready! Click the button above to download.")
        except Exception as e:
            st.error(f"❌ Failed to generate PDF: {str(e)}")
            st.info("Make sure fpdf2 is installed: pip install fpdf2")
