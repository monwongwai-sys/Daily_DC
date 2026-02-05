import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(page_title="DC Daily Production Dashboard", layout="wide")

# --- ฟังก์ชันจัดการ Range ของแกน Y ---
def get_y_range(df, columns, padding_top=0.5, padding_bottom=0.15):
    all_values = pd.concat([df[col] for col in columns if col in df.columns]).dropna()
    if all_values.empty: return [0, 100]
    v_min, v_max = all_values.min(), all_values.max()
    spread = v_max - v_min
    if spread == 0: return [v_min * 0.7, v_max * 1.5]
    return [v_min - (spread * padding_bottom), v_max + (spread * padding_top)]

# --- ฟังก์ชันจัดการ Data Label ---
def get_smart_labels(df, column_name, prefix_col=None, precision=2, is_integer=False, show_last_only=False, first_last_only=False):
    labels = [""] * len(df)
    if df.empty: return labels
    def fmt(idx):
        v = df[column_name].iloc[idx]
        if pd.isnull(v): return ""
        num_str = f"{int(round(float(v))):,}" if is_integer else f"{float(v):.{precision}f}"
        if prefix_col and prefix_col in df.columns:
            p = str(df[prefix_col].iloc[idx]) if pd.notnull(df[prefix_col].iloc[idx]) else ""
            return f"{p}: {num_str}" if p else num_str
        return num_str
    if show_last_only: labels[-1] = fmt(len(df)-1)
    elif first_last_only:
        labels[0] = fmt(0); labels[-1] = fmt(len(df)-1)
    return labels

def label_style(color, size=11):
    return dict(color=color, family="Arial Black", size=size)

# --- สีมาตรฐาน ---
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

try:
    df = pd.read_excel("Actual vs Plan.xlsx", engine="openpyxl")
    cols = [1, 15, 16, 17, 26, 27, 28, 7, 8, 29, 30, 11, 31, 12, 32, 22, 23, 36]
    chart_data = df.iloc[:, cols].copy()
    chart_data.columns = [
        'Date', 'CF_Actual', 'Yield_C_Act', 'Yield_B_Act', 'CF_Target', 'Yield_C_Plan', 'Yield_B_Plan',
        'FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan', 'Vin_Act', 'Vin_Plan', 'Sale_Act', 'Sale_Plan',
        'Eth_Name', 'Eth_Act', 'Eth_Plan'
    ]
    chart_data['Date'] = pd.to_datetime(chart_data['Date'], errors='coerce')
    chart_data = chart_data.dropna(subset=['Date']).sort_values('Date')

    # Sidebar
    st.sidebar.header("⚙️ Settings")
    max_d = chart_data['Date'].max()
    date_range = st.sidebar.date_input("Date Range", value=(date(2026, 1, 1), max_d.date()))

    if isinstance(date_range, tuple) and len(date_range) == 2:
        data = chart_data[(chart_data['Date'].dt.date >= date_range[0]) & (chart_data['Date'].dt.date <= date_range[1])]
        
        st.title("🚀 DC Daily Production")
        latest_str = data['Date'].max().strftime('%d/%m/%Y') if not data.empty else "-"
        st.subheader(f"📅 ข้อมูลล่าสุด ณ วันที่: {latest_str}")
        

        if not data.empty:
            COMMON_LAYOUT = dict(
                template="plotly_white",
                height=400, # ปรับความสูงลงนิดหน่อยเพื่อเผื่อพื้นที่ตัวหนังสือด้านล่าง
                margin=dict(t=60, b=20, l=50, r=100),
                xaxis=dict(automargin=True),
                showlegend=False
            )

            c1, c2 = st.columns(2)
            
            # --- 1. CF ---
            with c1:
                st.subheader("1️⃣ CF Performance")
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=data['Date'], y=data['CF_Actual'], mode='lines+markers+text', text=get_smart_labels(data, 'CF_Actual', precision=3, first_last_only=True), textposition="top center", cliponaxis=False,textfont=label_style(COLORS['CF_ACT']), line=dict(color=COLORS['CF_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['CF_FILL']))
                fig1.add_trace(go.Scatter(x=data['Date'], y=data['CF_Target'], mode='lines+text', text=get_smart_labels(data, 'CF_Target', precision=3, show_last_only=True), textposition="bottom right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dash')))
                fig1.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['CF_Actual', 'CF_Target'])))
                st.plotly_chart(fig1, use_container_width=True, config=CHART_CONFIG)
                st.markdown(f'<p style="color:gray; font-size:13px; text-align:center;">🔵 <b>Actual:</b> CF Actual | 🔴 <b>Plan:</b> CF Target</p>', unsafe_allow_html=True)

            # --- 2. Yield ---
            with c2:
                st.subheader("2️⃣ Yield Performance")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_C_Act'], mode='lines+markers+text', text=get_smart_labels(data, 'Yield_C_Act', is_integer=True, first_last_only=True), textposition="top center", cliponaxis=False, textfont=label_style(COLORS['Y_C_ACT']), line=dict(color=COLORS['Y_C_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['Y_C_FILL']))
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_B_Act'], mode='lines+markers+text', text=get_smart_labels(data, 'Yield_B_Act', is_integer=True, first_last_only=True), textposition="bottom center", cliponaxis=False, textfont=label_style(COLORS['Y_B_ACT']), line=dict(color=COLORS['Y_B_ACT'], width=3), fill='tonexty', fillcolor=COLORS['Y_B_FILL']))
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_C_Plan'], mode='lines+text', text=get_smart_labels(data, 'Yield_C_Plan', is_integer=True, show_last_only=True), textposition="top right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig2.add_trace(go.Scatter(x=data['Date'], y=data['Yield_B_Plan'], mode='lines+text', text=get_smart_labels(data, 'Yield_B_Plan', is_integer=True, show_last_only=True), textposition="bottom right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig2.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Yield_C_Act', 'Yield_B_Act', 'Yield_C_Plan', 'Yield_B_Plan'])))
                st.plotly_chart(fig2, use_container_width=True, config=CHART_CONFIG)
                st.markdown(f'<p style="color:gray; font-size:13px; text-align:center;">🟢 <b>C-Act:</b> Yield C | 🟣 <b>B-Act:</b> Yield B | 🔴 <b>Plan:</b> Target Yield</p>', unsafe_allow_html=True)

            st.write("##")
            c3, c4 = st.columns(2)
            # --- 3. %FS ---
            with c3:
                st.subheader("3️⃣ %FS Raw Material")
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_C_Act'], mode='lines+markers+text', text=get_smart_labels(data, 'FS_C_Act', precision=2, first_last_only=True), textposition="top center", cliponaxis=False, textfont=label_style(COLORS['FS_C_ACT']), line=dict(color=COLORS['FS_C_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['FS_C_FILL']))
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_B_Act'], mode='lines+markers+text', text=get_smart_labels(data, 'FS_B_Act', precision=2, first_last_only=True), textposition="bottom center", cliponaxis=False, textfont=label_style(COLORS['FS_B_ACT']), line=dict(color=COLORS['FS_B_ACT'], width=3), fill='tonexty', fillcolor=COLORS['FS_B_FILL']))
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_C_Plan'], mode='lines+text', text=get_smart_labels(data, 'FS_C_Plan', precision=2, show_last_only=True), textposition="top right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig3.add_trace(go.Scatter(x=data['Date'], y=data['FS_B_Plan'], mode='lines+text', text=get_smart_labels(data, 'FS_B_Plan', precision=2, show_last_only=True), textposition="bottom right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig3.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan'])))
                st.plotly_chart(fig3, use_container_width=True, config=CHART_CONFIG)
                st.markdown(f'<p style="color:gray; font-size:13px; text-align:center;">🔵 <b>FS-C:</b> Act | 🟠 <b>FS-B:</b> Act | 🔴 <b>Plan:</b> Target %FS</p>', unsafe_allow_html=True)

            # --- 4. Vin Production ---
            with c4:
                st.subheader("4️⃣ Vinasses Production")
                fig4 = go.Figure()
                fig4.add_trace(go.Scatter(x=data['Date'], y=data['Vin_Act'], mode='lines+markers+text', text=get_smart_labels(data, 'Vin_Act', is_integer=True, first_last_only=True), textposition="top center", cliponaxis=False, textfont=label_style(COLORS['VIN_ACT']), line=dict(color=COLORS['VIN_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['VIN_FILL']))
                fig4.add_trace(go.Scatter(x=data['Date'], y=data['Vin_Plan'], mode='lines+text', text=get_smart_labels(data, 'Vin_Plan', is_integer=True, show_last_only=True), textposition="bottom right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig4.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Vin_Act', 'Vin_Plan'])))
                st.plotly_chart(fig4, use_container_width=True, config=CHART_CONFIG)
                st.markdown(f'<p style="color:gray; font-size:13px; text-align:center;">🌸 <b>Actual:</b> Vin Production | 🔴 <b>Plan:</b> Vin Target</p>', unsafe_allow_html=True)

            st.write("##")
            c5, c6 = st.columns(2)
            # --- 5. Vin Sale ---
            with c5:
                st.subheader("5️⃣ Vinasses Sale")
                fig5 = go.Figure()
                fig5.add_trace(go.Scatter(x=data['Date'], y=data['Sale_Act'], mode='lines+markers+text', text=get_smart_labels(data, 'Sale_Act', is_integer=True, first_last_only=True), textposition="top center", cliponaxis=False, textfont=label_style(COLORS['SALE_ACT']), line=dict(color=COLORS['SALE_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['SALE_FILL']))
                fig5.add_trace(go.Scatter(x=data['Date'], y=data['Sale_Plan'], mode='lines+text', text=get_smart_labels(data, 'Sale_Plan', is_integer=True, show_last_only=True), textposition="bottom right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig5.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Sale_Act', 'Sale_Plan'])))
                st.plotly_chart(fig5, use_container_width=True, config=CHART_CONFIG)
                st.markdown(f'<p style="color:gray; font-size:13px; text-align:center;">🟡 <b>Actual:</b> Vin Sale | 🔴 <b>Plan:</b> Sale Target</p>', unsafe_allow_html=True)

            # --- 6. Ethanol ---
            with c6:
                st.subheader("6️⃣ Ethanol Production")
                fig6 = go.Figure()
                act_labels = get_smart_labels(data, 'Eth_Act', prefix_col='Eth_Name', is_integer=True, first_last_only=True)
                fig6.add_trace(go.Scatter(x=data['Date'], y=data['Eth_Act'], mode='lines+markers+text', text=act_labels, textposition="top center", cliponaxis=False, textfont=label_style(COLORS['ETH_ACT']), line=dict(color=COLORS['ETH_ACT'], width=3), fill='tozeroy', fillcolor=COLORS['ETH_FILL']))
                plan_labels = get_smart_labels(data, 'Eth_Plan', prefix_col='Eth_Name', is_integer=True, show_last_only=True)
                fig6.add_trace(go.Scatter(x=data['Date'], y=data['Eth_Plan'], mode='lines+text', text=plan_labels, textposition="bottom right", cliponaxis=False, textfont=label_style(COLORS['RED_PLAN']), line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot')))
                fig6.update_layout(**COMMON_LAYOUT, yaxis=dict(range=get_y_range(data, ['Eth_Act', 'Eth_Plan'])))
                st.plotly_chart(fig6, use_container_width=True, config=CHART_CONFIG)
                st.markdown(f'<p style="color:gray; font-size:13px; text-align:center;">💎 <b>Actual:</b> Eth Production | 🔴 <b>Plan:</b> Eth Target</p>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")