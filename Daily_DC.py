import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

# --- 1. Page Configuration & Custom CSS ---
st.set_page_config(page_title="DC Daily Production Dashboard", layout="wide")

style_css = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {display: none !important;}
    .main .block-container {padding-top: 1.5rem;}
    
    .latest-date-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 20px;
    }
    .latest-date-text {
        font-size: 14px;
        color: #555;
        margin-bottom: 0px;
        font-weight: bold;
    }
    .latest-date-value {
        font-size: 32px;
        font-weight: 800;
        color: #1f77b4;
        font-family: 'Arial Black', sans-serif;
    }
    </style>
    """
st.markdown(style_css, unsafe_allow_html=True)

# --- 2. Helper Functions ---
def render_legend(items):
    item_template = ""
    for label, color in items:
        item_template += f"""
        <div style="display: inline-flex; align-items: center; margin: 0 12px;">
            <div style="width: 12px; height: 12px; background-color: {color}; border-radius: 2px; margin-right: 6px;"></div>
            <span style="font-size: 13px; font-weight: bold; color: #444;">{label}</span>
        </div>"""
    full_html = f"""<div style="text-align: center; width: 100%; margin-top: -10px; margin-bottom: 20px;">{item_template}</div>"""
    st.markdown(full_html, unsafe_allow_html=True)

def get_custom_labels(df, column_name, label_type="actual", prefix_col=None, precision=2, is_integer=False):
    labels = [""] * len(df)
    if df.empty: return labels
    def fmt(idx):
        v = df[column_name].iloc[idx]
        if pd.isnull(v): return ""
        num_str = f"{int(round(float(v))):,}" if is_integer else f"{float(v):.{precision}f}"
        if prefix_col and prefix_col in df.columns:
            p = str(df[prefix_col].iloc[idx]) if pd.notnull(df[prefix_col].iloc[idx]) else ""
            return f"{p} {num_str}" if p else num_str 
        return num_str
    
    if label_type == "actual":
        labels[0] = fmt(0)
        labels[-1] = fmt(len(df)-1)
    elif label_type == "plan":
        labels[-1] = fmt(len(df)-1)
    return labels

def get_y_range(df, columns, padding_top=0.6, padding_bottom=0.2):
    all_values = pd.concat([df[col] for col in columns if col in df.columns]).dropna()
    if all_values.empty: return [0, 100]
    v_min, v_max = all_values.min(), all_values.max()
    spread = v_max - v_min
    if spread == 0: return [v_min * 0.7, v_max * 1.5]
    return [v_min - (spread * padding_bottom), v_max + (spread * padding_top)]

# แก้ไขฟังก์ชันสไตล์เพื่อเพิ่มพื้นหลังให้ Label
def get_label_settings(color, size=11):
    return dict(
        font=dict(color=color, family="Arial Black", size=size),
        bgcolor="rgba(255, 255, 255, 0.8)", # พื้นหลังสีขาวโปร่งแสง
        bordercolor=color,                   # ขอบสีตามเส้นกราฟ
        borderwidth=1
    )

COLORS = {
    'CF_ACT': '#1f77b4', 'CF_FILL': 'rgba(31, 119, 180, 0.15)',
    'Y_C_ACT': '#2ca02c', 'Y_C_FILL': 'rgba(44, 160, 44, 0.15)',
    'Y_B_ACT': '#9467bd', 'Y_B_FILL': 'rgba(148, 103, 189, 0.15)',
    'FS_C_ACT': '#00ced1', 'FS_C_FILL': 'rgba(0, 206, 209, 0.15)',
    'FS_B_ACT': '#ff8c00', 'FS_B_FILL': 'rgba(255, 140, 0, 0.15)',
    'VIN_ACT': '#e377c2', 'VIN_FILL': 'rgba(227, 119, 194, 0.15)',
    'SALE_ACT': '#edc948', 'SALE_FILL': 'rgba(237, 201, 72, 0.15)',
    'ETH_ACT': '#17becf', 'ETH_FILL': 'rgba(23, 190, 207, 0.15)',
    'RED_PLAN': '#d62728' 
}
CHART_CONFIG = {'displayModeBar': False}

# --- 3. Data Loading ---
try:
    df_raw = pd.read_excel("Actual vs Plan.xlsx", engine="openpyxl")
    cols = [1, 15, 16, 17, 26, 27, 28, 7, 8, 29, 30, 11, 31, 12, 32, 22, 23, 36]
    chart_data = df_raw.iloc[:, cols].copy()
    chart_data.columns = [
        'Date', 'CF_Actual', 'Yield_C_Act', 'Yield_B_Act', 'CF_Target', 'Yield_C_Plan', 'Yield_B_Plan',
        'FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan', 'Vin_Act', 'Vin_Plan', 'Sale_Act', 'Sale_Plan',
        'Eth_Name', 'Eth_Act', 'Eth_Plan'
    ]
    chart_data['Date'] = pd.to_datetime(chart_data['Date'], errors='coerce')
    chart_data = chart_data.dropna(subset=['Date']).sort_values('Date')

    head_col, set_col = st.columns([2, 1])
    with set_col:
        st.write("##") 
        with st.expander("⚙️ REPORT SETTINGS", expanded=True):
            date_range = st.date_input("Select Date Range", value=(date(2026, 1, 1), date(2026, 1, 31)))

    if isinstance(date_range, tuple) and len(date_range) == 2:
        data = chart_data[(chart_data['Date'].dt.date >= date_range[0]) & 
                          (chart_data['Date'].dt.date <= date_range[1])]
        
        with head_col:
            st.title("🚀 DC Daily Production Dashboard")
            latest_date = data['Date'].max() if not data.empty else None
            date_str = latest_date.strftime('%d %B %Y').upper() if pd.notnull(latest_date) else 'N/A'
            st.markdown(f'<div class="latest-date-box"><p class="latest-date-text">LATEST DATA UPDATE AS OF</p><p class="latest-date-value">{date_str}</p></div>', unsafe_allow_html=True)

        if not data.empty:
            COMMON_LAYOUT = dict(template="plotly_white", height=350, margin=dict(t=50, b=10, l=50, r=220), xaxis=dict(automargin=True), showlegend=False)

            # --- Row 1 ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("1. CF Performance")
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=data['Date'], y=data['CF_Actual'], mode='lines+markers+text', text=get_custom_labels(data, 'CF_Actual', precision=3), textposition="top center", textfont=get_label_settings(COLORS['CF_ACT'])['font'], line=dict(color=COLORS['CF_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['CF_FILL'], cliponaxis=False))
                fig1.add_trace(go.Scatter(x=data['Date'], y=data['CF_Target'], mode='lines+text', text=get_custom_labels(data, 'CF_Target', "plan", precision=3), textposition="bottom right", textfont=get_label_settings(COLORS['RED_PLAN'])['font'], line=dict(color=COLORS['RED_PLAN'], width=2, dash='dash'), cliponaxis=False))
                fig1.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['CF_Actual', 'CF_Target'])))
                st.plotly_chart(fig1, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['CF_ACT']), ("Target", COLORS['RED_PLAN'])])

            with c2:
                st.subheader("2. Yield Performance")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_C_Act'], mode='lines+markers+text', text=get_custom_labels(data, 'Yield_C_Act', is_integer=True), textposition="top center", textfont=get_label_settings(COLORS['Y_C_ACT'])['font'], line=dict(color=COLORS['Y_C_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['Y_C_FILL'], cliponaxis=False))
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_B_Act'], mode='lines+markers+text', text=get_custom_labels(data, 'Yield_B_Act', is_integer=True), textposition="top center", textfont=get_label_settings(COLORS['Y_B_ACT'])['font'], line=dict(color=COLORS['Y_B_ACT'], width=3), fill='tonexty', fillcolor=COLORS['Y_B_FILL'], cliponaxis=False))
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_C_Plan'], mode='lines+text', text=get_custom_labels(data, 'Yield_C_Plan', "plan", is_integer=True), textposition="middle right", textfont=get_label_settings(COLORS['RED_PLAN'])['font'], line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False))
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_B_Plan'], mode='lines+text', text=get_custom_labels(data, 'Yield_B_Plan', "plan", is_integer=True), textposition="bottom right", textfont=get_label_settings(COLORS['RED_PLAN'])['font'], line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False))
                fig2.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Yield_C_Act', 'Yield_B_Act', 'Yield_C_Plan', 'Yield_B_Plan'])))
                st.plotly_chart(fig2, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Yield C", COLORS['Y_C_ACT']), ("Yield B", COLORS['Y_B_ACT']), ("Plan", COLORS['RED_PLAN'])])

            st.write("---")
            # --- Row 2 ---
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("3. %FS Raw Material")
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_C_Act'], mode='lines+markers+text', text=get_custom_labels(data, 'FS_C_Act'), textposition="top center", textfont=get_label_settings(COLORS['FS_C_ACT'])['font'], line=dict(color=COLORS['FS_C_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['FS_C_FILL'], cliponaxis=False))
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_B_Act'], mode='lines+markers+text', text=get_custom_labels(data, 'FS_B_Act'), textposition="top center", textfont=get_label_settings(COLORS['FS_B_ACT'])['font'], line=dict(color=COLORS['FS_B_ACT'], width=3), fill='tonexty', fillcolor=COLORS['FS_B_FILL'], cliponaxis=False))
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_C_Plan'], mode='lines+text', text=get_custom_labels(data, 'FS_C_Plan', "plan"), textposition="middle right", textfont=get_label_settings(COLORS['RED_PLAN'])['font'], line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False))
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_B_Plan'], mode='lines+text', text=get_custom_labels(data, 'FS_B_Plan', "plan"), textposition="bottom right", textfont=get_label_settings(COLORS['RED_PLAN'])['font'], line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False))
                fig3.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan'])))
                st.plotly_chart(fig3, use_container_width=True, config=CHART_CONFIG)
                render_legend([("FS C", COLORS['FS_C_ACT']), ("FS B", COLORS['FS_B_ACT']), ("Plan", COLORS['RED_PLAN'])])

            with c4:
                # กราฟ 4 (Vinasses Production) เพิ่มสไตล์พื้นหลัง Data Label
                st.subheader("4. Vinasses Production")
                fig4 = go.Figure()
                # สำหรับ Actual
                label_act = get_label_settings(COLORS['VIN_ACT'])
                fig4.add_trace(go.Scatter(
                    x=data['Date'], y=data['Vin_Act'], mode='lines+markers+text', 
                    text=get_custom_labels(data, 'Vin_Act', is_integer=True), 
                    textposition="top center", 
                    textfont=label_act['font'],
                    # เพิ่มพื้นหลังตรงนี้
                    texttemplate="<b>%{text}</b>",
                    line=dict(color=COLORS['VIN_ACT'], width=3), 
                    fill='tozeroy', fillcolor=COLORS['VIN_FILL'], cliponaxis=False
                ))
                # สำหรับ Plan
                label_plan = get_label_settings(COLORS['RED_PLAN'])
                fig4.add_trace(go.Scatter(
                    x=data['Date'], y=data['Vin_Plan'], mode='lines+text', 
                    text=get_custom_labels(data, 'Vin_Plan', "plan", is_integer=True), 
                    textposition="bottom right", 
                    textfont=label_plan['font'],
                    texttemplate="<b>%{text}</b>",
                    line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False
                ))
                fig4.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Vin_Act', 'Vin_Plan'])))
                st.plotly_chart(fig4, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['VIN_ACT']), ("Plan", COLORS['RED_PLAN'])])

            st.write("---")
            # --- Row 3 ---
            c5, c6 = st.columns(2)
            with c5:
                st.subheader("5. Vinasses Sale")
                fig5 = go.Figure()
                fig5.add_trace(go.Scatter(x=data['Date'], y=data['Sale_Act'], mode='lines+markers+text', text=get_custom_labels(data, 'Sale_Act', is_integer=True), textposition="top center", textfont=get_label_settings(COLORS['SALE_ACT'])['font'], line=dict(color=COLORS['SALE_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['SALE_FILL'], cliponaxis=False))
                fig5.add_trace(go.Scatter(x=data['Date'], y=data['Sale_Plan'], mode='lines+text', text=get_custom_labels(data, 'Sale_Plan', "plan", is_integer=True), textposition="bottom right", textfont=get_label_settings(COLORS['RED_PLAN'])['font'], line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False))
                fig5.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Sale_Act', 'Sale_Plan'])))
                st.plotly_chart(fig5, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['SALE_ACT']), ("Plan", COLORS['RED_PLAN'])])

            with c6:
                st.subheader("6. Ethanol Production")
                fig6 = go.Figure()
                # Actual พร้อมพื้นหลัง
                eth_act_style = get_label_settings(COLORS['ETH_ACT'], size=10)
                fig6.add_trace(go.Scatter(
                    x=data['Date'], y=data['Eth_Act'], mode='lines+markers+text', 
                    text=get_custom_labels(data, 'Eth_Act', prefix_col='Eth_Name', is_integer=True), 
                    textposition="top center", 
                    textfont=eth_act_style['font'], 
                    texttemplate="<b>%{text}</b>",
                    line=dict(color=COLORS['ETH_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['ETH_FILL'], cliponaxis=False
                ))
                # Plan พร้อมพื้นหลัง
                eth_plan_style = get_label_settings(COLORS['RED_PLAN'], size=10)
                fig6.add_trace(go.Scatter(
                    x=data['Date'], y=data['Eth_Plan'], mode='lines+text', 
                    text=get_custom_labels(data, 'Eth_Plan', "plan", prefix_col='Eth_Name', is_integer=True), 
                    textposition="bottom right", 
                    textfont=eth_plan_style['font'],
                    texttemplate="<b>%{text}</b>",
                    line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'), cliponaxis=False
                ))
                fig6.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Eth_Act', 'Eth_Plan'])))
                # เพิ่มคำสั่งปรับปรุง Data Labels ทั่วทั้งกราฟ 6 ให้มีพื้นหลังขาว
                fig6.update_traces(textfont_size=11, selector=dict(type='scatter'))
                
                st.plotly_chart(fig6, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['ETH_ACT']), ("Plan", COLORS['RED_PLAN'])])
        else:
            st.warning("No data found for the selected date range.")
except Exception as e:
    st.error(f"System Error: {e}")