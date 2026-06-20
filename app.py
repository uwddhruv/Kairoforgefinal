"""
app.py — KAIROFORGE
Institutional-Grade Equity Research Terminal for Indian Markets (NSE).

Navigation (sidebar):
  📊 Screener       — Ranked stock screener with live Value Opportunity Scores
  📈 Stock Analysis — Graham Number · 3-Stage DCF · Ratios · Sensitivity · Price Target
"""

import html as _html
import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from stocks           import STOCKS, SORTED_LABELS, INDUSTRY_PEERS, SECTOR_PEERS, TICKER_TO_NAME
from data_loader      import fetch_stock_data, fetch_price_history, fetch_news, safe_get
from valuation_models import (
    calculate_graham, calculate_ratios,
    estimate_wacc, calculate_dcf, run_sensitivity,
)
from screener  import run_screener, generate_signal, score_stock as _score_stock
from portfolio import screener_to_csv
from nl_search import parse_nl_query, apply_nl_filters


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KAIROFORGE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# CSS — dark financial terminal theme (safe, visible overrides only)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: box-shadow .2s, transform .15s !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(59,130,246,0.5) !important;
    transform: translateY(-1px) !important;
}

/* ── Metric cards ─────────────────────────────────────────── */
[data-testid="metric-container"] {
    border: 1px solid rgba(59,130,246,0.25) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important;
    color: #fff !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}

/* ── Divider ──────────────────────────────────────────────── */
hr { border-color: rgba(59,130,246,0.2) !important; }

/* ── Glass card (used for hero + info boxes) ──────────────── */
.glass-card {
    background: rgba(30,41,59,0.6);
    border: 1px solid rgba(59,130,246,0.22);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 12px;
    color: #e2e8f0;
}

/* ── Hero card ────────────────────────────────────────────── */
.hero-card {
    background: rgba(29,78,216,0.12);
    border: 1px solid rgba(59,130,246,0.35);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    color: #e2e8f0;
}

/* ── Screener table ───────────────────────────────────────── */
.scr-wrap { overflow-x:auto; border-radius:12px; border:1px solid rgba(59,130,246,0.18); margin-top:8px; }
.scr-table { width:100%; border-collapse:collapse; font-size:.875rem; }
.scr-table thead tr { background:rgba(15,23,42,0.95); }
.scr-table th {
    padding:10px 14px; text-align:left; color:#94a3b8;
    text-transform:uppercase; font-size:.7rem; letter-spacing:.07em; font-weight:600;
    border-bottom:1px solid rgba(59,130,246,0.15); white-space:nowrap;
}
.scr-table td { padding:9px 14px; border-bottom:1px solid rgba(59,130,246,0.07); color:#cbd5e1; white-space:nowrap; }
.scr-table tbody tr:hover { background:rgba(59,130,246,0.08) !important; }

/* signal badges */
.badge { padding:3px 10px; border-radius:20px; font-size:.72rem; font-weight:700; display:inline-block; }
.b-sb  { background:rgba(22,163,74,.22);   color:#4ade80; border:1px solid #16a34a; }
.b-b   { background:rgba(74,222,128,.14);  color:#86efac; border:1px solid rgba(74,222,128,.5); }
.b-h   { background:rgba(202,138,4,.2);    color:#fbbf24; border:1px solid #ca8a04; }
.b-av  { background:rgba(220,38,38,.2);    color:#f87171; border:1px solid #dc2626; }

/* ── KPI tiles ────────────────────────────────────────────── */
.kpi-row { display:flex; gap:12px; flex-wrap:wrap; margin:12px 0; }
.kpi-tile {
    flex:1; min-width:140px;
    background: rgba(30,41,59,0.55);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 12px; padding:14px 16px;
}
.kpi-label { color:#94a3b8; font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; font-weight:600; margin-bottom:6px; }
.kpi-value { font-size:1.25rem; font-weight:700; }
.kpi-help  { color:#475569; font-size:.7rem; margin-top:4px; }

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:rgba(15,23,42,.4); }
::-webkit-scrollbar-thumb { background:rgba(59,130,246,.5); border-radius:4px; }

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
if "screener_df"     not in st.session_state: st.session_state.screener_df     = None
if "analysis_ticker" not in st.session_state: st.session_state.analysis_ticker = None
if "nl_results"      not in st.session_state: st.session_state.nl_results      = None
if "nl_query"        not in st.session_state: st.session_state.nl_query        = None
if "nl_explanation"  not in st.session_state: st.session_state.nl_explanation  = None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — logo + navigation
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("logo.png", width=240)
    st.markdown("<hr style='border:1px solid rgba(59,130,246,0.2);margin:12px 0'>", unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["📊  Screener", "📈  Stock Analysis"],
        label_visibility="collapsed",
        key="page",
    )

    st.markdown("<hr style='border:1px solid rgba(59,130,246,0.1);margin:12px 0'>", unsafe_allow_html=True)
    st.caption("Data: Yahoo Finance · yfinance")
    st.caption(f"Universe: {len(STOCKS)} NSE stocks")

    # Quick-load indicator
    if st.session_state.analysis_ticker:
        st.markdown(
            f"<div style='background:rgba(29,78,216,.15);border:1px solid rgba(59,130,246,.3);"
            f"border-radius:8px;padding:8px 12px;font-size:.8rem;color:#93c5fd;margin-top:8px'>"
            f"📈 Loaded: <strong>{st.session_state.analysis_ticker}</strong></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='color:#334155;font-size:.72rem;text-align:center'>"
        "KAIROFORGE · Equity Research Terminal</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(v, prefix="₹", dec=2):
    return f"{prefix}{v:,.{dec}f}" if v is not None else "N/A"

def _pct(v, dec=1):
    return f"{v:+.{dec}f}%" if v is not None else "N/A"

# Plotly base layout for dark charts
_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(8,13,26,0)",
    plot_bgcolor="rgba(8,13,26,0)",
    font=dict(family="Inter, sans-serif", color="#94a3b8"),
    margin=dict(t=55, b=25, l=15, r=15),
)


# ─────────────────────────────────────────────────────────────────────────────
# CHART FACTORIES  (all dark-themed)
# ─────────────────────────────────────────────────────────────────────────────

def make_gauge(current, target, title=""):
    is_under  = current < target
    bar_color = "#22c55e" if is_under else "#ef4444"
    max_r     = max(current, target) * 1.65
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        number={"prefix": "₹", "valueformat": ",.0f", "font": {"size": 26, "color": "#f1f5f9"}},
        delta={"reference": target, "prefix": "₹", "valueformat": ",.0f",
               "increasing": {"color": "#ef4444"}, "decreasing": {"color": "#22c55e"}},
        title={"text": title, "font": {"size": 12, "color": "#64748b"}},
        gauge={
            "axis": {"range": [0, max_r], "tickprefix": "₹", "tickformat": ",", "tickcolor": "#334155"},
            "bar":  {"color": bar_color, "thickness": 0.26},
            "bgcolor": "rgba(15,23,42,0.4)",
            "steps": [
                {"range": [0, target],  "color": "rgba(34,197,94,.1)"},
                {"range": [target, max_r], "color": "rgba(239,68,68,.1)"},
            ],
            "threshold": {"line": {"color": "#3b82f6", "width": 3},
                          "value": target, "thickness": 0.85},
        },
    ))
    fig.update_layout(height=255, **_DARK_LAYOUT)
    return fig


def make_bar_comp(labels, values, colors, title=""):
    fig = go.Figure()
    for lbl, val, col in zip(labels, values, colors):
        fig.add_trace(go.Bar(
            name=lbl, x=[lbl], y=[val],
            marker_color=col, marker_line_color="rgba(0,0,0,0)",
            text=[f"₹{val:,.0f}"], textposition="outside",
            textfont={"color": "#e2e8f0"},
        ))
    fig.update_layout(
        title=dict(text=title, font={"size": 13}),
        showlegend=False,
        yaxis={"tickprefix": "₹", "tickformat": ",", "gridcolor": "rgba(59,130,246,0.08)"},
        height=295, **_DARK_LAYOUT,
    )
    return fig


def make_hist_chart(hist, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        name="Close", line={"color": "#3b82f6", "width": 1.8},
        fill="tozeroy", fillcolor="rgba(59,130,246,0.07)",
    ))
    if len(hist) >= 50:
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(50).mean(),
            name="50D SMA", line={"color": "#f59e0b", "width": 1.2, "dash": "dot"}))
    if len(hist) >= 200:
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(200).mean(),
            name="200D SMA", line={"color": "#8b5cf6", "width": 1.2, "dash": "dash"}))
    fig.update_layout(
        title=dict(text=f"{ticker} — 5-Year Price History", font={"size": 13}),
        yaxis={"tickprefix": "₹", "tickformat": ",", "gridcolor": "rgba(59,130,246,0.08)"},
        legend={"orientation": "h", "y": 1.08},
        height=355, hovermode="x unified", **_DARK_LAYOUT,
    )
    return fig


def make_dcf_waterfall(result):
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["relative","relative","relative","total"],
        x=["Stage 1\nHigh Growth","Stage 2\nTransition","Terminal\nValue","Intrinsic\nValue"],
        y=[result["pv_stage1"], result["pv_stage2"], result["pv_terminal"], result["intrinsic_value"]],
        texttemplate="₹%{y:,.0f}", textposition="outside",
        textfont={"color": "#e2e8f0"},
        connector={"line": {"color": "rgba(59,130,246,0.3)"}},
        increasing={"marker": {"color": "#22c55e"}},
        totals={"marker": {"color": "#3b82f6"}},
    ))
    fig.update_layout(
        title=dict(text="DCF Components — Present Value Breakdown (₹/Share)", font={"size": 13}),
        yaxis={"tickprefix": "₹", "tickformat": ",", "gridcolor": "rgba(59,130,246,0.08)"},
        height=315, showlegend=False, **_DARK_LAYOUT,
    )
    return fig


def make_sensitivity_heatmap(df, current_price):
    z  = df.values.astype(float)
    fig = go.Figure(go.Heatmap(
        z=z, x=list(df.columns), y=list(df.index),
        colorscale=[[0,"#7f1d1d"],[0.35,"#dc2626"],[0.5,"#1e3a5f"],[0.65,"#16a34a"],[1,"#166534"]],
        zmid=current_price,
        text=[[f"₹{v:,.0f}" if not math.isnan(v) else "—" for v in row] for row in z],
        texttemplate="%{text}", textfont={"size": 11, "color": "#f1f5f9"},
        colorbar={"title": "Fair Value (₹)", "tickprefix": "₹", "tickformat": ",",
                  "tickfont": {"color": "#94a3b8"}},
    ))
    fig.update_layout(
        title=dict(
            text=f"DCF Sensitivity  |  Current Price ₹{current_price:,.0f}  |  <span style='color:#22c55e'>Green = undervalued</span>",
            font={"size": 13}
        ),
        xaxis_title="Terminal Growth Rate", yaxis_title="WACC",
        xaxis={"tickfont": {"color": "#94a3b8"}},
        yaxis={"tickfont": {"color": "#94a3b8"}},
        height=395, **{**_DARK_LAYOUT, "margin": dict(t=60, b=45, l=80, r=20)},
    )
    return fig


def score_donut(score):
    color = "#16a34a" if score >= 70 else "#3b82f6" if score >= 50 else "#ca8a04" if score >= 30 else "#dc2626"
    fig = go.Figure(go.Pie(
        values=[score, 100 - score], hole=0.72,
        marker_colors=[color, "rgba(30,41,59,0.6)"],
        textinfo="none", hoverinfo="skip",
    ))
    fig.add_annotation(text=f"<b>{score}</b>", x=0.5, y=0.5,
                       font={"size": 30, "color": color}, showarrow=False)
    fig.update_layout(showlegend=False, height=175,
                      **{**_DARK_LAYOUT, "margin": dict(t=8, b=8, l=8, r=8)})
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT ANALYSIS  (keyword-based, no external API)
# ─────────────────────────────────────────────────────────────────────────────

_POS_WORDS = {
    "profit","growth","record","surge","strong","beat","rise","gain","rally",
    "upgrade","outperform","buy","positive","expand","increase","boost","high",
    "milestone","robust","recovery","optimistic","advance","jumped","soared",
    "breakout","dividend","award","win","agreement","acquisition","launch",
    "delivered","exceeded","improved","raised","bullish","opportunity",
}
_NEG_WORDS = {
    "loss","decline","miss","weak","fall","drop","downgrade","underperform",
    "sell","negative","cut","reduce","decrease","slump","warn","concern",
    "risk","debt","lawsuit","probe","investigation","fine","penalty","fraud",
    "crash","plunge","tumble","bearish","disappoint","challenge","struggle",
    "default","downside","volatile","uncertainty","slow","miss","halt",
}

def _score_headline(title: str) -> int:
    """Return +1 (positive), -1 (negative), or 0 (neutral) for a headline."""
    words = set(title.lower().split())
    pos = len(words & _POS_WORDS)
    neg = len(words & _NEG_WORDS)
    if pos > neg:   return 1
    if neg > pos:   return -1
    return 0


def _time_ago(ts) -> str:
    """Convert a Unix timestamp or ISO string to a human-readable 'X ago' label."""
    import time as _time
    try:
        if ts is None:
            return ""
        if isinstance(ts, str):
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            epoch = dt.timestamp()
        else:
            epoch = float(ts)
        diff = int(_time.time() - epoch)
        if diff < 3600:   return f"{diff//60}m ago"
        if diff < 86400:  return f"{diff//3600}h ago"
        return f"{diff//86400}d ago"
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# HTML REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_html_report(
    ticker: str,
    name: str,
    sector: str,
    price,
    signal: str,
    score: int,
    explanation: str,
    graham,
    eps,
    bvps,
    ratios: dict,
    dcf_res: dict | None,
    mkt_cap,
    beta,
    wacc: float,
) -> str:
    """Return a self-contained HTML equity research report as a string."""
    from datetime import date as _date

    def _v(val, fmt="₹{:,.2f}", fallback="N/A"):
        if val is None:
            return fallback
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return fallback
            return fmt.format(f)
        except (TypeError, ValueError):
            return str(val)

    today     = _date.today().strftime("%d %B %Y")
    sig_color = {"STRONG BUY":"#16a34a","BUY":"#059669","HOLD":"#d97706","AVOID":"#dc2626"}.get(signal,"#6b7280")
    price_s   = _v(price, "₹{:,.2f}")
    graham_s  = _v(graham, "₹{:,.2f}")
    mos_s     = f"{((graham - price)/graham*100):+.1f}%" if (graham and price and graham > 0) else "N/A"
    # Escape external strings used inside HTML
    name   = _html.escape(str(name))
    ticker = _html.escape(str(ticker))
    sector = _html.escape(str(sector))
    cap_s     = "N/A"
    if mkt_cap:
        if mkt_cap >= 1e12:   cap_s = f"₹{mkt_cap/1e12:.2f}T"
        elif mkt_cap >= 1e9:  cap_s = f"₹{mkt_cap/1e9:.1f}B"
        else:                 cap_s = f"₹{mkt_cap/1e6:.0f}M"

    # Ratios rows  — keys must match calculate_ratios() return dict
    ratio_rows = ""
    ratio_defs = [
        ("P/E (Trailing)",         "P/E (Trailing)",     "{:.1f}×"),
        ("P/E (Forward)",          "P/E (Forward)",      "{:.1f}×"),
        ("P/B",                    "P/B",                "{:.2f}×"),
        ("ROE (%)",                "ROE (%)",            "{:.1f}%"),
        ("ROIC (%)",               "ROIC (%)",           "{:.1f}%"),
        ("Debt / Equity",          "Debt / Equity",      "{:.2f}×"),
        ("EPS Growth (Fwd vs TTM)","EPS Growth (%)",     "{:+.1f}%"),
        ("Dividend Yield (%)",     "Dividend Yield (%)", "{:.2f}%"),
    ]
    for label, key, fmt in ratio_defs:
        val = ratios.get(key)
        disp = _v(val, fmt) if val is not None else "N/A"
        ratio_rows += f"<tr><td>{label}</td><td><strong>{disp}</strong></td></tr>"

    # DCF section
    dcf_html = ""
    if dcf_res:
        iv  = dcf_res.get("intrinsic_value")
        pv1 = dcf_res.get("pv_stage1")
        pv2 = dcf_res.get("pv_stage2")
        pvt = dcf_res.get("pv_terminal")
        if iv and price:
            disc = (iv - price) / iv * 100
            verdict = f"{'Undervalued' if price < iv else 'Overvalued'} by {abs(disc):.1f}%"
        else:
            verdict = "N/A"
        dcf_html = f"""
        <h2>3-Stage DCF Valuation</h2>
        <table class="rtable">
          <tr><td>DCF Intrinsic Value</td><td><strong>{_v(iv, "₹{{:,.0f}}")}</strong></td></tr>
          <tr><td>Market Price</td><td><strong>{price_s}</strong></td></tr>
          <tr><td>Verdict</td><td><strong style="color:{sig_color}">{verdict}</strong></td></tr>
          <tr><td>PV Stage 1 (High Growth)</td><td>{_v(pv1, "₹{{:,.0f}}")}</td></tr>
          <tr><td>PV Stage 2 (Transition)</td><td>{_v(pv2, "₹{{:,.0f}}")}</td></tr>
          <tr><td>PV Terminal Value</td><td>{_v(pvt, "₹{{:,.0f}}")}</td></tr>
        </table>"""

    # Explanation — strip markdown bold markers, then escape for safe HTML embedding
    expl_clean = _html.escape(explanation.replace("**", "")).replace("  \n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KAIROFORGE — {name} Research Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
          color: #1e293b; background: #f8fafc; padding: 32px; }}
  .page {{ max-width: 820px; margin: 0 auto; background: #fff;
           border-radius: 8px; padding: 40px 48px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ border-bottom: 3px solid #1d4ed8; padding-bottom: 20px; margin-bottom: 28px; }}
  .brand {{ font-size: 11px; font-weight: 700; color: #1d4ed8;
            letter-spacing: .12em; text-transform: uppercase; margin-bottom: 8px; }}
  .co-name {{ font-size: 26px; font-weight: 800; color: #0f172a; line-height: 1.15; }}
  .co-sub {{ color: #64748b; font-size: 13px; margin-top: 6px; }}
  .signal-badge {{ display: inline-block; padding: 4px 14px; border-radius: 20px;
                   font-weight: 700; font-size: 12px; color: #fff;
                   background: {sig_color}; margin-top: 10px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr);
               gap: 14px; margin: 24px 0; }}
  .kpi-box {{ background: #f1f5f9; border-radius: 8px; padding: 14px 16px; }}
  .kpi-label {{ font-size: 10px; font-weight: 700; color: #64748b;
                text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; }}
  .kpi-val {{ font-size: 18px; font-weight: 800; color: #0f172a; }}
  h2 {{ font-size: 14px; font-weight: 700; color: #1d4ed8;
        text-transform: uppercase; letter-spacing: .06em;
        border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;
        margin: 28px 0 14px; }}
  .rtable {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  .rtable td {{ padding: 7px 10px; border-bottom: 1px solid #f1f5f9; }}
  .rtable tr:nth-child(even) td {{ background: #f8fafc; }}
  .rtable td:first-child {{ color: #475569; width: 55%; }}
  .explanation {{ background: #f8fafc; border-left: 4px solid #1d4ed8;
                  border-radius: 0 8px 8px 0; padding: 14px 18px;
                  line-height: 1.65; color: #334155; font-size: 12.5px; margin: 14px 0; }}
  .score-bar-bg {{ background: #e2e8f0; border-radius: 6px; height: 10px; margin-top: 6px; overflow:hidden; }}
  .score-bar {{ height: 10px; border-radius: 6px; background: {sig_color}; width: {score}%; }}
  .footer {{ margin-top: 36px; padding-top: 16px; border-top: 1px solid #e2e8f0;
             font-size: 10.5px; color: #94a3b8; text-align: center; line-height: 1.7; }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .page {{ box-shadow: none; padding: 20px; }}
  }}
</style>
</head>
<body>
<div class="page">

  <div class="header">
    <div class="brand">KAIROFORGE · Equity Research Terminal</div>
    <div class="co-name">{name}</div>
    <div class="co-sub">
      {sector or "NSE"} &nbsp;·&nbsp; <strong>{ticker}</strong>
      &nbsp;·&nbsp; Report date: {today}
    </div>
    <div class="signal-badge">{signal}</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-box">
      <div class="kpi-label">Market Price</div>
      <div class="kpi-val">{price_s}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">Graham Number</div>
      <div class="kpi-val">{graham_s}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">Margin of Safety</div>
      <div class="kpi-val">{mos_s}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">Market Cap</div>
      <div class="kpi-val">{cap_s}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">Beta</div>
      <div class="kpi-val">{_v(beta, "{:.2f}")}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">Est. WACC</div>
      <div class="kpi-val">{wacc*100:.1f}%</div>
    </div>
  </div>

  <h2>Value Opportunity Score</h2>
  <p style="font-size:28px;font-weight:800;color:{sig_color}">{score}<span style="font-size:14px;color:#64748b;font-weight:500"> / 100</span></p>
  <div class="score-bar-bg"><div class="score-bar"></div></div>

  <h2>Investment Rationale</h2>
  <div class="explanation">{expl_clean}</div>

  <h2>Graham Number Analysis</h2>
  <table class="rtable">
    <tr><td>EPS (Trailing / Adjusted)</td><td><strong>{_v(eps, "₹{{:,.2f}}")}</strong></td></tr>
    <tr><td>Book Value per Share</td><td><strong>{_v(bvps, "₹{{:,.2f}}")}</strong></td></tr>
    <tr><td>Graham Number (√22.5 × EPS × BVPS)</td><td><strong>{graham_s}</strong></td></tr>
    <tr><td>Current Price</td><td><strong>{price_s}</strong></td></tr>
    <tr><td>Margin of Safety</td><td><strong style="color:{sig_color}">{mos_s}</strong></td></tr>
  </table>

  <h2>Key Ratios</h2>
  <table class="rtable">{ratio_rows}</table>

  {dcf_html}

  <div class="footer">
    <strong>KAIROFORGE — Equity Research Terminal</strong><br>
    Created by Dhruv Vaniawala · uwddhruv@gmail.com<br><br>
    ⚠️ For educational purposes only — not financial advice.
    All valuations are model-based estimates. Consult a qualified financial adviser before investing.<br>
    Data sourced from Yahoo Finance. Accuracy not guaranteed.
  </div>

</div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM HTML COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def hero_card(name, ticker, sector, price, signal, emoji, score, explanation):
    """Render a stock hero card with name, price, signal, and rationale."""
    sig_colors = {"STRONG BUY": "#22c55e", "BUY": "#4ade80",
                  "HOLD": "#fbbf24", "AVOID": "#ef4444"}
    sig_bg = {"STRONG BUY": "rgba(22,163,74,.18)", "BUY": "rgba(74,222,128,.12)",
              "HOLD": "rgba(202,138,4,.18)", "AVOID": "rgba(220,38,38,.18)"}
    col = sig_colors.get(signal, "#94a3b8")
    bg  = sig_bg.get(signal, "rgba(59,130,246,.1)")
    p   = f"₹{price:,.2f}" if price else "N/A"
    # Escape external strings before embedding in HTML
    s_name    = _html.escape(str(name))
    s_ticker  = _html.escape(str(ticker))
    s_sector  = _html.escape(str(sector))
    s_expl    = _html.escape(str(explanation))
    st.markdown(f"""
<div class="hero-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px">
    <div>
      <div style="color:#475569;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px">{s_sector}</div>
      <div style="font-size:1.75rem;font-weight:800;color:#f1f5f9;line-height:1.1">{s_name}</div>
      <div style="color:#475569;font-size:.85rem;margin-top:5px">NSE &nbsp;·&nbsp; <strong style="color:#93c5fd">{s_ticker}</strong></div>
    </div>
    <div style="text-align:right">
      <div style="font-size:2.1rem;font-weight:800;color:#f1f5f9;font-variant-numeric:tabular-nums">{p}</div>
      <div style="margin-top:10px">
        <span style="background:{bg};color:{col};border:1px solid {col};padding:5px 16px;border-radius:20px;font-weight:700;font-size:.85rem">{emoji} {signal}</span>
      </div>
      <div style="color:#475569;font-size:.78rem;margin-top:8px">Value Score &nbsp;<strong style="color:{col}">{score}/100</strong></div>
    </div>
  </div>
  <div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(59,130,246,0.12);color:#64748b;font-size:.82rem;line-height:1.5">{s_expl[:200]}{"…" if len(s_expl)>200 else ""}</div>
</div>
""", unsafe_allow_html=True)


def kpi_tiles(items: list[dict]):
    """Render a row of KPI tiles.  items = [{'label','value','help','color'}]"""
    cols_html = "".join(f"""
<div class="kpi-tile">
  <div class="kpi-label">{it['label']}</div>
  <div class="kpi-value" style="color:{it.get('color','#f1f5f9')}">{it['value']}</div>
  <div class="kpi-help">{it.get('help','')}</div>
</div>""" for it in items)
    st.markdown(f'<div class="kpi-row">{cols_html}</div>', unsafe_allow_html=True)


def screener_table(df: pd.DataFrame):
    """Render a color-coded, terminal-style screener results table."""
    if df.empty:
        st.info("No stocks match the current filters.")
        return

    sig_badge = {
        "STRONG BUY": '<span class="badge b-sb">STRONG BUY</span>',
        "BUY":        '<span class="badge b-b">BUY</span>',
        "HOLD":       '<span class="badge b-h">HOLD</span>',
        "AVOID":      '<span class="badge b-av">AVOID</span>',
    }
    border_col = {
        "STRONG BUY": "#16a34a", "BUY": "#4ade80", "HOLD": "#ca8a04", "AVOID": "#dc2626"
    }

    def _cell(col, val, signal):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return '<td style="color:#334155">—</td>'
        if col == "Signal":
            return f"<td>{sig_badge.get(val,'')}</td>"
        if col == "Rank":
            return f'<td style="color:#475569;font-weight:600">#{int(val)}</td>'
        if col in ("Price (₹)", "Graham No."):
            return f'<td style="font-weight:600;color:#e2e8f0">₹{float(val):,.0f}</td>'
        if col == "Score":
            clr = border_col.get(signal, "#94a3b8")
            return f'<td style="color:{clr};font-weight:700">{int(val)}</td>'
        if col == "MoS %":
            v = float(val)
            c = "#22c55e" if v > 0 else "#ef4444"
            return f'<td style="color:{c};font-weight:600">{v:+.1f}%</td>'
        if col == "ROE (%)":
            v = float(val)
            c = "#22c55e" if v > 15 else "#fbbf24" if v > 0 else "#ef4444"
            return f'<td style="color:{c}">{v:.1f}%</td>'
        if col == "P/E":
            v = float(val)
            c = "#22c55e" if v <= 15 else "#fbbf24" if v <= 30 else "#ef4444"
            return f'<td style="color:{c}">{v:.1f}×</td>'
        return f"<td>{val}</td>"

    display_cols = ["Rank","Company","Ticker","Price (₹)","Graham No.",
                    "MoS %","ROE (%)","P/E","D/E","Score","Signal"]
    visible = [c for c in display_cols if c in df.columns]

    header = "".join(f"<th>{c}</th>" for c in visible)
    rows   = ""
    for _, row in df.iterrows():
        sig = row.get("Signal","")
        bg  = {"STRONG BUY":"rgba(22,163,74,.06)","BUY":"rgba(74,222,128,.04)",
               "HOLD":"rgba(202,138,4,.05)","AVOID":"rgba(220,38,38,.05)"}.get(sig,"")
        bl  = border_col.get(sig,"transparent")
        cells = "".join(_cell(c, row.get(c), sig) for c in visible)
        rows += f'<tr style="background:{bg};border-left:3px solid {bl}">{cells}</tr>'

    st.markdown(
        f'<div class="scr-wrap"><table class="scr-table"><thead><tr>{header}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER  (appears on all pages)
# ─────────────────────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<span style='color:#475569;font-size:.9rem'>{subtitle}</span>",
                    unsafe_allow_html=True)
    st.divider()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: SCREENER
# ═══════════════════════════════════════════════════════════════════════════
def render_screener():

    # ── NL SEARCH RESULTS STATE ───────────────────────────────────────────
    if st.session_state.get("nl_results") is not None:
        _render_landing()
        return

    # ── LANDING STATE (no full screener ran yet)
    if st.session_state.screener_df is None:
        _render_landing()
        return

    # ── ACTIVE SCREENER ───────────────────────────────────────────────────
    _render_screener_results()


def _render_landing():
    """Full-page landing experience shown before the screener is run."""

    # ── Hero section ──────────────────────────────────────────────────────
    st.markdown(f"""
<div style="
  background: linear-gradient(135deg, rgba(13,18,36,0.98) 0%, rgba(15,27,58,0.95) 50%, rgba(10,15,30,0.98) 100%);
  border: 1px solid rgba(59,130,246,0.25);
  border-radius: 20px;
  padding: 52px 48px 44px;
  margin-bottom: 28px;
  position: relative;
  overflow: hidden;
">
  <!-- glow blobs -->
  <div style="position:absolute;top:-60px;right:-60px;width:280px;height:280px;
    background:radial-gradient(circle,rgba(59,130,246,0.18) 0%,transparent 70%);pointer-events:none"></div>
  <div style="position:absolute;bottom:-80px;left:-40px;width:240px;height:240px;
    background:radial-gradient(circle,rgba(139,92,246,0.12) 0%,transparent 70%);pointer-events:none"></div>

  <!-- brand line -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:22px">
    <div style="width:3px;height:32px;background:linear-gradient(180deg,#3b82f6,#8b5cf6);border-radius:2px"></div>
    <span style="font-size:.75rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
      color:#3b82f6;font-family:'Inter',sans-serif">KAIROFORGE · EQUITY RESEARCH TERMINAL</span>
  </div>

  <!-- headline -->
  <h1 style="font-size:2.6rem;font-weight:900;color:#f8fafc;line-height:1.15;margin:0 0 16px;
    font-family:'Inter',sans-serif;letter-spacing:-0.02em">
    Find undervalued Indian stocks<br>
    <span style="background:linear-gradient(90deg,#3b82f6,#8b5cf6,#06b6d4);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
      before the market does.
    </span>
  </h1>

  <!-- sub -->
  <p style="color:#64748b;font-size:1.05rem;line-height:1.6;margin:0 0 36px;max-width:600px">
    Institutional-grade screening across <strong style="color:#93c5fd">{len(STOCKS)} Nifty stocks</strong> —
    Graham Number, 3-stage DCF, sensitivity analysis and news sentiment, all in one terminal.
  </p>

  <!-- feature pills -->
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:36px">
    {"".join(f'''<span style="background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.25);
      border-radius:20px;padding:5px 14px;font-size:.78rem;color:#93c5fd;font-weight:600">{t}</span>'''
      for t in ["Graham Number","3-Stage DCF","Sensitivity Heatmap","News & Sentiment",
                "Peer Comparison","Price Targets","HTML Reports","Live NSE Data"])}
  </div>

  <!-- CTA -->
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
    <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);border-radius:10px;
      padding:13px 28px;font-weight:700;font-size:1rem;color:#fff;display:inline-block;
      box-shadow:0 6px 24px rgba(59,130,246,0.4)">
      🚀 &nbsp;Run the screener below to begin
    </div>
    <span style="color:#334155;font-size:.85rem">~20 seconds · live Yahoo Finance data</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Stats row ─────────────────────────────────────────────────────────
    st.markdown("""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px">

  <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(59,130,246,0.18);
    border-radius:14px;padding:20px 22px;text-align:center">
    <div style="font-size:2rem;font-weight:800;color:#3b82f6;font-variant-numeric:tabular-nums">120+</div>
    <div style="color:#475569;font-size:.78rem;font-weight:600;text-transform:uppercase;
      letter-spacing:.07em;margin-top:4px">NSE Stocks</div>
    <div style="color:#1e3a5f;font-size:.7rem;margin-top:3px">Nifty universe</div>
  </div>

  <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(139,92,246,0.2);
    border-radius:14px;padding:20px 22px;text-align:center">
    <div style="font-size:2rem;font-weight:800;color:#8b5cf6">4</div>
    <div style="color:#475569;font-size:.78rem;font-weight:600;text-transform:uppercase;
      letter-spacing:.07em;margin-top:4px">Scoring Factors</div>
    <div style="color:#1e3a5f;font-size:.7rem;margin-top:3px">Graham · ROE · P/E · D/E</div>
  </div>

  <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(6,182,212,0.2);
    border-radius:14px;padding:20px 22px;text-align:center">
    <div style="font-size:2rem;font-weight:800;color:#06b6d4">0-100</div>
    <div style="color:#475569;font-size:.78rem;font-weight:600;text-transform:uppercase;
      letter-spacing:.07em;margin-top:4px">Value Score</div>
    <div style="color:#1e3a5f;font-size:.7rem;margin-top:3px">Proprietary ranking</div>
  </div>

  <div style="background:rgba(15,23,42,0.7);border:1px solid rgba(34,197,94,0.2);
    border-radius:14px;padding:20px 22px;text-align:center">
    <div style="font-size:2rem;font-weight:800;color:#22c55e">3</div>
    <div style="color:#475569;font-size:.78rem;font-weight:600;text-transform:uppercase;
      letter-spacing:.07em;margin-top:4px">DCF Stages</div>
    <div style="color:#1e3a5f;font-size:.7rem;margin-top:3px">Growth · Transition · Terminal</div>
  </div>

</div>
""", unsafe_allow_html=True)

    # ── Natural Language Search ─────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(16,185,129,0.08),rgba(59,130,246,0.06));
  border:1px solid rgba(16,185,129,0.2);border-radius:16px;padding:24px 28px;margin-bottom:28px">
  <div style="font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
    color:#334155;margin-bottom:12px">🔍 NATURAL LANGUAGE SEARCH</div>
  <div style="color:#94a3b8;font-size:.8rem;margin-bottom:14px">
    Type what you want in plain English — e.g. "undervalued healthcare stocks with low PE and high ROCE"
  </div>
</div>
""", unsafe_allow_html=True)

    nl_query = st.text_input(
        "Search stocks",
        placeholder="undervalued healthcare stocks with low pe and high roce...",
        label_visibility="collapsed",
    )

    nl_search_btn = st.button("🔎  Search", type="secondary", width='content')

    if nl_search_btn and nl_query:
        with st.spinner("Searching with natural language query..."):
            criteria = parse_nl_query(nl_query)
            # Run screener on the narrowed ticker pool
            narrowed_stocks = {k: v for k, v in STOCKS.items() if v in criteria["tickers"]}
            if not narrowed_stocks:
                st.warning("No stocks matched the sector / industry filter. Try a broader query.")
            else:
                pb = st.progress(0.0)
                stx = st.empty()
                df = run_screener(narrowed_stocks, progress_bar=pb, status_text=stx)
                pb.empty(); stx.empty()
                if not df.empty:
                    # Apply NL metric filters
                    stock_list = df.to_dict("records")
                    filtered = apply_nl_filters(stock_list, criteria)
                    if filtered:
                        st.session_state.nl_results = filtered
                        st.session_state.nl_query = nl_query
                        st.session_state.nl_explanation = criteria["explanation"]
                        st.rerun()
                    else:
                        st.info(f"No stocks passed all filters for: {criteria['explanation']}")
                else:
                    st.error("Failed to fetch stock data. Check your connection.")

    # Show NL results if available
    if st.session_state.get("nl_results") is not None:
        st.markdown(f"""
<div style="background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.2);
  border-radius:14px;padding:18px 22px;margin-bottom:18px">
  <div style="font-weight:700;color:#e2e8f0;font-size:.95rem;margin-bottom:4px">
    🔍 Results for: {st.session_state.nl_query}
  </div>
  <div style="color:#94a3b8;font-size:.78rem">{st.session_state.nl_explanation}</div>
</div>
""", unsafe_allow_html=True)

        nl_df = pd.DataFrame(st.session_state.nl_results)
        cols = ["Ticker", "Company", "Score", "Signal", "P/E", "D/E", "ROE (%)", "Beta", "MoS %", "Price (₹)"]
        display_cols = {
            "Ticker": "TICKER",
            "Company": "COMPANY",
            "Score": "SCORE",
            "Signal": "SIGNAL",
            "P/E": "P/E",
            "D/E": "D/E",
            "ROE (%)": "ROE %",
            "Beta": "BETA",
            "MoS %": "MoS %",
            "Price (₹)": "PRICE",
        }
        st.dataframe(
            nl_df[cols].rename(columns=display_cols),
            width='stretch',
            hide_index=True,
            key="nl_table",
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "SCORE": st.column_config.NumberColumn(format="%.1f"),
                "P/E": st.column_config.NumberColumn(format="%.1f"),
                "D/E": st.column_config.NumberColumn(format="%.2f"),
                "ROE %": st.column_config.NumberColumn(format="%.1f"),
                "BETA": st.column_config.NumberColumn(format="%.2f"),
                "MoS %": st.column_config.NumberColumn(format="%.1f"),
                "PRICE": st.column_config.NumberColumn(format="₹%.2f"),
            },
        )

        # Row selection → navigate to stock analysis
        selected = st.session_state.get("nl_table")
        if selected and selected.get("selection", {}).get("rows", []):
            idx = selected["selection"]["rows"][0]
            ticker = nl_df.iloc[idx]["Ticker"]
            st.session_state.analysis_ticker = ticker
            st.session_state.page = "📈  Stock Analysis"
            st.rerun()

        if st.button("Clear Search Results", type="tertiary"):
            st.session_state.nl_results = None
            st.session_state.nl_query = None
            st.session_state.nl_explanation = None
            st.rerun()

    # ── Feature cards ─────────────────────────────────────────────────────
    st.markdown("<div style='font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;"
                "color:#334155;margin-bottom:16px'>WHAT YOU GET</div>",
                unsafe_allow_html=True)

    _feature_cards = [
        ("📊", "Value Screener", "Rank all 120+ stocks by Value Opportunity Score. Filter by signal strength and data quality. Export to CSV.",
         "rgba(29,78,216,0.08)", "rgba(59,130,246,0.2)"),
        ("💹", "Deep Valuation", "Graham Number, 3-stage DCF with custom growth sliders, WACC auto-estimation, and sensitivity heatmap.",
         "rgba(139,92,246,0.07)", "rgba(139,92,246,0.2)"),
        ("🎯", "Price Targets", "Bull / Base / Bear DCF scenarios with visual range bar, upside %, and scenario breakdown table.",
         "rgba(6,182,212,0.06)", "rgba(6,182,212,0.18)"),
        ("📰", "News & Sentiment", "Live Yahoo Finance headlines with keyword-based sentiment scoring. Bullish / Bearish / Neutral classification.",
         "rgba(245,158,11,0.06)", "rgba(245,158,11,0.18)"),
        ("🔄", "Peer Comparison", "Side-by-side P/E, P/B, ROE, D/E and Value Score vs sector peers. Radar chart and ranking table.",
         "rgba(34,197,94,0.06)", "rgba(34,197,94,0.18)"),
        ("⬇️", "Research Reports", "Download self-contained HTML reports per stock — all ratios, DCF, Graham and signal summary. Print-ready.",
         "rgba(239,68,68,0.06)", "rgba(239,68,68,0.15)"),
    ]
    for i in range(0, 6, 3):
        c1, c2, c3 = st.columns(3)
        for col, (emoji, title, desc, bg, border) in zip([c1, c2, c3], _feature_cards[i:i+3]):
            with col:
                st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:14px;padding:20px;
  margin-bottom:14px;height:100%">
  <div style="font-size:1.5rem;margin-bottom:10px">{emoji}</div>
  <div style="font-weight:700;color:#e2e8f0;font-size:.9rem;margin-bottom:6px">{title}</div>
  <div style="color:#475569;font-size:.78rem;line-height:1.55">{desc}</div>
</div>
""", unsafe_allow_html=True)

    # ── Signal legend ─────────────────────────────────────────────────────
    st.markdown("<div style='font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
                "color:#334155;margin-bottom:14px'>INVESTMENT SIGNAL ENGINE</div>",
                unsafe_allow_html=True)

    # Signal badges in columns
    sg1, sg2, sg3, sg4, sg5 = st.columns([1, 1, 1, 1, 2.5])
    with sg1:
        st.markdown("<span style='color:#4ade80;font-weight:700;font-size:.82rem'>● STRONG BUY</span><br>"
                    "<span style='color:#334155;font-size:.75rem'>Score ≥ 70</span>",
                    unsafe_allow_html=True)
    with sg2:
        st.markdown("<span style='color:#86efac;font-weight:700;font-size:.82rem'>● BUY</span><br>"
                    "<span style='color:#334155;font-size:.75rem'>Score 50–69</span>",
                    unsafe_allow_html=True)
    with sg3:
        st.markdown("<span style='color:#fbbf24;font-weight:700;font-size:.82rem'>● HOLD</span><br>"
                    "<span style='color:#334155;font-size:.75rem'>Score 30–49</span>",
                    unsafe_allow_html=True)
    with sg4:
        st.markdown("<span style='color:#f87171;font-weight:700;font-size:.82rem'>● AVOID</span><br>"
                    "<span style='color:#334155;font-size:.75rem'>Score &lt; 30</span>",
                    unsafe_allow_html=True)
    with sg5:
        st.markdown("<span style='color:#475569;font-size:.75rem;'>"
                    "Graham MoS <strong style='color:#94a3b8'>40 pts</strong> &nbsp;·&nbsp;"
                    "ROE Quality <strong style='color:#94a3b8'>25 pts</strong> &nbsp;·&nbsp;"
                    "P/E <strong style='color:#94a3b8'>20 pts</strong> &nbsp;·&nbsp;"
                    "D/E <strong style='color:#94a3b8'>15 pts</strong></span>",
                    unsafe_allow_html=True)

    # ── Screener launch panel ─────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(29,78,216,0.12),rgba(139,92,246,0.08));
  border:1px solid rgba(59,130,246,0.3);border-radius:16px;padding:28px 32px;margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px">
    <div>
      <div style="font-weight:800;color:#e2e8f0;font-size:1.05rem;margin-bottom:4px">
        Ready to scan the market?
      </div>
      <div style="color:#475569;font-size:.83rem">
        Fetches live fundamentals for all stocks · Results cached for 5 min · First run ~20 s
      </div>
    </div>
    <div style="color:#334155;font-size:.78rem;text-align:right">
      <div>📡 &nbsp;Yahoo Finance API</div>
      <div style="margin-top:3px">⚡ &nbsp;15 parallel threads</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    run_btn = st.button("🚀  Run Full Screener — Scan All Stocks", type="primary",
                        width='stretch',
                        help="Fetches live data for all stocks — takes ~20 seconds on first run.")
    if run_btn:
        pb  = st.progress(0.0)
        stx = st.empty()
        with st.spinner("Analysing fundamentals across all NSE stocks…"):
            df = run_screener(STOCKS, progress_bar=pb, status_text=stx)
        pb.empty(); stx.empty()
        if df.empty:
            st.error("Screener returned no results. Check your internet connection.")
        else:
            st.session_state.screener_df = df
            st.rerun()

    # ── Disclaimer ────────────────────────────────────────────────────────
    st.markdown("""
<div style="text-align:center;color:#1e293b;font-size:.72rem;margin-top:20px">
  ⚠️ For educational purposes only — not financial advice. &nbsp;·&nbsp;
  Data via Yahoo Finance. Accuracy not guaranteed. &nbsp;·&nbsp;
  Always consult a qualified financial adviser before investing.
</div>
""", unsafe_allow_html=True)


def _render_screener_results():
    """Screener results view — shown after the screener has been run."""
    page_header("📊 Value Screener",
                f"Ranks {len(STOCKS)} NSE companies by fundamental value. Scores combine Graham safety, ROE quality, P/E, and debt levels.")

    # Controls row
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1, 1.2, 2.2, 1.3])
    with ctrl1:
        run_btn = st.button("🔄 Re-run", type="primary", width='stretch',
                            help="Re-fetches live data for all stocks.")
    with ctrl2:
        if st.button("🏠 Back to Overview", width='stretch'):
            st.session_state.screener_df = None
            st.rerun()
    with ctrl3:
        signal_filter = st.radio(
            "Show",
            ["All stocks", "BUY signals or better", "STRONG BUY only"],
            horizontal=True, label_visibility="collapsed",
        )
    with ctrl4:
        quality_only = st.checkbox("Complete data only", value=True,
            help="Hides stocks where EPS or Book Value is missing.")

    # Run
    if run_btn:
        pb  = st.progress(0.0)
        stx = st.empty()
        with st.spinner("Analyzing fundamentals…"):
            df = run_screener(STOCKS, progress_bar=pb, status_text=stx)
        pb.empty(); stx.empty()
        if df.empty:
            st.error("Screener returned no results. Check your internet connection.")
        else:
            st.session_state.screener_df = df
            st.success(f"✅ Done — {len(df)} stocks analysed and ranked.")

    df_all  = st.session_state.screener_df

    # Apply filters
    df_filt = df_all.copy()
    if signal_filter == "BUY signals or better":
        df_filt = df_filt[df_filt["Signal"].isin(["BUY","STRONG BUY"])]
    elif signal_filter == "STRONG BUY only":
        df_filt = df_filt[df_filt["Signal"] == "STRONG BUY"]
    if quality_only:
        df_filt = df_filt[df_filt["Data Quality"] >= 60]

    # KPI row
    kpi_tiles([
        {"label": "Stocks Screened",   "value": len(df_all),
         "help": "Total companies scored", "color": "#f1f5f9"},
        {"label": "Showing",           "value": len(df_filt),
         "help": "After filters",          "color": "#93c5fd"},
        {"label": "Strong Buy / Buy",  "value": len(df_all[df_all["Signal"].isin(["STRONG BUY","BUY"])]),
         "help": "Attractively priced",    "color": "#4ade80"},
        {"label": "Market Avg Score",  "value": f"{df_all['Score'].mean():.0f}/100",
         "help": "Below 50 = market looks expensive", "color": "#fbbf24"},
    ])

    # Signal chart
    sig_order  = ["STRONG BUY","BUY","HOLD","AVOID"]
    sig_clrs   = {"STRONG BUY":"#16a34a","BUY":"#4ade80","HOLD":"#ca8a04","AVOID":"#dc2626"}
    sig_counts = df_all["Signal"].value_counts().reindex(sig_order, fill_value=0)
    sc_fig = go.Figure(go.Bar(
        x=sig_counts.index.tolist(), y=sig_counts.values.tolist(),
        marker_color=[sig_clrs[s] for s in sig_counts.index],
        text=sig_counts.values.tolist(), textposition="outside",
        textfont={"color": "#e2e8f0"},
    ))
    sc_fig.update_layout(
        title=dict(text="Signal distribution across all screened stocks", font={"size": 12}),
        yaxis_title="# Stocks", yaxis={"gridcolor": "rgba(59,130,246,0.08)"},
        height=230, showlegend=False, **_DARK_LAYOUT,
    )
    st.plotly_chart(sc_fig, width='stretch')

    # Top picks
    st.markdown("#### 🏆 Top Value Picks")
    if df_filt.empty:
        st.info("No stocks match the current filters. Try 'All stocks'.")
    else:
        top10 = df_filt.head(10)
        for _, row in top10.iterrows():
            signal = row.get("Signal","")
            emoji  = row.get("Signal Emoji","")
            score  = int(row.get("Score", 0))
            graham = row.get("Graham No.")
            roe    = row.get("ROE (%)")
            pe     = row.get("P/E")
            mos    = row.get("MoS %", 0)
            price  = row.get("Price (₹)")

            border = {"STRONG BUY":"#16a34a","BUY":"#4ade80","HOLD":"#ca8a04","AVOID":"#dc2626"}.get(signal,"#334155")

            st.markdown(f"""
<div style="background:rgba(15,23,42,0.7);border:1px solid rgba(59,130,246,0.12);
border-left:3px solid {border};border-radius:12px;padding:14px 18px;margin-bottom:8px;
display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
  <div style="flex:2;min-width:200px">
    <div style="font-weight:700;color:#e2e8f0;font-size:.95rem">#{int(row['Rank'])} {row['Company']}</div>
    <div style="color:#475569;font-size:.75rem;margin-top:2px">{row['Ticker']}</div>
    <div style="color:#64748b;font-size:.78rem;margin-top:6px;line-height:1.4">{str(row.get('Explanation',''))[:120]}…</div>
  </div>
  <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center">
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">Price</div><div style="color:#f1f5f9;font-weight:700">{"₹"+f"{price:,.0f}" if (price is not None and price == price) else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">Fair Value</div><div style="color:#f1f5f9;font-weight:700">{"₹"+f"{graham:,.0f}" if (graham is not None and graham == graham) else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">MoS</div><div style="color:{"#22c55e" if (mos is not None and mos > 0) else "#ef4444"};font-weight:700">{f"{mos:+.1f}%" if (mos is not None and mos == mos) else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">ROE</div><div style="color:#f1f5f9">{f"{roe:.1f}%" if roe is not None else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">Score</div><div style="color:{border};font-weight:700">{score}/100</div></div>
  </div>
</div>""", unsafe_allow_html=True)
            if st.button(f"📈 Open Analysis — {row['Company'][:22]}", key=f"dd_{row['Ticker']}",
                         width='content'):
                st.session_state.analysis_ticker = row["Ticker"]
                st.toast(f"✅ {row['Company']} loaded — switch to 📈 Stock Analysis", icon="✅")

    # Full table
    st.markdown("#### 📋 Full Ranked Results")
    screener_table(df_filt)

    # Quick open from table
    st.markdown("")
    qa, qb = st.columns([3, 1])
    with qa:
        quick_pick = st.selectbox(
            "Open any stock in the full analysis view →",
            ["— pick a company —"] + df_filt["Company"].tolist(),
            label_visibility="visible",
        )
    with qb:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("📈 Open Analysis", type="primary", width='stretch'):
            if quick_pick != "— pick a company —":
                match = df_filt[df_filt["Company"] == quick_pick]
                if not match.empty:
                    st.session_state.analysis_ticker = match.iloc[0]["Ticker"]
                    st.toast(f"✅ {quick_pick} loaded — switch to 📈 Stock Analysis tab!", icon="✅")

    st.markdown("")
    ex1, ex2 = st.columns(2)
    with ex1:
        st.download_button("⬇️ Download Results (CSV)", data=screener_to_csv(df_filt),
                           file_name="kairoforge_screener.csv", mime="text/csv",
                           key="dl_screener_csv")
    with ex2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.caption(f"{len(df_filt)} result(s) visible. Run screener for more.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: STOCK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def render_analysis():
    page_header("📈 Stock Analysis", "In-depth Graham Number · 3-Stage DCF · Ratio analysis · Sensitivity")

    # Stock selector
    da1, da2, da3 = st.columns([3, 1.5, 1])
    with da1:
        chosen = st.selectbox("Search company", ["— choose a stock —"] + SORTED_LABELS,
                               help="Start typing to filter")
    with da2:
        custom_t = st.text_input("Or enter NSE ticker", placeholder="e.g. ZOMATO.NS")
    with da3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        analyse_btn = st.button("Analyse →", type="primary", width='stretch')

    TICKER = None
    if custom_t.strip():
        TICKER = custom_t.strip().upper()
    elif chosen != "— choose a stock —":
        TICKER = STOCKS[chosen]

    if analyse_btn and TICKER:
        st.session_state.analysis_ticker = TICKER
    elif analyse_btn:
        st.warning("Please select a stock or enter a ticker.")

    if not st.session_state.analysis_ticker:
        st.markdown("""
<div class="glass-card" style="text-align:center;padding:50px">
  <div style="font-size:2.5rem">🔍</div>
  <div style="color:#475569;margin-top:8px">Select a company and click <strong style="color:#93c5fd">Analyse</strong> to generate a full equity research report.</div>
</div>""", unsafe_allow_html=True)
        return

    TICKER = st.session_state.analysis_ticker
    with st.spinner("Fetching fundamentals…"):
        info = fetch_stock_data(TICKER)
        hist = fetch_price_history(TICKER)

    if not info:
        st.error(f"No data returned for **{TICKER}**. Check the ticker format (e.g. RELIANCE.NS).")
        return

    price      = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    eps        = safe_get(info, "trailingEps")
    bvps       = safe_get(info, "bookValue")
    name       = safe_get(info, "longName", TICKER)
    sector     = safe_get(info, "sector", "")
    industry   = safe_get(info, "industry", "")
    mkt_cap    = safe_get(info, "marketCap")
    shares_out = safe_get(info, "sharesOutstanding")
    fcf_total  = safe_get(info, "freeCashflow")
    beta       = safe_get(info, "beta", 1.0) or 1.0

    # EPS / FCF fallbacks (same logic as screener)
    net_inc = safe_get(info, "netIncomeToCommon")
    if eps is None and net_inc and shares_out and shares_out > 0:
        eps = net_inc / shares_out
    fcf_ps = (fcf_total / shares_out) if (fcf_total and shares_out and shares_out > 0) else (eps or 1.0)

    graham = calculate_graham(eps, bvps)
    ratios = calculate_ratios(info)
    wacc   = estimate_wacc(info)

    # Quick score for hero card
    qd      = _score_stock(TICKER, name, info)
    q_signal = qd.get("Signal","")
    q_score  = qd.get("Score", 0)
    q_emoji  = qd.get("Signal Emoji","")
    q_expl   = qd.get("Explanation","")

    # Hero card
    hero_card(name, TICKER, sector or industry or "Equity", price,
              q_signal, q_emoji, q_score, q_expl)

    # Export report button — always visible once a stock is loaded
    _dcf_for_report = st.session_state.get("_dcf_res")
    _dcf_params = st.session_state.get("_dcf_params")
    # If no DCF has been run yet, compute a default one for the report
    if _dcf_for_report is None and price is not None:
        _default_dcf = calculate_dcf(
            fcf_ps=max(fcf_ps, 0.01),
            g1=0.20, yr1=5, g2=0.10, yr2=5, gT=0.04,
            wacc=wacc if wacc > 0.04 else 0.10,
        )
        _dcf_for_report = _default_dcf
    _report_html = generate_html_report(
        ticker=TICKER, name=name, sector=sector or industry or "",
        price=price, signal=q_signal, score=q_score, explanation=q_expl,
        graham=graham, eps=eps, bvps=bvps, ratios=ratios,
        dcf_res=_dcf_for_report, mkt_cap=mkt_cap, beta=beta, wacc=wacc,
    )
    _safe_name = "".join(c if c.isalnum() else "_" for c in name)
    st.download_button(
        label="⬇️ Download Research Report (HTML)",
        data=_report_html.encode("utf-8"),
        file_name=f"KAIROFORGE_{_safe_name}_{TICKER}.html",
        mime="text/html",
        help="Downloads a self-contained HTML report. Open in any browser to view or print as PDF.",
        key="dl_report_html",
    )

    # Sub-tabs
    ov, val, dcf_tab, sens, pt_tab, news_tab, peer_tab = st.tabs([
        "🏠 Overview", "📐 Valuation", "💹 DCF Model",
        "🔬 Sensitivity", "🎯 Price Target", "📰 News & Sentiment", "🔄 Peer Comparison"
    ])

    # ── OVERVIEW ──────────────────────────────────────────────
    with ov:
        wh   = safe_get(info,"fiftyTwoWeekHigh")
        wl   = safe_get(info,"fiftyTwoWeekLow")
        cap  = "N/A"
        if mkt_cap:
            if mkt_cap >= 1e12: cap = f"₹{mkt_cap/1e12:.2f}T"
            elif mkt_cap >= 1e9: cap = f"₹{mkt_cap/1e9:.1f}B"
            else: cap = f"₹{mkt_cap/1e6:.0f}M"

        kpi_tiles([
            {"label": "Current Price",  "value": f"₹{price:,.2f}" if price else "N/A", "color": "#f1f5f9"},
            {"label": "Market Cap",     "value": cap, "color": "#93c5fd"},
            {"label": "Trailing EPS",   "value": f"₹{eps:,.2f}" if eps else "N/A",
             "help": "Earnings per share (trailing 12 months)", "color": "#fbbf24"},
            {"label": "Book Value/Share","value": f"₹{bvps:,.2f}" if bvps else "N/A",
             "help": "Net asset value per share", "color": "#e2e8f0"},
            {"label": "52-Week Range",  "value": f"₹{wl:,.0f}–₹{wh:,.0f}" if wh and wl else "N/A",
             "color": "#94a3b8"},
            {"label": "Beta",           "value": f"{beta:.2f}",
             "help": "Market sensitivity (1 = moves with index)", "color": "#94a3b8"},
        ])

        st.markdown("")
        if not hist.empty:
            st.plotly_chart(make_hist_chart(hist, TICKER), width='stretch')
        else:
            st.info("Historical price data unavailable.")

        desc = safe_get(info, "longBusinessSummary")
        if desc:
            with st.expander("About the company"):
                st.write(desc)

    # ── VALUATION ─────────────────────────────────────────────
    with val:
        st.markdown("#### Graham Number Analysis")
        st.caption("The Graham Number — √(22.5 × EPS × Book Value) — is the maximum price a value investor should pay.")

        if graham is None:
            st.markdown("""
<div class="glass-card">
  <div style="color:#f87171;font-weight:600">⚠️ Graham Number unavailable</div>
  <div style="color:#64748b;margin-top:6px;font-size:.85rem">EPS or Book Value is negative or missing. Graham Number can only be computed for profitable companies with positive book value.</div>
</div>""", unsafe_allow_html=True)
        else:
            mos_pct  = (graham - price) / graham * 100
            is_under = price < graham
            sign_col = "#22c55e" if is_under else "#ef4444"
            verdict  = f"{'✅ Undervalued' if is_under else '🔴 Overvalued'} by {abs(mos_pct):.1f}%"
            st.markdown(f"""
<div class="glass-card" style="border-color:{sign_col}33">
  <div style="font-size:1.1rem;font-weight:700;color:{sign_col}">{verdict}</div>
  <div style="color:#64748b;font-size:.82rem;margin-top:4px">Graham Number: <strong style="color:#e2e8f0">₹{graham:,.2f}</strong> &nbsp;·&nbsp; Current Price: <strong style="color:#e2e8f0">₹{price:,.2f}</strong></div>
</div>""", unsafe_allow_html=True)

            gc, bc = st.columns(2)
            with gc:
                st.plotly_chart(make_gauge(price, graham, "Price vs Graham Number"),
                                width='stretch')
            with bc:
                st.plotly_chart(make_bar_comp(
                    ["Current Price","Graham Number"], [price, graham],
                    ["#3b82f6","#22c55e" if is_under else "#ef4444"],
                    "Price vs Graham Number (₹)"), width='stretch')

            with st.expander("🧮 Formula breakdown"):
                st.markdown(f"""
`Graham Number = √(22.5 × EPS × Book Value per Share)`  
= √(22.5 × {eps:.2f} × {bvps:.2f}) = √{22.5*eps*bvps:,.0f} = **₹{graham:,.2f}**
""")

        st.divider()
        st.markdown("#### Key Ratios")
        pe  = ratios.get("P/E (Trailing)")
        pb  = ratios.get("P/B")
        roe = ratios.get("ROE (%)")
        rc  = ratios.get("ROIC (%)")
        de  = ratios.get("Debt / Equity")
        eg  = ratios.get("EPS Growth (%)")
        dy  = ratios.get("Dividend Yield (%)")

        def _ratio_color(metric, v):
            if v is None: return "#94a3b8"
            if metric == "P/E":   return "#22c55e" if v<=15 else "#fbbf24" if v<=30 else "#ef4444"
            if metric == "P/B":   return "#22c55e" if v<=1.5 else "#fbbf24" if v<=3 else "#ef4444"
            if metric == "ROE":   return "#22c55e" if v>=20 else "#fbbf24" if v>=10 else "#ef4444"
            if metric == "ROIC":  return "#22c55e" if v>=15 else "#fbbf24" if v>=8 else "#ef4444"
            if metric == "DE":    return "#22c55e" if v<=0.5 else "#fbbf24" if v<=1.5 else "#ef4444"
            return "#94a3b8"

        kpi_tiles([
            {"label":"P/E Ratio (TTM)","value":f"{pe:.1f}×" if pe else "N/A",
             "help":"ℹ️ Price paid per ₹1 of earnings. Under 15 is generally cheap.",
             "color":_ratio_color("P/E",pe)},
            {"label":"P/B (Price/Book)","value":f"{pb:.2f}×" if pb else "N/A",
             "help":"ℹ️ Price vs net asset value. Under 1.5 preferred by Graham.",
             "color":_ratio_color("P/B",pb)},
            {"label":"ROE (Return on Equity)","value":f"{roe:.1f}%" if roe is not None else "N/A",
             "help":"ℹ️ How efficiently management earns profit. 20%+ is excellent.",
             "color":_ratio_color("ROE",roe)},
            {"label":"ROIC","value":f"{rc:.1f}%" if rc is not None else "N/A",
             "help":"ℹ️ Return on all invested capital — includes debt.",
             "color":_ratio_color("ROIC",rc)},
            {"label":"Debt / Equity","value":f"{de:.2f}×" if de is not None else "N/A",
             "help":"ℹ️ Financial leverage. Below 0.5 is low risk.",
             "color":_ratio_color("DE",de)},
            {"label":"EPS Growth (1Y)","value":f"{eg:+.1f}%" if eg is not None else "N/A",
             "help":"ℹ️ Earnings per share change vs previous year.",
             "color":"#22c55e" if (eg or 0)>0 else "#ef4444"},
            {"label":"Dividend Yield","value":f"{dy:.2f}%" if dy else "0%",
             "help":"ℹ️ Annual dividend as % of share price.",
             "color":"#93c5fd"},
        ])

    # ── DCF ───────────────────────────────────────────────────
    with dcf_tab:
        st.markdown("#### 3-Stage DCF Valuation")
        st.caption("Discounted Cash Flow — estimates intrinsic value by projecting future cash flows and discounting them back to today.")

        if fcf_ps and fcf_ps > 0:
            st.markdown(f"Using Free Cash Flow per share: **₹{fcf_ps:.2f}**")
        else:
            if fcf_ps is not None and fcf_ps < 0:
                st.warning(
                    f"Free Cash Flow per share is negative (₹{fcf_ps:.2f}). "
                    "DCF requires positive FCF — falling back to EPS or ₹1. "
                    "Adjust the Base FCF/Share slider below to a realistic estimate."
                )
            if eps and eps > 0:
                fcf_ps = eps
                st.info(f"Using EPS (₹{eps:.2f}) as FCF proxy.")
            else:
                fcf_ps = 1.0
                st.warning("No FCF or EPS data. Defaulting to ₹1 — please adjust.")

        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown("**Stage 1 — High Growth**")
            fcf_in = st.number_input("Base FCF/Share (₹)", 0.01, 50000.0,
                                      float(round(max(fcf_ps,0.01),2)), 1.0)
            g1p = st.slider("Growth rate %", 0, 50, 20, key="g1p")
            yr1 = st.slider("Years",         1, 10, 5,  key="yr1")
        with d2:
            st.markdown("**Stage 2 — Transition**")
            g2p = st.slider("Ending growth %", 0, 20, 10, key="g2p")
            yr2 = st.slider("Years",            1, 10, 5,  key="yr2")
            gTp = st.slider("Terminal growth %",1, 10, 4,  key="gTp")
        with d3:
            st.markdown("**Discount Rate (WACC)**")
            wp  = st.slider("WACC %", 5, 25, min(25, max(5, int(round(wacc*100)))), key="wp",
                             help=f"Auto-estimated: {wacc*100:.1f}% using CAPM (β={beta:.2f})")
            st.markdown(f"""
<div class="glass-card" style="padding:12px 16px;font-size:.82rem">
  <div style="color:#64748b">Auto WACC: <strong style="color:#93c5fd">{wacc*100:.1f}%</strong></div>
  <div style="color:#334155;margin-top:4px">Rf=7.2% · ERP=7% · β={beta:.2f}</div>
</div>""", unsafe_allow_html=True)

        g1, g2, gT, w = g1p/100, g2p/100, gTp/100, wp/100
        res = calculate_dcf(fcf_in, g1, yr1, g2, yr2, gT, w)
        st.session_state["_dcf_res"]    = res
        st.session_state["_dcf_params"] = dict(fcf_in=fcf_in, g1=g1, yr1=yr1, g2=g2,
                                                yr2=yr2, gT=gT, wp=wp, price=price)

        if not res:
            st.error("WACC must be higher than the terminal growth rate.")
        elif price is None:
            st.warning("Current price unavailable — cannot compute discount to intrinsic value.")
        else:
            iv   = res["intrinsic_value"]
            dp   = (iv - price) / iv * 100
            du   = price < iv
            col  = "#22c55e" if du else "#ef4444"
            verdict = f"{'✅ Undervalued' if du else '🔴 Overvalued'} by {abs(dp):.1f}% vs DCF value"

            st.markdown(f"""
<div class="glass-card" style="border-color:{col}33;margin-top:8px">
  <div style="font-size:1.05rem;font-weight:700;color:{col}">{verdict}</div>
  <div style="color:#64748b;font-size:.82rem;margin-top:4px">DCF Intrinsic Value: <strong style="color:#e2e8f0">₹{iv:,.0f}</strong> &nbsp;·&nbsp; Market Price: <strong style="color:#e2e8f0">₹{price:,.0f}</strong></div>
</div>""", unsafe_allow_html=True)

            kpi_tiles([
                {"label":"Intrinsic Value",  "value":f"₹{iv:,.0f}",     "help":"DCF fair value",         "color":col},
                {"label":"PV Stage 1",       "value":f"₹{res['pv_stage1']:,.0f}", "help":"High-growth cash flows","color":"#22c55e"},
                {"label":"PV Stage 2",       "value":f"₹{res['pv_stage2']:,.0f}", "help":"Transition cash flows",  "color":"#fbbf24"},
                {"label":"PV Terminal",      "value":f"₹{res['pv_terminal']:,.0f}","help":"Perpetuity value",       "color":"#3b82f6"},
            ])

            ch1, ch2 = st.columns(2)
            with ch1:
                st.plotly_chart(make_dcf_waterfall(res), width='stretch')
            with ch2:
                st.plotly_chart(make_gauge(price, iv, "Price vs DCF Intrinsic Value"),
                                width='stretch')

            with st.expander("📋 Year-by-year cash flow table"):
                rows = [{"Year":yr,"FCF (₹)":f"₹{f:,.2f}","PV (₹)":f"₹{pv:,.2f}"}
                        for yr,f,pv in res["stage_cashflows"]]
                rows.append({"Year":"Terminal","FCF (₹)":f"₹{res['terminal_value']:,.2f}",
                             "PV (₹)":f"₹{res['pv_terminal']:,.2f}"})
                st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    # ── SENSITIVITY ───────────────────────────────────────────
    with sens:
        st.markdown("#### Sensitivity Analysis")
        st.caption("See how the DCF fair value changes as WACC and terminal growth assumptions shift.")

        _dcf = st.session_state.get("_dcf_res")
        _prm = st.session_state.get("_dcf_params")
        if _dcf is None or _prm is None:
            st.info("Open the **3-Stage DCF** tab first to compute a valuation, then return here.")
        elif not _dcf:
            st.warning("DCF returned no result — check WACC vs terminal growth.")
        else:
            _w   = _prm["wp"] / 100
            w_range = sorted({round(_w + (i-3)*0.01, 3) for i in range(7)
                               if 0.05 <= round(_w+(i-3)*0.01,3) <= 0.25})
            g_range = [round(0.02 + i*0.01, 2) for i in range(6)]

            with st.spinner("Computing sensitivity grid…"):
                sdf = run_sensitivity(
                    _prm["fcf_in"], _prm["g1"], _prm["yr1"],
                    _prm["g2"],    _prm["yr2"],
                    w_range, g_range,
                )

            st.plotly_chart(make_sensitivity_heatmap(sdf, _prm["price"]),
                            width='stretch')

            fmt_df = sdf.copy()
            for c in fmt_df.columns:
                fmt_df[c] = fmt_df[c].apply(lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—")
            st.dataframe(fmt_df, width='stretch')

    # ── PRICE TARGET ───────────────────────────────────────────
    with pt_tab:
        st.markdown("#### 🎯 Price Target")
        st.caption("Bull · Base · Bear scenarios derived from the DCF model.")

        _dcf_res = st.session_state.get("_dcf_res")
        _dcf_prm = st.session_state.get("_dcf_params")

        if _dcf_res is None or _dcf_prm is None:
            st.info("Open the **3-Stage DCF** tab first, click **Compute DCF Valuation**, then return here.")
        elif not _dcf_res:
            st.warning("DCF returned no result. Check WACC vs terminal growth.")
        else:
            base_iv = _dcf_res.get("intrinsic_value", 0)
            _fcf_in = _dcf_prm.get("fcf_in", 0)
            _g1 = _dcf_prm.get("g1", 0)
            _yr1 = _dcf_prm.get("yr1", 0)
            _g2 = _dcf_prm.get("g2", 0)
            _yr2 = _dcf_prm.get("yr2", 0)
            _gT = _dcf_prm.get("gT", 0.035)   # actual terminal growth used in base DCF
            _wp = _dcf_prm.get("wp", 0)
            _base_w = _wp / 100

            # Bull case: lower WACC + higher terminal growth
            bull_g = min(0.045, _gT + 0.02)
            bull_w = max(0.07, _base_w - 0.02)
            bull_res = calculate_dcf(_fcf_in, _g1, _yr1, _g2, _yr2, bull_g, bull_w)
            bull_iv = bull_res.get("intrinsic_value", base_iv)

            # Bear case: higher WACC + lower terminal growth
            bear_g = max(0.01, _gT - 0.02)
            bear_w = min(0.18, _base_w + 0.02)
            bear_res = calculate_dcf(_fcf_in, _g1, _yr1, _g2, _yr2, bear_g, bear_w)
            bear_iv = bear_res.get("intrinsic_value", base_iv)

            # Ensure ordering: bear ≤ base ≤ bull
            bear_iv = min(bear_iv, base_iv)
            bull_iv = max(bull_iv, base_iv)
            _price = _dcf_prm.get("price", 0)

            # ── KPI tiles ──
            if _price and _price > 0:
                b_up = (bull_iv - _price) / _price * 100
                b_dn = (bear_iv - _price) / _price * 100
                b_up_c = "#22c55e" if b_up > 0 else "#ef4444"
                b_dn_c = "#22c55e" if b_dn > 0 else "#ef4444"
                bull_lbl = f"🟢 ₹{bull_iv:,.0f} (+{b_up:.1f}% vs price)"
                bear_lbl = f"🔴 ₹{bear_iv:,.0f} ({b_dn:+.1f}% vs price)"
                base_lbl = f"⚪ ₹{base_iv:,.0f}"
                target_val = f"{((bull_iv + bear_iv) / 2 / _price - 1) * 100:+.1f}%"
                target_c = "#22c55e" if b_up + b_dn > 0 else "#ef4444"
            else:
                bull_lbl = f"🟢 ₹{bull_iv:,.0f}"
                bear_lbl = f"🔴 ₹{bear_iv:,.0f}"
                base_lbl = f"⚪ ₹{base_iv:,.0f}"
                target_val = "N/A"
                target_c = "#94a3b8"

            kpi_tiles([
                {"label": "Bull Case",  "value": bull_lbl,
                 "help": f"WACC {bull_w*100:.1f}% | Terminal {bull_g*100:.1f}%", "color": "#16a34a"},
                {"label": "Base Case",  "value": base_lbl,
                 "help": f"WACC {_base_w*100:.1f}% | Terminal {_gT*100:.1f}%", "color": "#3b82f6"},
                {"label": "Bear Case",  "value": bear_lbl,
                 "help": f"WACC {bear_w*100:.1f}% | Terminal {bear_g*100:.1f}%", "color": "#dc2626"},
                {"label": "Implied Upside", "value": target_val,
                 "help": "Midpoint of range vs current price", "color": target_c},
            ])

            # ── Price Target Range Bar ──
            if _price and _price > 0:
                span = bull_iv - bear_iv
                if span > 0:
                    _base_pct = (base_iv - bear_iv) / span
                    _price_pct = max(0, min(1, (_price - bear_iv) / span))

                    st.markdown("")
                    st.markdown(f"""
<div style="position:relative;height:42px;background:#0f172a;border-radius:8px;border:1px solid rgba(59,130,246,0.2);overflow:hidden">
  <div style="position:absolute;left:0;right:0;top:0;height:100%;background:linear-gradient(90deg, rgba(220,38,38,.25) 0%, rgba(59,130,246,.2) {_base_pct*100}%, rgba(22,163,74,.25) 100%)"></div>
  <div style="position:absolute;left:{_base_pct*100}%;top:0;bottom:0;width:2px;background:#3b82f6;transform:translateX(-1px)"></div>
  <div style="position:absolute;left:{_price_pct*100}%;top:0;bottom:0;width:3px;background:#fff;transform:translateX(-1.5px)"></div>
  <div style="position:absolute;bottom:4px;left:8px;font-size:10px;color:#f87171;font-weight:700">Bear ₹{bear_iv:,.0f}</div>
  <div style="position:absolute;bottom:4px;left:50%;transform:translateX(-50%);font-size:10px;color:#93c5fd;font-weight:700">Base ₹{base_iv:,.0f}</div>
  <div style="position:absolute;bottom:4px;right:8px;font-size:10px;color:#4ade80;font-weight:700">Bull ₹{bull_iv:,.0f}</div>
</div>
<div style="text-align:center;font-size:11px;color:#94a3b8;margin-top:6px">
  White marker = Current Price (₹{_price:,.2f}) &nbsp;·&nbsp; Blue line = Base Case
</div>""", unsafe_allow_html=True)

                    # Verdict text
                    if _price < bear_iv:
                        verdict = "Price sits below the bear case — deep value if assumptions hold."
                        vcol = "#22c55e"
                    elif _price < base_iv:
                        verdict = "Price sits between bear and base cases — modest value opportunity."
                        vcol = "#4ade80"
                    elif _price <= bull_iv:
                        verdict = "Price sits between base and bull cases — near fair value."
                        vcol = "#fbbf24"
                    else:
                        verdict = "Price sits above the bull case — overvalued on DCF assumptions."
                        vcol = "#ef4444"

                    st.markdown(f"""
<div style="margin-top:8px;padding:12px;border-radius:8px;background:rgba(15,23,42,0.6);border:1px solid rgba(59,130,246,0.1);">
  <strong style="color:{vcol}">{verdict}</strong>
</div>""", unsafe_allow_html=True)

                    # ── Scenario table ──
                    st.markdown("")
                    st.markdown("##### Scenario Breakdown")
                    scenario_rows = []
                    for lbl, iv, w, g in [
                        ("Bull", bull_iv, bull_w, bull_g),
                        ("Base", base_iv, _base_w, _gT),
                        ("Bear", bear_iv, bear_w, bear_g),
                    ]:
                        if _price and _price > 0:
                            ups = (iv - _price) / _price * 100
                            ups_s = f"+{ups:.1f}%" if ups > 0 else f"{ups:.1f}%"
                        else:
                            ups_s = "N/A"
                        scenario_rows.append({
                            "Scenario": lbl,
                            "Intrinsic Value": f"₹{iv:,.0f}",
                            "vs Price": ups_s,
                            "WACC": f"{w*100:.1f}%",
                            "Terminal Growth": f"{g*100:.1f}%",
                        })
                    st.dataframe(pd.DataFrame(scenario_rows), width='stretch', hide_index=True)

                    # ── Bull / Base / Bear waterfall chart ──
                    pt_fig = go.Figure()
                    pt_fig.add_trace(go.Bar(
                        name="", x=["Bear", "Base", "Bull"],
                        y=[bear_iv, base_iv, bull_iv],
                        marker_color=["#dc2626", "#3b82f6", "#16a34a"],
                        text=[f"₹{bear_iv:,.0f}", f"₹{base_iv:,.0f}", f"₹{bull_iv:,.0f}"],
                        textposition="outside",
                        textfont={"color": "#e2e8f0", "size": 12},
                    ))
                    if _price and _price > 0:
                        pt_fig.add_hline(y=_price, line_dash="dash", line_color="#f1f5f9",
                                         annotation_text=f"Current Price ₹{_price:,.0f}",
                                         annotation_position="right",
                                         annotation_font_color="#f1f5f9")
                    pt_fig.update_layout(
                        title=dict(text="Price Target Range", font={"size": 12}),
                        yaxis={"gridcolor": "rgba(59,130,246,0.08)", "title": "Intrinsic Value (₹)"},
                        height=320, showlegend=False, **_DARK_LAYOUT,
                    )
                    st.plotly_chart(pt_fig, width='stretch')
                else:
                    st.warning("Bear and Bull cases are identical — assumptions are too narrow.")
            else:
                st.warning("Current price unavailable — cannot show target range.")

    # ── NEWS & SENTIMENT ───────────────────────────────────────
    with news_tab:
        st.markdown("#### 📰 News & Sentiment")
        st.caption("Recent headlines fetched via Yahoo Finance. Sentiment is keyword-based — for context only.")

        with st.spinner("Loading news…"):
            articles = fetch_news(TICKER)

        if not articles:
            st.info("No recent news found for this ticker. Yahoo Finance may not have coverage for this stock.")
        else:
            # ── Sentiment scores ───────────────────────────────
            scores = [_score_headline(a["title"]) for a in articles]
            pos_n  = scores.count(1)
            neg_n  = scores.count(-1)
            neu_n  = scores.count(0)
            total  = len(scores)
            avg_s  = sum(scores) / total if total else 0

            # Overall label
            if avg_s >= 0.25:
                sent_label, sent_color, sent_emoji = "Bullish", "#22c55e", "🟢"
            elif avg_s <= -0.25:
                sent_label, sent_color, sent_emoji = "Bearish", "#ef4444", "🔴"
            else:
                sent_label, sent_color, sent_emoji = "Neutral", "#fbbf24", "🟡"

            # Summary KPI tiles
            kpi_tiles([
                {"label": "Overall Sentiment", "value": f"{sent_emoji} {sent_label}",
                 "help": f"Average score: {avg_s:+.2f}", "color": sent_color},
                {"label": "Positive Headlines", "value": pos_n,
                 "help": "Articles with bullish keywords", "color": "#22c55e"},
                {"label": "Neutral Headlines",  "value": neu_n,
                 "help": "No clear signal", "color": "#94a3b8"},
                {"label": "Negative Headlines", "value": neg_n,
                 "help": "Articles with bearish keywords", "color": "#ef4444"},
                {"label": "Total Articles",     "value": total,
                 "help": "From Yahoo Finance", "color": "#f1f5f9"},
            ])

            # Sentiment bar chart
            bar_fig = go.Figure(go.Bar(
                x=["Positive", "Neutral", "Negative"],
                y=[pos_n, neu_n, neg_n],
                marker_color=["#22c55e", "#94a3b8", "#ef4444"],
                text=[pos_n, neu_n, neg_n], textposition="outside",
                textfont={"color": "#e2e8f0"},
            ))
            bar_fig.update_layout(
                title=dict(text="Headline Sentiment Breakdown", font={"size": 12}),
                yaxis_title="# Articles",
                yaxis={"gridcolor": "rgba(59,130,246,0.08)"},
                height=220, showlegend=False, **_DARK_LAYOUT,
            )
            st.plotly_chart(bar_fig, width='stretch')

            st.markdown("#### Recent Headlines")

            # Render each article
            for art, sc in zip(articles, scores):
                if sc == 1:
                    badge = '<span style="background:rgba(22,163,74,.2);color:#4ade80;border:1px solid #16a34a;padding:2px 9px;border-radius:12px;font-size:.7rem;font-weight:700">POSITIVE</span>'
                    left_border = "#16a34a"
                elif sc == -1:
                    badge = '<span style="background:rgba(220,38,38,.2);color:#f87171;border:1px solid #dc2626;padding:2px 9px;border-radius:12px;font-size:.7rem;font-weight:700">NEGATIVE</span>'
                    left_border = "#dc2626"
                else:
                    badge = '<span style="background:rgba(148,163,184,.15);color:#94a3b8;border:1px solid #475569;padding:2px 9px;border-radius:12px;font-size:.7rem;font-weight:700">NEUTRAL</span>'
                    left_border = "#334155"

                pub   = _html.escape(art.get("publisher") or "")
                t_ago = _time_ago(art.get("time"))
                raw_link = art.get("link") or ""
                # Only allow http/https links — never javascript: or data: URIs
                link  = raw_link if raw_link.startswith(("http://", "https://")) else ""
                title = _html.escape(art.get("title", ""))

                meta  = " · ".join(filter(None, [pub, t_ago]))
                title_html = (
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#e2e8f0;text-decoration:none;font-weight:600;font-size:.9rem">'
                    f'{title}</a>'
                    if link else
                    f'<span style="color:#e2e8f0;font-weight:600;font-size:.9rem">{title}</span>'
                )

                st.markdown(f"""
<div style="background:rgba(15,23,42,0.6);border:1px solid rgba(59,130,246,0.1);
border-left:3px solid {left_border};border-radius:10px;
padding:12px 16px;margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
    <div style="flex:1;min-width:200px">{title_html}</div>
    <div style="white-space:nowrap">{badge}</div>
  </div>
  <div style="color:#475569;font-size:.75rem;margin-top:6px">{meta}</div>
</div>""", unsafe_allow_html=True)

            st.caption("⚠️ Sentiment is automated keyword analysis — not investment advice.")

    # ── PEER COMPARISON ───────────────────────────────────────
    with peer_tab:
        st.markdown("#### 🔄 Peer Comparison")

        # Determine the peer universe from industry first, sector as fallback
        _cur_industry = safe_get(info, "industry", "") or ""
        _cur_sector   = safe_get(info, "sector",   "") or ""

        # Industry-level match (most specific)
        _ind_peers = [
            t for t in INDUSTRY_PEERS.get(_cur_industry, [])
            if t != TICKER
        ]
        # Sector-level supplement — only same-sector tickers not already in industry list
        _sec_peers = [
            t for t in SECTOR_PEERS.get(_cur_sector, [])
            if t != TICKER and t not in _ind_peers
        ]

        if _ind_peers:
            # Industry peers are specific enough — never mix in sector peers
            _peer_tickers = _ind_peers[:7]
            _match_level  = "industry"
            _group_label  = _cur_industry
        elif _sec_peers:
            _peer_tickers = _sec_peers[:7]
            _match_level  = "sector"
            _group_label  = _cur_sector
        else:
            _peer_tickers = []
            _match_level  = ""
            _group_label  = ""

        if _peer_tickers:
            st.caption(f"Matched by **{_match_level}**: {_group_label}")
        else:
            st.caption("No industry/sector peers found in our universe — showing broad market snapshot.")

        # Fetch and score peer data
        peer_rows: list[dict] = []

        # Cap at 7 peers; yfinance data is cached so subsequent calls are fast
        _tickers_to_load = _peer_tickers[:7]

        # Absolute fallback: show a handful of large-caps as market context
        if not _tickers_to_load:
            _tickers_to_load = [
                t for t in [
                    "RELIANCE.NS","TCS.NS","HDFCBANK.NS",
                    "INFY.NS","ICICIBANK.NS","ITC.NS","KOTAKBANK.NS",
                ] if t != TICKER
            ][:6]

        with st.spinner(f"Loading {len(_tickers_to_load)} peers…"):
            for bticker in _tickers_to_load:
                try:
                    binfo = fetch_stock_data(bticker)
                    if not binfo:
                        continue
                    bname = (
                        TICKER_TO_NAME.get(bticker)
                        or safe_get(binfo, "shortName")
                        or bticker
                    )
                    brow = _score_stock(bticker, bname, binfo)
                    peer_rows.append({
                        "Ticker":  bticker,
                        "Company": bname,
                        "Price":   brow.get("Price (₹)"),
                        "Score":   brow.get("Score", 0),
                        "Signal":  brow.get("Signal", ""),
                        "MoS":     brow.get("MoS %"),
                        "ROE":     brow.get("ROE (%)"),
                        "PE":      brow.get("P/E"),
                        "DE":      brow.get("D/E"),
                    })
                except Exception:
                    continue

        # Always add the current stock at the top
        cur_row = {
            "Ticker":  TICKER,
            "Company": f"★ {name}",   # star marks the current stock
            "Price":   price,
            "Score":   q_score,
            "Signal":  q_signal,
            "MoS":     qd.get("MoS %"),
            "ROE":     qd.get("ROE (%)"),
            "PE":      qd.get("P/E"),
            "DE":      qd.get("D/E"),
        }
        all_rows = [cur_row] + peer_rows

        if len(all_rows) < 2:
            st.info("Not enough peer data available. Run the Screener to enable full peer comparison.")
        else:
            # ── Comparison table ───────────────────────────────
            sig_badge = {
                "STRONG BUY": '<span class="badge b-sb">STRONG BUY</span>',
                "BUY":        '<span class="badge b-b">BUY</span>',
                "HOLD":       '<span class="badge b-h">HOLD</span>',
                "AVOID":      '<span class="badge b-av">AVOID</span>',
            }

            def _peer_cell(col, val, is_cur):
                hi = "font-weight:700;" if is_cur else ""
                na = f'<td style="color:#334155;{hi}">—</td>'
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return na
                if col == "Company":
                    clr = "#93c5fd" if is_cur else "#cbd5e1"
                    return f'<td style="color:{clr};font-weight:700">{val}</td>'
                if col == "Signal":
                    return f"<td>{sig_badge.get(str(val), str(val))}</td>"
                if col == "Price":
                    return f'<td style="color:#e2e8f0;{hi}">₹{float(val):,.0f}</td>'
                if col == "Score":
                    border_c = {"STRONG BUY":"#16a34a","BUY":"#4ade80",
                                "HOLD":"#ca8a04","AVOID":"#dc2626"}
                    clr = border_c.get("", "#94a3b8")
                    return f'<td style="color:#f1f5f9;{hi}">{int(val)}</td>'
                if col == "MoS":
                    v = float(val)
                    clr = "#22c55e" if v > 0 else "#ef4444"
                    return f'<td style="color:{clr};{hi}">{v:+.1f}%</td>'
                if col == "ROE":
                    v = float(val)
                    clr = "#22c55e" if v >= 20 else "#fbbf24" if v >= 10 else "#ef4444"
                    return f'<td style="color:{clr};{hi}">{v:.1f}%</td>'
                if col == "PE":
                    v = float(val)
                    clr = "#22c55e" if v <= 15 else "#fbbf24" if v <= 30 else "#ef4444"
                    return f'<td style="color:{clr};{hi}">{v:.1f}×</td>'
                if col == "DE":
                    v = float(val)
                    clr = "#22c55e" if v <= 0.5 else "#fbbf24" if v <= 1.5 else "#ef4444"
                    return f'<td style="color:{clr};{hi}">{v:.2f}×</td>'
                return f"<td>{val}</td>"

            cols = ["Company", "Price", "Score", "Signal", "MoS", "ROE", "PE", "DE"]
            labels = ["Company", "Price (₹)", "Score", "Signal",
                      "MoS %", "ROE %", "P/E", "D/E"]

            header = "".join(f"<th>{l}</th>" for l in labels)
            t_rows = ""
            for r in all_rows:
                is_cur = r["Ticker"] == TICKER
                bg = "rgba(29,78,216,0.12)" if is_cur else ""
                bl = "rgba(59,130,246,0.6)" if is_cur else "transparent"
                cells = "".join(_peer_cell(c, r.get(c), is_cur) for c in cols)
                t_rows += (
                    f'<tr style="background:{bg};border-left:3px solid {bl}">'
                    f'{cells}</tr>'
                )

            st.markdown(
                f'<div class="scr-wrap"><table class="scr-table">'
                f'<thead><tr>{header}</tr></thead>'
                f'<tbody>{t_rows}</tbody></table></div>',
                unsafe_allow_html=True,
            )

            # ── Bar chart: Score comparison ─────────────────────
            st.markdown("")
            companies = [r["Company"] for r in all_rows]
            scores_v  = [r.get("Score") or 0 for r in all_rows]
            bar_cols  = [
                "#3b82f6" if r["Ticker"] == TICKER else
                "#16a34a" if (r.get("Score") or 0) >= 70 else
                "#4ade80" if (r.get("Score") or 0) >= 50 else
                "#ca8a04" if (r.get("Score") or 0) >= 30 else "#dc2626"
                for r in all_rows
            ]

            cmp_fig = go.Figure(go.Bar(
                x=companies,
                y=scores_v,
                marker_color=bar_cols,
                text=scores_v,
                textposition="outside",
                textfont={"color": "#e2e8f0"},
            ))
            cmp_fig.update_layout(
                title=dict(
                    text="Value Opportunity Score — Current Stock (blue) vs Peers",
                    font={"size": 12},
                ),
                yaxis={"range": [0, 115], "gridcolor": "rgba(59,130,246,0.08)"},
                xaxis={"tickangle": -25},
                height=320, showlegend=False, **_DARK_LAYOUT,
            )
            st.plotly_chart(cmp_fig, width='stretch')

            # ── ROE vs P/E scatter ──────────────────────────────
            sc_x, sc_y, sc_t, sc_c, sc_s = [], [], [], [], []
            for r in all_rows:
                pe_v  = r.get("PE")
                roe_v = r.get("ROE")
                if pe_v is None or roe_v is None:
                    continue
                try:
                    pe_f  = float(pe_v)
                    roe_f = float(roe_v)
                    if math.isnan(pe_f) or math.isnan(roe_f):
                        continue
                except (TypeError, ValueError):
                    continue
                sc_x.append(pe_f)
                sc_y.append(roe_f)
                sc_t.append(r["Company"])
                sc_c.append("#3b82f6" if r["Ticker"] == TICKER else "#64748b")
                sc_s.append(18 if r["Ticker"] == TICKER else 10)

            if len(sc_x) >= 2:
                scat_fig = go.Figure(go.Scatter(
                    x=sc_x, y=sc_y, mode="markers+text",
                    text=sc_t, textposition="top center",
                    textfont={"size": 9, "color": "#94a3b8"},
                    marker={"color": sc_c, "size": sc_s,
                            "line": {"color": "rgba(255,255,255,0.2)", "width": 1}},
                    hovertemplate="<b>%{text}</b><br>P/E: %{x:.1f}×<br>ROE: %{y:.1f}%<extra></extra>",
                ))
                scat_fig.update_layout(
                    title=dict(text="P/E vs ROE — lower P/E + higher ROE = better value",
                               font={"size": 12}),
                    xaxis={"title": "P/E Ratio (lower = cheaper)",
                           "gridcolor": "rgba(59,130,246,0.08)"},
                    yaxis={"title": "ROE % (higher = better)",
                           "gridcolor": "rgba(59,130,246,0.08)"},
                    height=340, **_DARK_LAYOUT,
                )
                st.plotly_chart(scat_fig, width='stretch')


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if   "Screener"  in page: render_screener()
elif "Analysis"  in page: render_analysis()


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='color:#475569;font-size:.78rem;text-align:center'>"
    "⚠️ For educational purposes only — not financial advice. "
    "All valuations are model-based estimates. Consult a qualified financial adviser before investing."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div style='text-align:center;color:#334155;font-size:.78rem;padding:6px 0 12px'>"
    "Created by <strong style='color:#475569'>Dhruv Vaniawala</strong> &nbsp;·&nbsp; "
    "<a href='mailto:uwddhruv@gmail.com' style='color:#3b82f6;text-decoration:none'>uwddhruv@gmail.com</a>"
    "</div>",
    unsafe_allow_html=True,
)
