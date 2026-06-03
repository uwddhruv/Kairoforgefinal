"""
app.py — KAIROFORGE
Institutional-Grade Equity Research Terminal for Indian Markets (NSE).

Navigation (sidebar):
  📊 Screener       — Ranked stock screener with live Value Opportunity Scores
  📈 Stock Analysis — Graham Number · 3-Stage DCF · Ratios · Sensitivity
  💼 Portfolio      — Equal-weight portfolio builder with risk metrics
"""

import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from stocks           import STOCKS, SORTED_LABELS
from data_loader      import fetch_stock_data, fetch_price_history, fetch_news, safe_get
from valuation_models import (
    calculate_graham, calculate_ratios,
    estimate_wacc, calculate_dcf, run_sensitivity,
)
from screener  import run_screener, generate_signal, score_stock as _score_stock
from portfolio import build_portfolio, compute_portfolio_metrics, portfolio_to_csv, screener_to_csv


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
if "portfolio_rows"  not in st.session_state: st.session_state.portfolio_rows  = []
if "analysis_ticker" not in st.session_state: st.session_state.analysis_ticker = None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — logo + navigation
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("logo.png", width=240)
    st.markdown("<hr style='border:1px solid rgba(59,130,246,0.2);margin:12px 0'>", unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["📊  Screener", "📈  Stock Analysis", "💼  Portfolio Builder"],
        label_visibility="collapsed",
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
    st.markdown(f"""
<div class="hero-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px">
    <div>
      <div style="color:#475569;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px">{sector}</div>
      <div style="font-size:1.75rem;font-weight:800;color:#f1f5f9;line-height:1.1">{name}</div>
      <div style="color:#475569;font-size:.85rem;margin-top:5px">NSE &nbsp;·&nbsp; <strong style="color:#93c5fd">{ticker}</strong></div>
    </div>
    <div style="text-align:right">
      <div style="font-size:2.1rem;font-weight:800;color:#f1f5f9;font-variant-numeric:tabular-nums">{p}</div>
      <div style="margin-top:10px">
        <span style="background:{bg};color:{col};border:1px solid {col};padding:5px 16px;border-radius:20px;font-weight:700;font-size:.85rem">{emoji} {signal}</span>
      </div>
      <div style="color:#475569;font-size:.78rem;margin-top:8px">Value Score &nbsp;<strong style="color:{col}">{score}/100</strong></div>
    </div>
  </div>
  <div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(59,130,246,0.12);color:#64748b;font-size:.82rem;line-height:1.5">{explanation[:200]}{"…" if len(explanation)>200 else ""}</div>
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
    page_header("📊 Value Screener",
                f"Ranks {len(STOCKS)} NSE companies by fundamental value. Scores combine Graham safety, ROE quality, P/E, and debt levels.")

    # How it works
    with st.expander("ℹ️ How does the scoring work?", expanded=False):
        st.markdown("""
| What we check | Plain English | Weight |
|---|---|---|
| **Graham Number margin of safety** | Is the stock cheaper than what Graham's formula says it's worth? | 40 pts |
| **Return on Equity (ROE)** | Is the company earning good returns on shareholder money? | 25 pts |
| **Price-to-Earnings (P/E)** | Are you paying a fair price relative to earnings? | 20 pts |
| **Debt level (D/E)** | Is the balance sheet safe? | 15 pts |

**Score → Signal:** ≥70 = 🟢 STRONG BUY · 50–69 = BUY · 30–49 = HOLD · <30 = 🔴 AVOID
        """)

    # Controls
    ctrl1, ctrl2, ctrl3 = st.columns([1.2, 2.5, 1.3])
    with ctrl1:
        run_btn = st.button("🚀 Run Screener", type="primary", use_container_width=True,
                            help="Fetches live data for all stocks — takes ~20 seconds on first run.")
    with ctrl2:
        signal_filter = st.radio(
            "Show",
            ["All stocks", "BUY signals or better", "STRONG BUY only"],
            horizontal=True, label_visibility="collapsed",
        )
    with ctrl3:
        quality_only = st.checkbox("Complete data only", value=True,
            help="Hides stocks where EPS or Book Value is missing — scores for those are less reliable.")

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

    if st.session_state.screener_df is None:
        st.markdown("""
<div class="glass-card" style="text-align:center;padding:40px">
  <div style="font-size:2.5rem">📊</div>
  <div style="color:#475569;margin-top:8px">Click <strong style="color:#93c5fd">Run Screener</strong> to fetch live data and rank all stocks by value opportunity.</div>
</div>""", unsafe_allow_html=True)
        return

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
    st.plotly_chart(sc_fig, use_container_width=True)

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
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">Price</div><div style="color:#f1f5f9;font-weight:700">{"₹"+f"{price:,.0f}" if price else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">Fair Value</div><div style="color:#f1f5f9;font-weight:700">{"₹"+f"{graham:,.0f}" if graham else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">MoS</div><div style="color:{"#22c55e" if mos>0 else "#ef4444"};font-weight:700">{mos:+.1f}%</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">ROE</div><div style="color:#f1f5f9">{f"{roe:.1f}%" if roe is not None else "N/A"}</div></div>
    <div style="text-align:center"><div style="color:#475569;font-size:.68rem;text-transform:uppercase;letter-spacing:.05em">Score</div><div style="color:{border};font-weight:700">{score}/100</div></div>
  </div>
</div>""", unsafe_allow_html=True)
            if st.button(f"📈 Open Analysis — {row['Company'][:22]}", key=f"dd_{row['Ticker']}",
                         use_container_width=False):
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
        if st.button("📈 Open Analysis", type="primary", use_container_width=True):
            if quick_pick != "— pick a company —":
                match = df_filt[df_filt["Company"] == quick_pick]
                if not match.empty:
                    st.session_state.analysis_ticker = match.iloc[0]["Ticker"]
                    st.toast(f"✅ {quick_pick} loaded — switch to 📈 Stock Analysis tab!", icon="✅")

    st.markdown("")
    ex1, ex2 = st.columns(2)
    with ex1:
        st.download_button("⬇️ Download Results (CSV)", data=screener_to_csv(df_filt),
                           file_name="kairoforge_screener.csv", mime="text/csv")
    with ex2:
        add_labels = st.multiselect("Add to Portfolio →",
                                    options=df_filt["Company"].tolist(),
                                    placeholder="Select stocks…")
        if add_labels and st.button("➕ Add to Portfolio", type="secondary"):
            existing = {r["Company"] for r in st.session_state.portfolio_rows}
            added = 0
            for lbl in add_labels:
                m = df_filt[df_filt["Company"] == lbl]
                if not m.empty and lbl not in existing:
                    st.session_state.portfolio_rows.append(m.iloc[0].to_dict())
                    existing.add(lbl); added += 1
            st.success(f"Added {added} stock(s). Switch to 💼 Portfolio Builder.")


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
        analyse_btn = st.button("Analyse →", type="primary", use_container_width=True)

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

    # Sub-tabs
    ov, val, dcf_tab, sens, news_tab = st.tabs([
        "🏠 Overview", "📐 Valuation", "💹 DCF Model", "🔬 Sensitivity", "📰 News & Sentiment"
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
            st.plotly_chart(make_hist_chart(hist, TICKER), use_container_width=True)
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
                                use_container_width=True)
            with bc:
                st.plotly_chart(make_bar_comp(
                    ["Current Price","Graham Number"], [price, graham],
                    ["#3b82f6","#22c55e" if is_under else "#ef4444"],
                    "Price vs Graham Number (₹)"), use_container_width=True)

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
            if eps and eps > 0:
                fcf_ps = eps
                st.info(f"FCF unavailable — using EPS (₹{eps:.2f}) as proxy.")
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
            wp  = st.slider("WACC %", 5, 25, int(round(wacc*100)), key="wp",
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
                                                yr2=yr2, wp=wp, price=price)

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
                st.plotly_chart(make_dcf_waterfall(res), use_container_width=True)
            with ch2:
                st.plotly_chart(make_gauge(price, iv, "Price vs DCF Intrinsic Value"),
                                use_container_width=True)

            with st.expander("📋 Year-by-year cash flow table"):
                rows = [{"Year":yr,"FCF (₹)":f"₹{f:,.2f}","PV (₹)":f"₹{pv:,.2f}"}
                        for yr,f,pv in res["stage_cashflows"]]
                rows.append({"Year":"Terminal","FCF (₹)":f"₹{res['terminal_value']:,.2f}",
                             "PV (₹)":f"₹{res['pv_terminal']:,.2f}"})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
                            use_container_width=True)

            fmt_df = sdf.copy()
            for c in fmt_df.columns:
                fmt_df[c] = fmt_df[c].apply(lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—")
            st.dataframe(fmt_df, use_container_width=True)

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
            st.plotly_chart(bar_fig, use_container_width=True)

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

                pub   = art.get("publisher") or ""
                t_ago = _time_ago(art.get("time"))
                link  = art.get("link") or ""
                title = art.get("title", "")

                meta  = " · ".join(filter(None, [pub, t_ago]))
                title_html = (
                    f'<a href="{link}" target="_blank" '
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


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO BUILDER
# ═══════════════════════════════════════════════════════════════════════════
def render_portfolio():
    page_header("💼 Portfolio Builder", "Simulate an equal-weight portfolio from your screener picks.")

    if st.session_state.screener_df is not None:
        df_scr = st.session_state.screener_df
        in_port = {r["Company"] for r in st.session_state.portfolio_rows}
        avail   = [n for n in df_scr["Company"].tolist() if n not in in_port]

        pa, pb = st.columns([3, 1])
        with pa:
            manual_add = st.multiselect("Add stocks from screener", options=avail,
                                        placeholder="Search and select…", max_selections=10)
        with pb:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("➕ Add", type="primary", use_container_width=True) and manual_add:
                for lbl in manual_add:
                    m = df_scr[df_scr["Company"] == lbl]
                    if not m.empty and lbl not in in_port:
                        st.session_state.portfolio_rows.append(m.iloc[0].to_dict())
                        in_port.add(lbl)
                st.rerun()
    else:
        st.info("Run the **📊 Screener** first to enable stock selection.")

    if st.session_state.portfolio_rows:
        to_remove = st.multiselect("Remove stocks", [r["Company"] for r in st.session_state.portfolio_rows])
        if to_remove and st.button("🗑️ Remove", type="secondary"):
            st.session_state.portfolio_rows = [r for r in st.session_state.portfolio_rows
                                               if r["Company"] not in to_remove]
            st.rerun()

    if not st.session_state.portfolio_rows:
        st.markdown("""
<div class="glass-card" style="text-align:center;padding:40px">
  <div style="font-size:2.5rem">💼</div>
  <div style="color:#475569;margin-top:8px">Your portfolio is empty.<br>Run the Screener, then add stocks here to build a hypothetical portfolio.</div>
</div>""", unsafe_allow_html=True)
        return

    port_df = build_portfolio(st.session_state.portfolio_rows)
    metrics = compute_portfolio_metrics(port_df)

    risk_color = {"LOW": "#22c55e", "MEDIUM": "#fbbf24", "HIGH": "#ef4444"}.get(
        metrics.get("risk_level","MEDIUM"), "#94a3b8")

    kpi_tiles([
        {"label":"Holdings",        "value":metrics["n_stocks"],              "color":"#f1f5f9"},
        {"label":"Avg Value Score", "value":f"{metrics['avg_score']:.0f}/100","color":"#93c5fd"},
        {"label":"Avg Margin of Safety","value":f"{metrics['avg_mos']:+.1f}%",
         "help":"ℹ️ How far below fair value on average",
         "color":"#22c55e" if metrics['avg_mos']>0 else "#ef4444"},
        {"label":"Avg Beta",        "value":f"{metrics['avg_beta']:.2f}",
         "help":"ℹ️ Portfolio volatility vs market","color":"#fbbf24"},
        {"label":"Portfolio Risk",  "value":metrics.get("risk_level","—"),   "color":risk_color},
        {"label":"Avg Data Quality","value":f"{int(metrics.get('avg_data_quality',0))}/100","color":"#94a3b8"},
    ])

    # Holdings table
    st.markdown("#### Holdings")
    disp = ["Ticker","Company","Price (₹)","Weight (%)","Score","Signal","MoS (%)","ROE (%)","Beta"]
    st.dataframe(port_df[[c for c in disp if c in port_df.columns]],
                 use_container_width=True, hide_index=True)

    # Charts
    pie_col, bar_col = st.columns(2)
    with pie_col:
        pie = go.Figure(go.Pie(
            labels=port_df["Company"].str[:22].tolist(),
            values=port_df["Weight (%)"].tolist(),
            hole=0.5, textinfo="label+percent",
            textfont={"size": 11},
            marker={"line": {"color": "rgba(0,0,0,0)", "width": 0}},
        ))
        pie.update_layout(title="Allocation", height=330, showlegend=False, **_DARK_LAYOUT)
        st.plotly_chart(pie, use_container_width=True)

    with bar_col:
        sig_c = {"STRONG BUY":"#16a34a","BUY":"#4ade80","HOLD":"#ca8a04","AVOID":"#dc2626"}
        sc_b  = go.Figure(go.Bar(
            x=port_df["Company"].str[:20].tolist(),
            y=port_df["Score"].tolist(),
            marker_color=[sig_c.get(s,"#94a3b8") for s in port_df["Signal"].tolist()],
            text=port_df["Score"].tolist(), textposition="outside",
            textfont={"color":"#e2e8f0"},
        ))
        sc_b.update_layout(title="Value Score by Holding", height=330, yaxis_range=[0,115],
                           yaxis={"gridcolor":"rgba(59,130,246,0.08)"},
                           xaxis_tickangle=-30, **_DARK_LAYOUT)
        st.plotly_chart(sc_b, use_container_width=True)

    # Signal count
    sc_c = metrics.get("signal_counts",{})
    if sc_c:
        emoji_m = {"STRONG BUY":"🟢","BUY":"🟩","HOLD":"🟡","AVOID":"🔴"}
        sig_tiles = [{"label":f"{emoji_m.get(s,'')} {s}","value":v,
                      "color":{"STRONG BUY":"#22c55e","BUY":"#4ade80","HOLD":"#fbbf24","AVOID":"#ef4444"}.get(s,"#94a3b8")}
                     for s,v in sc_c.items()]
        kpi_tiles(sig_tiles)

    # Rationale
    with st.expander("📝 Investment rationale — all holdings"):
        for _, row in port_df.iterrows():
            st.markdown(f"**{row['Company']}** `{row['Ticker']}` — Score {row['Score']}/100 · {row['Signal']}")
            st.markdown(row.get("Explanation",""))
            st.divider()

    st.download_button("⬇️ Download Portfolio (CSV)", data=portfolio_to_csv(port_df),
                       file_name="kairoforge_portfolio.csv", mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if   "Screener"  in page: render_screener()
elif "Analysis"  in page: render_analysis()
elif "Portfolio" in page: render_portfolio()


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
