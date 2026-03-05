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

def fmt_val(v, precision=2, is_integer=False, prefix=""):
    if pd.isnull(v):
        return ""
    num_str = f"{int(round(float(v))):,}" if is_integer else f"{float(v):.{precision}f}"
    return f"{prefix} {num_str}".strip() if prefix else num_str

def get_y_range(df, columns, padding_top=0.6, padding_bottom=0.2):
    all_values = pd.concat([df[col] for col in columns if col in df.columns]).dropna()
    if all_values.empty:
        return [0, 100]
    v_min, v_max = all_values.min(), all_values.max()
    spread = v_max - v_min
    if spread == 0:
        return [v_min * 0.7, v_max * 1.5]
    return [v_min - (spread * padding_bottom), v_max + (spread * padding_top)]

# ─── Core annotation helpers ──────────────────────────────────────────────────
MIN_PIX_GAP = 20  # minimum pixel separation between labels at same x-position

def resolve_yshifts(entries, min_gap=MIN_PIX_GAP):
    """
    entries: list of (y_data_value, preferred_shift_direction)
             preferred_shift_direction: +1 = prefer above, -1 = prefer below
    Returns list of pixel yshift values, same order.
    Uses iterative push-apart in pixel space.
    """
    n = len(entries)
    if n == 0:
        return []
    # Initialise each label at its preferred side
    shifts = [e[1] * min_gap for e in entries]

    for _ in range(30):
        moved = False
        # Sort by (y_data + shift) to process bottom-to-top
        order = sorted(range(n), key=lambda i: entries[i][0] + shifts[i] * 0.01)
        for k in range(len(order) - 1):
            i, j = order[k], order[k + 1]
            gap = shifts[j] - shifts[i]
            overlap = min_gap - gap
            if overlap > 0:
                push = overlap / 2.0 + 1
                shifts[i] -= push
                shifts[j] += push
                moved = True
        if not moved:
            break
    return shifts

def make_ann(x, y, text, color, yshift=0, xanchor="center", xshift=0):
    return dict(
        x=x, y=y,
        text=f"<b>{text}</b>",
        xanchor=xanchor, yanchor="middle",
        xshift=xshift, yshift=yshift,
        showarrow=False,
        font=dict(color=color, family="Arial Black", size=11),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor=color, borderwidth=1, borderpad=3
    )

def build_anns_2series(df, col_act, col_plan, color_act, color_plan,
                        precision=2, is_integer=False, prefix_fn=None):
    """Annotations for charts with 1 actual + 1 plan line."""
    if df.empty:
        return []
    anns = []
    n = len(df)

    def pfx(idx):
        return prefix_fn(idx) if prefix_fn else ""

    # First point — actual only (above)
    v0 = df[col_act].iloc[0]
    if pd.notnull(v0):
        anns.append(make_ann(df['Date'].iloc[0], float(v0),
                             fmt_val(v0, precision, is_integer, pfx(0)),
                             color_act, yshift=+MIN_PIX_GAP))

    # Last point — actual + plan (push apart)
    entries = []
    meta = []
    for col, color, pref in [(col_act, color_act, +1), (col_plan, color_plan, -1)]:
        v = df[col].iloc[-1]
        if pd.notnull(v):
            entries.append((float(v), pref))
            meta.append((float(v), color, fmt_val(v, precision, is_integer, pfx(n - 1))))

    if entries:
        shifts = resolve_yshifts(entries)
        for (y, color, txt), ysh in zip(meta, shifts):
            anns.append(make_ann(df['Date'].iloc[-1], y, txt, color,
                                 yshift=ysh, xanchor="left", xshift=8))
    return anns


def build_anns_4series(df,
                        col_ac, col_ab, col_pc, col_pb,
                        color_ac, color_ab, color_plan,
                        precision=2, is_integer=False):
    """Annotations for charts with 2 actuals + 2 plan lines."""
    if df.empty:
        return []
    anns = []
    n = len(df)

    # First point — both actuals
    entries0, meta0 = [], []
    for col, color, pref in [(col_ac, color_ac, +1), (col_ab, color_ab, -1)]:
        v = df[col].iloc[0]
        if pd.notnull(v):
            entries0.append((float(v), pref))
            meta0.append((float(v), color, fmt_val(v, precision, is_integer)))
    if entries0:
        shifts = resolve_yshifts(entries0)
        for (y, color, txt), ysh in zip(meta0, shifts):
            anns.append(make_ann(df['Date'].iloc[0], y, txt, color, yshift=ysh))

    # Last point — all four series
    entries_l, meta_l = [], []
    for col, color, pref in [
        (col_ac, color_ac,   +1),
        (col_ab, color_ab,   -1),
        (col_pc, color_plan, +1),
        (col_pb, color_plan, -1),
    ]:
        v = df[col].iloc[-1]
        if pd.notnull(v):
            entries_l.append((float(v), pref))
            meta_l.append((float(v), color, fmt_val(v, precision, is_integer)))

    if entries_l:
        shifts = resolve_yshifts(entries_l)
        for (y, color, txt), ysh in zip(meta_l, shifts):
            anns.append(make_ann(df['Date'].iloc[-1], y, txt, color,
                                 yshift=ysh, xanchor="left", xshift=8))
    return anns


COLORS = {
    'CF_ACT':   '#1f77b4', 'CF_FILL':   'rgba(31, 119, 180, 0.15)',
    'Y_C_ACT':  '#2ca02c', 'Y_C_FILL':  'rgba(44, 160, 44, 0.15)',
    'Y_B_ACT':  '#9467bd', 'Y_B_FILL':  'rgba(148, 103, 189, 0.15)',
    'FS_C_ACT': '#00ced1', 'FS_C_FILL': 'rgba(0, 206, 209, 0.15)',
    'FS_B_ACT': '#ff8c00', 'FS_B_FILL': 'rgba(255, 140, 0, 0.15)',
    'VIN_ACT':  '#e377c2', 'VIN_FILL':  'rgba(227, 119, 194, 0.15)',
    'SALE_ACT': '#edc948', 'SALE_FILL': 'rgba(237, 201, 72, 0.15)',
    'ETH_ACT':  '#17becf', 'ETH_FILL':  'rgba(23, 190, 207, 0.15)',
    'RED_PLAN': '#d62728'
}
CHART_CONFIG = {'displayModeBar': False}

# ─── Data Loading ──────────────────────────────────────────────────────────────
try:
    df_raw = pd.read_excel("Actual vs Plan.xlsx", engine="openpyxl")
    cols = [1, 15, 16, 17, 26, 27, 28, 7, 8, 29, 30, 11, 31, 12, 32, 22, 23, 36]
    chart_data = df_raw.iloc[:, cols].copy()
    chart_data.columns = [
        'Date', 'CF_Actual', 'Yield_C_Act', 'Yield_B_Act',
        'CF_Target', 'Yield_C_Plan', 'Yield_B_Plan',
        'FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan',
        'Vin_Act', 'Vin_Plan', 'Sale_Act', 'Sale_Plan',
        'Eth_Name', 'Eth_Act', 'Eth_Plan'
    ]
    chart_data['Date'] = pd.to_datetime(chart_data['Date'], errors='coerce')
    chart_data = chart_data.dropna(subset=['Date']).sort_values('Date')

    head_col, set_col = st.columns([2, 1])
    with set_col:
        st.write("##")
        with st.expander("⚙️ REPORT SETTINGS", expanded=True):
            date_range = st.date_input("Select Date Range",
                                       value=(date(2026, 1, 1), date(2026, 1, 31)))

    if isinstance(date_range, tuple) and len(date_range) == 2:
        data = chart_data[
            (chart_data['Date'].dt.date >= date_range[0]) &
            (chart_data['Date'].dt.date <= date_range[1])
        ]

        with head_col:
            st.title("🚀 DC Daily Production Dashboard")
            latest_date = data['Date'].max() if not data.empty else None
            date_str = (latest_date.strftime('%d %B %Y').upper()
                        if pd.notnull(latest_date) else 'N/A')
            st.markdown(
                f'<div class="latest-date-box">'
                f'<p class="latest-date-text">LATEST DATA UPDATE AS OF</p>'
                f'<p class="latest-date-value">{date_str}</p></div>',
                unsafe_allow_html=True
            )

        if not data.empty:
            COMMON_LAYOUT = dict(
                template="plotly_white", height=350,
                margin=dict(t=50, b=10, l=50, r=220),
                xaxis=dict(automargin=True),
                showlegend=False
            )

            # ── Row 1 ──────────────────────────────────────────────────────────
            c1, c2 = st.columns(2)

            with c1:
                st.subheader("1. CF Performance")
                anns = build_anns_2series(
                    data, 'CF_Actual', 'CF_Target',
                    COLORS['CF_ACT'], COLORS['RED_PLAN'], precision=3
                )
                fig1 = go.Figure([
                    go.Scatter(x=data['Date'], y=data['CF_Actual'],
                               mode='lines+markers',
                               line=dict(color=COLORS['CF_ACT'], width=3),
                               fill='tozeroy', fillcolor=COLORS['CF_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['CF_Target'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dash'),
                               cliponaxis=False),
                ])
                fig1.update_layout(**COMMON_LAYOUT,
                                   yaxis=dict(range=get_y_range(data, ['CF_Actual', 'CF_Target'])),
                                   annotations=anns)
                st.plotly_chart(fig1, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['CF_ACT']), ("Target", COLORS['RED_PLAN'])])

            with c2:
                st.subheader("2. Yield Performance")
                anns = build_anns_4series(
                    data,
                    'Yield_C_Act', 'Yield_B_Act', 'Yield_C_Plan', 'Yield_B_Plan',
                    COLORS['Y_C_ACT'], COLORS['Y_B_ACT'], COLORS['RED_PLAN'],
                    is_integer=True
                )
                fig2 = go.Figure([
                    go.Scatter(x=data['Date'], y=data['Yield_C_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['Y_C_ACT'], width=3),
                               fill='tozeroy', fillcolor=COLORS['Y_C_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['Yield_B_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['Y_B_ACT'], width=3),
                               fill='tonexty', fillcolor=COLORS['Y_B_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['Yield_C_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['Yield_B_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                ])
                fig2.update_layout(
                    **COMMON_LAYOUT,
                    yaxis=dict(range=get_y_range(
                        data, ['Yield_C_Act', 'Yield_B_Act', 'Yield_C_Plan', 'Yield_B_Plan'])),
                    annotations=anns
                )
                st.plotly_chart(fig2, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Yield C", COLORS['Y_C_ACT']),
                               ("Yield B", COLORS['Y_B_ACT']),
                               ("Plan", COLORS['RED_PLAN'])])

            st.write("---")
            # ── Row 2 ──────────────────────────────────────────────────────────
            c3, c4 = st.columns(2)

            with c3:
                st.subheader("3. %FS Raw Material")
                anns = build_anns_4series(
                    data,
                    'FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan',
                    COLORS['FS_C_ACT'], COLORS['FS_B_ACT'], COLORS['RED_PLAN'],
                    precision=2
                )
                fig3 = go.Figure([
                    go.Scatter(x=data['Date'], y=data['FS_C_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['FS_C_ACT'], width=3),
                               fill='tozeroy', fillcolor=COLORS['FS_C_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['FS_B_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['FS_B_ACT'], width=3),
                               fill='tonexty', fillcolor=COLORS['FS_B_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['FS_C_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['FS_B_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                ])
                fig3.update_layout(
                    **COMMON_LAYOUT,
                    yaxis=dict(range=get_y_range(
                        data, ['FS_C_Act', 'FS_B_Act', 'FS_C_Plan', 'FS_B_Plan'])),
                    annotations=anns
                )
                st.plotly_chart(fig3, use_container_width=True, config=CHART_CONFIG)
                render_legend([("FS C", COLORS['FS_C_ACT']),
                               ("FS B", COLORS['FS_B_ACT']),
                               ("Plan", COLORS['RED_PLAN'])])

            with c4:
                st.subheader("4. Vinasses Production")
                anns = build_anns_2series(
                    data, 'Vin_Act', 'Vin_Plan',
                    COLORS['VIN_ACT'], COLORS['RED_PLAN'], is_integer=True
                )
                fig4 = go.Figure([
                    go.Scatter(x=data['Date'], y=data['Vin_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['VIN_ACT'], width=3),
                               fill='tozeroy', fillcolor=COLORS['VIN_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['Vin_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                ])
                fig4.update_layout(**COMMON_LAYOUT,
                                   yaxis=dict(range=get_y_range(data, ['Vin_Act', 'Vin_Plan'])),
                                   annotations=anns)
                st.plotly_chart(fig4, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['VIN_ACT']), ("Plan", COLORS['RED_PLAN'])])

            st.write("---")
            # ── Row 3 ──────────────────────────────────────────────────────────
            c5, c6 = st.columns(2)

            with c5:
                st.subheader("5. Vinasses Sale")
                anns = build_anns_2series(
                    data, 'Sale_Act', 'Sale_Plan',
                    COLORS['SALE_ACT'], COLORS['RED_PLAN'], is_integer=True
                )
                fig5 = go.Figure([
                    go.Scatter(x=data['Date'], y=data['Sale_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['SALE_ACT'], width=3),
                               fill='tozeroy', fillcolor=COLORS['SALE_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['Sale_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                ])
                fig5.update_layout(**COMMON_LAYOUT,
                                   yaxis=dict(range=get_y_range(data, ['Sale_Act', 'Sale_Plan'])),
                                   annotations=anns)
                st.plotly_chart(fig5, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['SALE_ACT']), ("Plan", COLORS['RED_PLAN'])])

            with c6:
                st.subheader("6. Ethanol Production")

                # Ethanol: prefix from Eth_Name column
                def eth_prefix_fn(idx):
                    v = data['Eth_Name'].iloc[idx]
                    return str(v) if pd.notnull(v) else ""

                anns = build_anns_2series(
                    data, 'Eth_Act', 'Eth_Plan',
                    COLORS['ETH_ACT'], COLORS['RED_PLAN'],
                    is_integer=True, prefix_fn=eth_prefix_fn
                )
                fig6 = go.Figure([
                    go.Scatter(x=data['Date'], y=data['Eth_Act'],
                               mode='lines+markers',
                               line=dict(color=COLORS['ETH_ACT'], width=3),
                               fill='tozeroy', fillcolor=COLORS['ETH_FILL'], cliponaxis=False),
                    go.Scatter(x=data['Date'], y=data['Eth_Plan'],
                               mode='lines',
                               line=dict(color=COLORS['RED_PLAN'], width=2, dash='dot'),
                               cliponaxis=False),
                ])
                fig6.update_layout(**COMMON_LAYOUT,
                                   yaxis=dict(range=get_y_range(data, ['Eth_Act', 'Eth_Plan'])),
                                   annotations=anns)
                st.plotly_chart(fig6, use_container_width=True, config=CHART_CONFIG)
                render_legend([("Actual", COLORS['ETH_ACT']), ("Plan", COLORS['RED_PLAN'])])

        else:
            st.warning("No data found for the selected date range.")

except Exception as e:
    st.error(f"System Error: {e}")