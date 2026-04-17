"""
app.py
------
Graham Number + DCF Financial Dashboard — Indian Stocks (NSE)
A professional-grade valuation tool demonstrating financial analysis &
software engineering skills.

Tabs
----
1. Overview        — Company snapshot, key metrics, 5-year price chart
2. Valuation       — Graham Number, ratio analysis, margin-of-safety gauge
3. DCF Analysis    — 3-stage DCF model with adjustable assumptions
4. Sensitivity     — Heatmap: DCF intrinsic value vs WACC & terminal growth
5. Compare         — Side-by-side analysis of up to 4 stocks
"""

# ─── standard library ────────────────────────────────────────────────────────
import math

# ─── third-party ─────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ─── local modules ───────────────────────────────────────────────────────────
from stocks import STOCKS, SORTED_LABELS
from data import fetch_stock_data, fetch_price_history, safe_get
from valuation import (
    calculate_graham,
    calculate_ratios,
    estimate_wacc,
    calculate_dcf,
    run_sensitivity,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Valuation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  — subtle polish without heavy custom styling
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* tighten tab spacing */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { padding: 6px 18px; border-radius: 6px 6px 0 0; }
    /* metric card highlight */
    [data-testid="metric-container"] {
        background: #f8f9fc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
    }
    /* section sub-headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e293b;
        margin: 1rem 0 0.5rem;
        padding-bottom: 4px;
        border-bottom: 2px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def fmt(value, prefix="₹", suffix="", decimals=2):
    """Format a number as a readable string with optional prefix/suffix.

    Returns "N/A" if value is None.
    """
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.{decimals}f}{suffix}"


def fmt_pct(value, decimals=2):
    """Format a decimal ratio as a percentage string (e.g. 0.18 → '18.00%')."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def make_gauge(current, target, title="Price vs Fair Value"):
    """Create a Plotly gauge chart comparing current price vs a target (fair value).

    Parameters
    ----------
    current : float
        Current market price.
    target : float
        Fair-value estimate (Graham Number or DCF).
    title : str
        Chart title.
    """
    max_range = max(current, target) * 1.65
    is_under   = current < target
    bar_color  = "#22c55e" if is_under else "#ef4444"

    fig = go.Figure(go.Indicator(
        mode  = "gauge+number+delta",
        value = current,
        number= {"prefix": "₹", "valueformat": ",.0f", "font": {"size": 30}},
        delta = {
            "reference"  : target,
            "prefix"     : "₹",
            "valueformat": ",.0f",
            "increasing" : {"color": "#ef4444"},
            "decreasing" : {"color": "#22c55e"},
        },
        title = {"text": title, "font": {"size": 14}},
        gauge = {
            "axis"     : {"range": [0, max_range], "tickprefix": "₹", "tickformat": ","},
            "bar"      : {"color": bar_color, "thickness": 0.28},
            "steps"    : [
                {"range": [0, target],    "color": "rgba(34,197,94,0.12)"},
                {"range": [target, max_range], "color": "rgba(239,68,68,0.12)"},
            ],
            "threshold": {
                "line" : {"color": "#1e40af", "width": 3},
                "value": target,
                "thickness": 0.85,
            },
        },
    ))
    fig.update_layout(height=270, margin={"t": 50, "b": 10, "l": 20, "r": 20})
    return fig


def make_bar_comparison(labels, values, colors, title=""):
    """Horizontal or vertical grouped bar chart for value comparisons."""
    fig = go.Figure()
    for label, value, color in zip(labels, values, colors):
        fig.add_trace(go.Bar(
            name=label, x=[label], y=[value],
            marker_color=color,
            text=[f"₹{value:,.0f}"],
            textposition="outside",
        ))
    fig.update_layout(
        title=title, showlegend=False,
        yaxis={"tickprefix": "₹", "tickformat": ","},
        height=320, margin={"t": 50, "b": 20, "l": 10, "r": 10},
    )
    return fig


def make_historical_chart(hist: pd.DataFrame, ticker: str) -> go.Figure:
    """Candlestick + volume chart for 5-year price history.

    Parameters
    ----------
    hist : pd.DataFrame
        OHLCV DataFrame from yfinance.
    ticker : str
        Ticker symbol — shown in the chart title.
    """
    fig = go.Figure()

    # Closing price line
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        name="Close Price",
        line={"color": "#3b82f6", "width": 1.8},
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)",
    ))

    # 50-day and 200-day simple moving averages
    if len(hist) >= 50:
        hist["SMA50"] = hist["Close"].rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["SMA50"],
            name="50-Day SMA",
            line={"color": "#f59e0b", "width": 1.3, "dash": "dot"},
        ))
    if len(hist) >= 200:
        hist["SMA200"] = hist["Close"].rolling(200).mean()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["SMA200"],
            name="200-Day SMA",
            line={"color": "#8b5cf6", "width": 1.3, "dash": "dash"},
        ))

    fig.update_layout(
        title=f"{ticker} — 5-Year Price History",
        xaxis_title="Date",
        yaxis={"title": "Price (₹)", "tickprefix": "₹", "tickformat": ","},
        legend={"orientation": "h", "y": 1.08},
        height=380,
        margin={"t": 60, "b": 30, "l": 10, "r": 10},
        hovermode="x unified",
    )
    return fig


def make_sensitivity_heatmap(df: pd.DataFrame, current_price: float) -> go.Figure:
    """Plotly heatmap of DCF intrinsic value vs WACC and terminal growth.

    Highlights cells where intrinsic value > current price in green.
    """
    z_values = df.values.astype(float)
    x_labels = list(df.columns)
    y_labels  = list(df.index)

    # Diverging colour scale centred on current price
    fig = go.Figure(go.Heatmap(
        z=z_values, x=x_labels, y=y_labels,
        colorscale=[
            [0.0, "#ef4444"],   # Low values → red (overvalued)
            [0.5, "#fef08a"],   # Near current price → yellow
            [1.0, "#22c55e"],   # High values → green (undervalued)
        ],
        zmid=current_price,
        text=[[f"₹{v:,.0f}" if not math.isnan(v) else "—" for v in row] for row in z_values],
        texttemplate="%{text}",
        textfont={"size": 11},
        colorbar={"title": "Fair Value (₹)", "tickprefix": "₹", "tickformat": ","},
    ))

    fig.update_layout(
        title=f"DCF Sensitivity  |  Current Price: ₹{current_price:,.0f}",
        xaxis_title="Terminal Growth Rate",
        yaxis_title="WACC",
        height=420,
        margin={"t": 60, "b": 40, "l": 80, "r": 20},
    )
    return fig


def make_dcf_waterfall(result: dict) -> go.Figure:
    """Waterfall chart showing the three DCF value components."""
    labels = ["Stage 1\n(High Growth)", "Stage 2\n(Transition)", "Terminal\nValue", "Intrinsic\nValue"]
    values = [
        result["pv_stage1"],
        result["pv_stage2"],
        result["pv_terminal"],
        result["intrinsic_value"],
    ]
    measures = ["relative", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        name="DCF Components", orientation="v",
        measure=measures, x=labels, y=values,
        texttemplate="₹%{y:,.0f}",
        textposition="outside",
        connector={"line": {"color": "#94a3b8"}},
        increasing={"marker": {"color": "#22c55e"}},
        totals={"marker": {"color": "#3b82f6"}},
    ))
    fig.update_layout(
        title="DCF Value Components (Per Share)",
        yaxis={"title": "₹ Per Share", "tickprefix": "₹", "tickformat": ","},
        height=340,
        margin={"t": 60, "b": 30, "l": 10, "r": 10},
        showlegend=False,
    )
    return fig


def ratio_badge(value, label, good_range=None, unit=""):
    """Render a styled metric card with an optional colour indicator."""
    if value is None:
        st.metric(label, "N/A")
        return
    display_val = f"{value:,.2f}{unit}"
    st.metric(label, display_val)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER  ────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Stock Valuation Dashboard — Indian Markets")
st.caption(
    "Graham Number · DCF (3-Stage) · Ratio Analysis · Sensitivity · Comparison  "
    "| Data sourced from Yahoo Finance via yfinance"
)
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# STOCK SELECTION SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
col_sel, col_cust, col_btn = st.columns([3, 1.5, 1])

with col_sel:
    chosen_label = st.selectbox(
        "🔍 Search & select a stock",
        ["— choose a company —"] + SORTED_LABELS,
        help="Start typing the company name to filter."
    )

with col_cust:
    custom_ticker = st.text_input(
        "Or enter a ticker",
        placeholder="e.g. ZOMATO.NS",
        help="NSE format: SYMBOL.NS"
    )

with col_btn:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    analyse = st.button("Analyse  🚀", type="primary", use_container_width=True)

# Resolve the ticker to use
if custom_ticker.strip():
    TICKER = custom_ticker.strip().upper()
elif chosen_label != "— choose a company —":
    TICKER = STOCKS[chosen_label]
else:
    TICKER = None

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# COMPARE TAB  — early check: let user also select stocks for comparison here
# (we build the compare list in the tab below, keyed by session state)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOGIC
# ─────────────────────────────────────────────────────────────────────────────
if not analyse and TICKER is None:
    # Landing state — show instructions
    st.info(
        "👆 Select a stock from the dropdown (or type a custom ticker) and click **Analyse**.",
        icon="ℹ️",
    )
    st.stop()   # st.stop() halts the script here; nothing below renders

if analyse and TICKER is None:
    st.warning("Please select a stock before clicking Analyse.")
    st.stop()

# If the user previously analysed a different ticker, treat the new selection as fresh
# (session state tracks the last analysed ticker to support the Compare tab)
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None

# ── Fetch data ────────────────────────────────────────────────────────────────
with st.spinner(f"Loading data for **{TICKER}** …"):
    info = fetch_stock_data(TICKER)
    hist = fetch_price_history(TICKER)

if not info:
    st.error(
        f"No data found for **{TICKER}**.  "
        "Check the ticker format (e.g. `RELIANCE.NS`) and try again."
    )
    st.stop()

# ── Core values ───────────────────────────────────────────────────────────────
price        = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
eps          = safe_get(info, "trailingEps")
bvps         = safe_get(info, "bookValue")
company_name = safe_get(info, "longName", TICKER)
sector       = safe_get(info, "sector", "")
industry     = safe_get(info, "industry", "")
market_cap   = safe_get(info, "marketCap")
shares_out   = safe_get(info, "sharesOutstanding")
fcf_total    = safe_get(info, "freeCashflow")   # total FCF in ₹ (not per share)

# Per-share FCF for DCF
fcf_per_share = None
if fcf_total and shares_out and shares_out > 0:
    fcf_per_share = fcf_total / shares_out

# Graham Number
graham = calculate_graham(eps, bvps)

# Ratios
ratios = calculate_ratios(info)

# WACC
wacc_est = estimate_wacc(info)

# Store in session state so Compare tab can access
st.session_state.last_ticker = TICKER
if "compare_data" not in st.session_state:
    st.session_state.compare_data = {}
st.session_state.compare_data[TICKER] = {
    "name"  : company_name,
    "price" : price,
    "graham": graham,
    "ratios": ratios,
    "eps"   : eps,
    "bvps"  : bvps,
}

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview",
    "📐 Valuation",
    "💹 DCF Analysis",
    "🔬 Sensitivity",
    "⚖️ Compare",
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    # Company header
    st.markdown(f"### {company_name}")
    if sector:
        st.caption(f"{sector}  ·  {industry}  ·  `{TICKER}`")

    st.markdown("")

    # ── KPI row ──────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Current Price", fmt(price))
    with k2:
        cap_str = "N/A"
        if market_cap:
            if market_cap >= 1e12:
                cap_str = f"₹{market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                cap_str = f"₹{market_cap/1e9:.2f}B"
            else:
                cap_str = f"₹{market_cap/1e6:.0f}M"
        st.metric("Market Cap", cap_str)
    with k3:
        st.metric("Trailing EPS", fmt(eps))
    with k4:
        st.metric("Book Value / Share", fmt(bvps))
    with k5:
        week_high = safe_get(info, "fiftyTwoWeekHigh")
        week_low  = safe_get(info, "fiftyTwoWeekLow")
        rng_str   = f"₹{week_low:,.0f} – ₹{week_high:,.0f}" if week_high and week_low else "N/A"
        st.metric("52-Week Range", rng_str)

    st.markdown("")

    # ── 5-Year Price Chart ────────────────────────────────────────────────
    if not hist.empty:
        st.plotly_chart(make_historical_chart(hist, TICKER), use_container_width=True)
    else:
        st.info("Historical price data not available for this ticker.")

    # ── Company description ───────────────────────────────────────────────
    desc = safe_get(info, "longBusinessSummary")
    if desc:
        with st.expander("About the company"):
            st.write(desc)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — VALUATION (Graham + Ratios)
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Graham Number Valuation")
    st.caption(
        "Benjamin Graham's formula: **√(22.5 × EPS × Book Value Per Share)**  |  "
        "Based on his rule: P/E ≤ 15 and P/B ≤ 1.5  →  15 × 1.5 = **22.5**"
    )
    st.markdown("")

    if graham is None:
        if eps and eps <= 0:
            st.warning(f"Graham Number cannot be computed — EPS is negative (₹{eps:.2f}).")
        elif bvps and bvps <= 0:
            st.warning(f"Graham Number cannot be computed — Book Value is negative (₹{bvps:.2f}).")
        else:
            st.warning("EPS or Book Value data is unavailable for this ticker.")
    else:
        pct_diff = (graham - price) / graham * 100   # + = undervalued, - = overvalued
        is_under = price < graham

        # Verdict banner
        if is_under:
            mos = abs(pct_diff)
            st.success(
                f"✅ **Undervalued** — trading **{mos:.1f}% below** the Graham Number.  "
                "May offer a margin of safety for value investors."
            )
            st.balloons()
        else:
            prem = abs(pct_diff)
            st.error(
                f"🔴 **Overvalued** — trading **{prem:.1f}% above** the Graham Number.  "
                "May be priced above its Benjamin Graham intrinsic value."
            )

        st.markdown("")

        # ── Metric row ────────────────────────────────────────────────────
        v1, v2, v3 = st.columns(3)
        with v1:
            st.metric("Current Price", fmt(price))
        with v2:
            delta_val = graham - price
            st.metric(
                "Graham Number",
                fmt(graham),
                delta=f"₹{abs(delta_val):,.2f} {'above' if delta_val > 0 else 'below'} price",
                delta_color="normal" if delta_val > 0 else "inverse",
            )
        with v3:
            label = "Margin of Safety" if is_under else "Premium to Fair Value"
            st.metric(label, f"{abs(pct_diff):.1f}%",
                      delta_color="normal" if is_under else "inverse")

        st.markdown("")

        # ── Side-by-side: gauge + bar ─────────────────────────────────────
        gc, bc = st.columns(2)
        with gc:
            st.plotly_chart(
                make_gauge(price, graham, "Current Price vs Graham Number"),
                use_container_width=True
            )
        with bc:
            bar_colors = ["#3b82f6", "#22c55e" if is_under else "#ef4444"]
            st.plotly_chart(
                make_bar_comparison(
                    ["Current Price", "Graham Number"],
                    [price, graham],
                    bar_colors,
                    title="Price vs Graham Number (₹)"
                ),
                use_container_width=True
            )

        # ── Formula breakdown ─────────────────────────────────────────────
        with st.expander("🧮 Step-by-step formula"):
            st.markdown(f"""
| Step | Expression | Value |
|------|-----------|-------|
| EPS (TTM) | Trailing earnings per share | **₹ {eps:,.2f}** |
| Book Value Per Share | From balance sheet | **₹ {bvps:,.2f}** |
| 22.5 × EPS × BVPS | 22.5 × {eps:.2f} × {bvps:.2f} | **{22.5*eps*bvps:,.2f}** |
| Graham Number | √({22.5*eps*bvps:,.2f}) | **₹ {graham:,.2f}** |
| Current Price | Live quote | **₹ {price:,.2f}** |
| Verdict | Price {'<' if is_under else '>'} Graham Number | **{'Undervalued ✅' if is_under else 'Overvalued 🔴'}** |
""")

    # ── Ratio Analysis ────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Key Ratios")

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("P/E (Trailing)", fmt_pct(ratios.get("P/E (Trailing)"), 1).replace("%","×") if ratios.get("P/E (Trailing)") else "N/A")
        st.metric("P/E (Forward)",  fmt_pct(ratios.get("P/E (Forward)"), 1).replace("%","×")  if ratios.get("P/E (Forward)")  else "N/A")
    with r2:
        st.metric("P/B Ratio", f"{ratios.get('P/B', 'N/A')}×" if ratios.get("P/B") else "N/A")
        st.metric("EPS Growth", fmt_pct(ratios.get("EPS Growth (%)"), 1) if ratios.get("EPS Growth (%)") is not None else "N/A")
    with r3:
        st.metric("ROE", fmt_pct(ratios.get("ROE (%)"), 1) if ratios.get("ROE (%)") is not None else "N/A")
        st.metric("ROIC", fmt_pct(ratios.get("ROIC (%)"), 1) if ratios.get("ROIC (%)") is not None else "N/A")
    with r4:
        st.metric("Debt / Equity", f"{ratios.get('Debt / Equity', 'N/A')}×" if ratios.get("Debt / Equity") is not None else "N/A")
        st.metric("Dividend Yield", fmt_pct(ratios.get("Dividend Yield (%)"), 2) if ratios.get("Dividend Yield (%)") is not None else "N/A")

    # Ratio context table
    st.markdown("")
    ratio_rows = []
    for key, val in ratios.items():
        ratio_rows.append({"Ratio": key, "Value": f"{val:,.2f}" if val is not None else "N/A"})
    st.dataframe(pd.DataFrame(ratio_rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — DCF ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 3-Stage Discounted Cash Flow (DCF) Valuation")
    st.caption(
        "Stage 1: High growth  ·  Stage 2: Linear transition  ·  Stage 3: Terminal value (Gordon Growth Model)"
    )

    # ── FCF check ─────────────────────────────────────────────────────────
    if fcf_per_share is None or fcf_per_share <= 0:
        # Fallback: use EPS as a conservative proxy for FCF per share
        fallback_fcf = eps if (eps and eps > 0) else None
        if fallback_fcf:
            st.info(
                f"Free Cash Flow data is not available from Yahoo Finance for **{company_name}**.  "
                f"Using **Trailing EPS (₹{eps:.2f})** as a proxy for FCF per share."
            )
            fcf_per_share = fallback_fcf
        else:
            st.warning(
                "Neither Free Cash Flow nor positive EPS data is available.  "
                "Please use the manual input below."
            )
            fcf_per_share = 0.0

    # ── DCF Assumption Controls ───────────────────────────────────────────
    st.markdown('<div class="section-header">DCF Assumptions</div>', unsafe_allow_html=True)
    da1, da2, da3 = st.columns(3)

    with da1:
        fcf_input = st.number_input(
            "Base FCF per Share (₹)",
            min_value=0.01, max_value=50000.0,
            value=float(round(fcf_per_share, 2)) if fcf_per_share else 1.0,
            step=1.0,
            help="Starting Free Cash Flow per share. Auto-populated from Yahoo Finance or EPS."
        )
        g1_pct = st.slider(
            "Stage 1 Growth Rate (%)",
            min_value=0, max_value=50, value=20,
            help="Expected annual FCF growth during high-growth phase."
        )
        yr1 = st.slider("Stage 1 Duration (years)", 1, 10, 5)

    with da2:
        g2_pct = st.slider(
            "Stage 2 Terminal Growth (%)",
            min_value=0, max_value=20, value=10,
            help="Growth rate that Stage 2 transitions down to (then continues to terminal)."
        )
        yr2 = st.slider("Stage 2 Duration (years)", 1, 10, 5)
        terminal_pct = st.slider(
            "Terminal Growth Rate (%)",
            min_value=1, max_value=10, value=4,
            help="Long-run perpetuity growth (India long-run GDP ≈ 6–7 %; use conservatively)."
        )

    with da3:
        # Show WACC estimate but let user override
        wacc_pct = st.slider(
            "WACC (%)",
            min_value=5, max_value=25,
            value=int(round(wacc_est * 100)),
            help=f"Estimated WACC: {wacc_est*100:.1f}% (Rf=7.2%, ERP=7%, β={safe_get(info,'beta',1.0):.2f})"
        )
        st.markdown("")
        st.markdown(
            f"**WACC Breakdown**  \n"
            f"Risk-free rate: 7.2%  \n"
            f"Beta: {safe_get(info,'beta',1.0):.2f}  \n"
            f"Equity Risk Premium: 7.0%  \n"
            f"Estimated Ke: {(7.2 + safe_get(info,'beta',1.0)*7.0):.1f}%"
        )

    # ── Run DCF ───────────────────────────────────────────────────────────
    g1  = g1_pct  / 100
    g2  = g2_pct  / 100
    gT  = terminal_pct / 100
    w   = wacc_pct / 100

    dcf_result = calculate_dcf(
        fcf_input, g1, yr1, g2, yr2, gT, w
    )

    st.divider()

    if not dcf_result:
        st.error("DCF calculation failed — WACC must be greater than the terminal growth rate.")
    else:
        iv = dcf_result["intrinsic_value"]
        dcf_pct_diff = (iv - price) / iv * 100 if iv else 0
        dcf_under    = price < iv

        # Verdict
        if dcf_under:
            st.success(
                f"✅ **DCF: Undervalued** — Intrinsic Value **₹{iv:,.2f}**  vs  "
                f"Market Price ₹{price:,.2f}  |  "
                f"Margin of Safety: **{abs(dcf_pct_diff):.1f}%**"
            )
        else:
            st.error(
                f"🔴 **DCF: Overvalued** — Intrinsic Value **₹{iv:,.2f}**  vs  "
                f"Market Price ₹{price:,.2f}  |  "
                f"Premium: **{abs(dcf_pct_diff):.1f}%**"
            )

        st.markdown("")

        # KPI metrics
        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            st.metric("DCF Intrinsic Value", fmt(iv))
        with dc2:
            st.metric("PV — Stage 1", fmt(dcf_result["pv_stage1"]))
        with dc3:
            st.metric("PV — Stage 2", fmt(dcf_result["pv_stage2"]))
        with dc4:
            st.metric("PV — Terminal", fmt(dcf_result["pv_terminal"]))

        st.markdown("")

        # Charts
        ch1, ch2 = st.columns(2)
        with ch1:
            st.plotly_chart(make_dcf_waterfall(dcf_result), use_container_width=True)
        with ch2:
            st.plotly_chart(
                make_gauge(price, iv, "Market Price vs DCF Fair Value"),
                use_container_width=True
            )

        # Year-by-year cash flow table
        with st.expander("📋 Projected cash flows (year by year)"):
            cf_rows = [
                {"Year": yr, "Nominal FCF (₹)": f"₹{fcf:,.2f}", "Present Value (₹)": f"₹{pv:,.2f}"}
                for yr, fcf, pv in dcf_result["stage_cashflows"]
            ]
            cf_rows.append({
                "Year": "Terminal",
                "Nominal FCF (₹)": f"₹{dcf_result['terminal_value']:,.2f}",
                "Present Value (₹)": f"₹{dcf_result['pv_terminal']:,.2f}",
            })
            st.dataframe(pd.DataFrame(cf_rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — SENSITIVITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### DCF Sensitivity Analysis")
    st.caption(
        "How does the DCF intrinsic value change when WACC and terminal growth rate vary?  "
        "Green cells = undervalued (market price < intrinsic value).  "
        "Red cells = overvalued."
    )

    if not dcf_result:
        st.warning("Run the DCF tab first (WACC must exceed terminal growth rate).")
    elif not fcf_input or fcf_input <= 0:
        st.warning("Please set a valid FCF per share in the DCF tab.")
    else:
        # WACC range: ±3 pp around the selected WACC
        base_w = wacc_pct / 100
        wacc_range  = [round(base_w - 0.03 + i * 0.01, 3) for i in range(7)]  # 7 steps
        wacc_range  = [w for w in wacc_range if 0.05 <= w <= 0.25]

        # Terminal growth range: 2 % → 7 %
        terminal_range = [round(0.02 + i * 0.01, 2) for i in range(6)]

        with st.spinner("Computing sensitivity matrix …"):
            sensitivity_df = run_sensitivity(
                fcf_input, g1, yr1, g2, yr2, wacc_range, terminal_range
            )

        st.plotly_chart(
            make_sensitivity_heatmap(sensitivity_df, price),
            use_container_width=True
        )

        st.markdown("**Sensitivity Table (₹ per share)**")
        # Format each cell as currency (column-wise apply avoids deprecated applymap)
        formatted_df = sensitivity_df.copy()
        for col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(
                lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—"
            )
        st.dataframe(formatted_df, use_container_width=True)

        st.caption(
            f"Assumptions held constant — Stage 1 growth: {g1_pct}%,  "
            f"Stage 1 duration: {yr1}y,  Stage 2 end-growth: {g2_pct}%,  "
            f"Stage 2 duration: {yr2}y.  Rows = WACC, Columns = Terminal Growth."
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — SIDE-BY-SIDE COMPARISON
# ═══════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### Multi-Stock Comparison")
    st.caption("Analyse up to 4 NSE stocks side by side on key valuation and profitability metrics.")

    # Stock selector for comparison
    compare_labels = st.multiselect(
        "Select stocks to compare",
        options=SORTED_LABELS,
        default=[chosen_label] if chosen_label != "— choose a company —" else [],
        max_selections=4,
        help="Choose 2–4 companies to compare."
    )

    if len(compare_labels) < 2:
        st.info("Select at least 2 stocks from the dropdown above to enable comparison.")
    else:
        compare_tickers = [STOCKS[lbl] for lbl in compare_labels]

        # Fetch all comparison stocks
        compare_rows = []
        compare_prices   = []
        compare_grahams  = []
        compare_names    = []

        with st.spinner("Fetching comparison data …"):
            for ticker_c, label_c in zip(compare_tickers, compare_labels):
                info_c  = fetch_stock_data(ticker_c)
                if not info_c:
                    st.warning(f"Could not load data for {ticker_c}. Skipping.")
                    continue
                price_c  = safe_get(info_c, "currentPrice") or safe_get(info_c, "regularMarketPrice")
                eps_c    = safe_get(info_c, "trailingEps")
                bvps_c   = safe_get(info_c, "bookValue")
                graham_c = calculate_graham(eps_c, bvps_c)
                ratios_c = calculate_ratios(info_c)
                name_c   = safe_get(info_c, "longName", ticker_c)

                compare_names.append(label_c)
                compare_prices.append(price_c)
                compare_grahams.append(graham_c)

                row = {"Company": name_c, "Ticker": ticker_c}
                row["Price (₹)"]      = f"₹{price_c:,.2f}" if price_c else "N/A"
                row["Graham No. (₹)"] = f"₹{graham_c:,.2f}" if graham_c else "N/A"
                if price_c and graham_c:
                    mos = (graham_c - price_c) / graham_c * 100
                    row["Margin of Safety"] = f"{mos:+.1f}%"
                else:
                    row["Margin of Safety"] = "N/A"

                for ratio_key in ["P/E (Trailing)", "P/B", "ROE (%)", "ROIC (%)", "Debt / Equity"]:
                    val = ratios_c.get(ratio_key)
                    row[ratio_key] = f"{val:.2f}" if val is not None else "N/A"

                compare_rows.append(row)

        # Summary table
        if compare_rows:
            comp_df = pd.DataFrame(compare_rows)
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

        st.markdown("")

        # Price vs Graham Number bar chart for all selected stocks
        valid_pairs = [
            (n, p, g) for n, p, g in zip(compare_names, compare_prices, compare_grahams)
            if p and g
        ]
        if valid_pairs:
            names_vp, prices_vp, grahams_vp = zip(*valid_pairs)
            comp_fig = go.Figure()
            comp_fig.add_trace(go.Bar(
                name="Current Price",
                x=list(names_vp), y=list(prices_vp),
                marker_color="#3b82f6",
                text=[f"₹{v:,.0f}" for v in prices_vp],
                textposition="outside",
            ))
            comp_fig.add_trace(go.Bar(
                name="Graham Number",
                x=list(names_vp), y=list(grahams_vp),
                marker_color="#22c55e",
                text=[f"₹{v:,.0f}" for v in grahams_vp],
                textposition="outside",
            ))
            comp_fig.update_layout(
                barmode="group",
                title="Price vs Graham Number — Comparison",
                yaxis={"title": "₹ Per Share", "tickprefix": "₹", "tickformat": ","},
                legend={"orientation": "h", "y": 1.08},
                height=400,
                margin={"t": 60, "b": 30, "l": 10, "r": 10},
            )
            st.plotly_chart(comp_fig, use_container_width=True)

        # Ratio comparison radar chart
        radar_metrics = ["P/E (Trailing)", "P/B", "ROE (%)", "ROIC (%)"]
        radar_rows = []
        for row in compare_rows:
            vals = []
            for m in radar_metrics:
                raw = row.get(m, "N/A")
                try:
                    vals.append(float(raw.replace("%","").replace("×","").replace("₹","").replace(",","")))
                except Exception:
                    vals.append(0)
            radar_rows.append({"name": row["Company"], "values": vals})

        if len(radar_rows) >= 2:
            radar_fig = go.Figure()
            for rd in radar_rows:
                radar_fig.add_trace(go.Scatterpolar(
                    r=rd["values"] + [rd["values"][0]],
                    theta=radar_metrics + [radar_metrics[0]],
                    name=rd["name"][:25],
                    fill="toself",
                    opacity=0.5,
                ))
            radar_fig.update_layout(
                polar={"radialaxis": {"visible": True}},
                title="Ratio Comparison — Radar Chart",
                height=420,
                margin={"t": 60, "b": 30, "l": 30, "r": 30},
            )
            st.plotly_chart(radar_fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚠️ **Disclaimer:** This dashboard is for educational and informational purposes only.  "
    "It does not constitute financial advice.  All valuations are model-based estimates — "
    "actual intrinsic value depends on many factors not captured here.  "
    "Always consult a qualified financial adviser before making investment decisions."
)
