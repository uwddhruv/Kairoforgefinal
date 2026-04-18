"""
app.py
------
Production-grade Indian Stock Valuation & Screening Dashboard.

Tabs
----
📊 Screener        — Parallel Nifty stock screener, ranked by Value Opportunity Score
📈 Deep Analysis   — Graham + DCF + Sensitivity + Ratio analysis for a single stock
💼 Portfolio       — Build a hypothetical equal-weight portfolio from screener picks
"""

import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from stocks           import STOCKS, SORTED_LABELS
from data_loader      import fetch_stock_data, fetch_price_history, safe_get
from valuation_models import (
    calculate_graham, calculate_ratios,
    estimate_wacc, calculate_dcf, run_sensitivity,
)
from screener  import run_screener, generate_signal
from portfolio import build_portfolio, compute_portfolio_metrics, portfolio_to_csv, screener_to_csv


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KAIROFORGE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# MINIMAL GLOBAL STYLE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="metric-container"]{
    background:#f8fafc;border:1px solid #e2e8f0;
    border-radius:10px;padding:12px 16px;
}
.sig-strong-buy{color:#fff;background:#16a34a;padding:3px 10px;border-radius:20px;font-weight:700;font-size:.85rem}
.sig-buy       {color:#fff;background:#4ade80;padding:3px 10px;border-radius:20px;font-weight:700;font-size:.85rem;color:#14532d}
.sig-hold      {color:#fff;background:#ca8a04;padding:3px 10px;border-radius:20px;font-weight:700;font-size:.85rem}
.sig-avoid     {color:#fff;background:#dc2626;padding:3px 10px;border-radius:20px;font-weight:700;font-size:.85rem}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(v, prefix="₹", dec=2):
    return f"{prefix}{v:,.{dec}f}" if v is not None else "N/A"

def _pct(v, dec=1):
    return f"{v:+.{dec}f}%" if v is not None else "N/A"

def _signal_badge(signal: str) -> str:
    cls = {"STRONG BUY": "sig-strong-buy", "BUY": "sig-buy",
           "HOLD": "sig-hold", "AVOID": "sig-avoid"}.get(signal, "")
    return f'<span class="{cls}">{signal}</span>'

def make_gauge(current, target, title=""):
    is_under  = current < target
    bar_color = "#22c55e" if is_under else "#ef4444"
    max_r     = max(current, target) * 1.65
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        number={"prefix": "₹", "valueformat": ",.0f", "font": {"size": 28}},
        delta={"reference": target, "prefix": "₹", "valueformat": ",.0f",
               "increasing": {"color": "#ef4444"}, "decreasing": {"color": "#22c55e"}},
        title={"text": title, "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, max_r], "tickprefix": "₹", "tickformat": ","},
            "bar":  {"color": bar_color, "thickness": 0.26},
            "steps": [
                {"range": [0, target],  "color": "rgba(34,197,94,.12)"},
                {"range": [target, max_r], "color": "rgba(239,68,68,.12)"},
            ],
            "threshold": {"line": {"color": "#1e40af", "width": 3},
                          "value": target, "thickness": 0.85},
        },
    ))
    fig.update_layout(height=260, margin={"t": 50, "b": 10, "l": 10, "r": 10})
    return fig

def make_bar_comp(labels, values, colors, title=""):
    fig = go.Figure()
    for lbl, val, col in zip(labels, values, colors):
        fig.add_trace(go.Bar(
            name=lbl, x=[lbl], y=[val],
            marker_color=col,
            text=[f"₹{val:,.0f}"], textposition="outside",
        ))
    fig.update_layout(
        title=title, showlegend=False,
        yaxis={"tickprefix": "₹", "tickformat": ","},
        height=300, margin={"t": 50, "b": 20, "l": 10, "r": 10},
    )
    return fig

def make_hist_chart(hist, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        name="Close", line={"color": "#3b82f6", "width": 1.8},
        fill="tozeroy", fillcolor="rgba(59,130,246,.08)",
    ))
    if len(hist) >= 50:
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(50).mean(),
            name="50D SMA", line={"color": "#f59e0b", "width": 1.2, "dash": "dot"}))
    if len(hist) >= 200:
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"].rolling(200).mean(),
            name="200D SMA", line={"color": "#8b5cf6", "width": 1.2, "dash": "dash"}))
    fig.update_layout(
        title=f"{ticker} — 5-Year Price History",
        yaxis={"tickprefix": "₹", "tickformat": ","},
        legend={"orientation": "h", "y": 1.08},
        height=360, margin={"t": 60, "b": 30, "l": 10, "r": 10}, hovermode="x unified",
    )
    return fig

def make_dcf_waterfall(result):
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["relative","relative","relative","total"],
        x=["Stage 1\nHigh Growth","Stage 2\nTransition","Terminal\nValue","Intrinsic\nValue"],
        y=[result["pv_stage1"], result["pv_stage2"], result["pv_terminal"], result["intrinsic_value"]],
        texttemplate="₹%{y:,.0f}", textposition="outside",
        connector={"line": {"color": "#94a3b8"}},
        increasing={"marker": {"color": "#22c55e"}},
        totals={"marker": {"color": "#3b82f6"}},
    ))
    fig.update_layout(
        title="DCF Components (₹/Share)",
        yaxis={"tickprefix": "₹", "tickformat": ","},
        height=320, margin={"t": 60, "b": 30, "l": 10, "r": 10}, showlegend=False,
    )
    return fig

def make_sensitivity_heatmap(df, current_price):
    z  = df.values.astype(float)
    fig = go.Figure(go.Heatmap(
        z=z, x=list(df.columns), y=list(df.index),
        colorscale=[[0,"#ef4444"],[0.5,"#fef08a"],[1,"#22c55e"]],
        zmid=current_price,
        text=[[f"₹{v:,.0f}" if not math.isnan(v) else "—" for v in row] for row in z],
        texttemplate="%{text}", textfont={"size": 11},
        colorbar={"title": "Fair Value", "tickprefix": "₹", "tickformat": ","},
    ))
    fig.update_layout(
        title=f"DCF Sensitivity  |  Current Price ₹{current_price:,.0f}",
        xaxis_title="Terminal Growth", yaxis_title="WACC",
        height=400, margin={"t": 60, "b": 40, "l": 80, "r": 20},
    )
    return fig

def score_donut(score):
    color = "#16a34a" if score >= 70 else "#4ade80" if score >= 50 else "#ca8a04" if score >= 30 else "#dc2626"
    fig = go.Figure(go.Pie(
        values=[score, 100 - score],
        hole=0.72,
        marker_colors=[color, "#f1f5f9"],
        textinfo="none",
        hoverinfo="skip",
    ))
    fig.add_annotation(text=f"<b>{score}</b>", x=0.5, y=0.5,
                       font_size=32, showarrow=False)
    fig.update_layout(showlegend=False, height=180,
                      margin={"t": 10, "b": 10, "l": 10, "r": 10})
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
if "screener_df"     not in st.session_state: st.session_state.screener_df     = None
if "portfolio_rows"  not in st.session_state: st.session_state.portfolio_rows  = []
if "analysis_ticker" not in st.session_state: st.session_state.analysis_ticker = None


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
logo_col, title_col = st.columns([1, 4])
with logo_col:
    st.image("logo.png", width=140)
with title_col:
    st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
    st.markdown("# KAIROFORGE")
    st.markdown(
        "<span style='color:#94a3b8;font-size:1rem'>"
        "Institutional-Grade Equity Research — Indian Markets (NSE)</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Value Screening · Graham Number · 3-Stage DCF · Ratio Analysis · Portfolio Simulation  "
        "| Data: Yahoo Finance via yfinance"
    )
    st.markdown("</div>", unsafe_allow_html=True)
st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_screen, tab_analysis, tab_portfolio = st.tabs([
    "📊  Screener",
    "📈  Deep Analysis",
    "💼  Portfolio Builder",
])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — SCREENER
# ═══════════════════════════════════════════════════════════════════════════
with tab_screen:
    st.markdown("### Value Screener — Nifty Top Stocks")

    # ── Plain-language intro ───────────────────────────────────
    with st.expander("ℹ️  How does the screener work?", expanded=False):
        st.markdown("""
The screener automatically fetches live data for **{n} NSE-listed companies** and
rates each one on four things every value investor cares about:

| What we check | Why it matters | Max points |
|---|---|---|
| **Price vs Graham Number** | Is the stock cheaper than what Benjamin Graham's formula says it's worth? | 40 |
| **Return on Equity (ROE)** | Is the company using shareholder money efficiently? | 25 |
| **P/E Ratio** | Are you paying a fair price relative to earnings? | 20 |
| **Debt level** | Does the company carry too much debt? | 15 |

The total gives a **Value Score out of 100**.  
Stocks scoring **70+** get a 🟢 STRONG BUY signal, **50–69** get BUY, **30–49** HOLD, and below 30 AVOID.
        """.format(n=len(STOCKS)))

    # ── Controls row ──────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([1.5, 2, 1.5])
    with ctrl1:
        run_btn = st.button("🚀 Run Screener", type="primary", use_container_width=True,
                            help="Fetches live data for all stocks and scores them. Takes ~20 seconds.")
    with ctrl2:
        signal_filter = st.radio(
            "Which stocks to show",
            ["All stocks", "Potential buys (BUY or better)", "Best picks only (STRONG BUY)"],
            horizontal=True,
        )
    with ctrl3:
        quality_only = st.checkbox(
            "Complete data only",
            value=True,
            help="Hides stocks where key data like EPS or Book Value is missing, making the score unreliable.",
        )

    # ── Run screener ──────────────────────────────────────────
    if run_btn:
        pb  = st.progress(0.0)
        stx = st.empty()
        with st.spinner(""):
            df = run_screener(STOCKS, progress_bar=pb, status_text=stx)
        pb.empty(); stx.empty()
        if df.empty:
            st.error("Screener returned no results. Check your internet connection and try again.")
        else:
            st.session_state.screener_df = df
            st.success(f"✅ Screener done — {len(df)} stocks analysed. Results cached for 5 minutes.")

    # ── Display results ───────────────────────────────────────
    if st.session_state.screener_df is not None:
        df_all = st.session_state.screener_df

        # Apply user-friendly filters
        df_filt = df_all.copy()
        if signal_filter == "Potential buys (BUY or better)":
            df_filt = df_filt[df_filt["Signal"].isin(["BUY","STRONG BUY"])]
        elif signal_filter == "Best picks only (STRONG BUY)":
            df_filt = df_filt[df_filt["Signal"] == "STRONG BUY"]
        if quality_only:
            # Only keep stocks where at least price + one valuation metric is available
            df_filt = df_filt[df_filt["Data Quality"] >= 60]

        # ── KPI row ───────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Stocks Screened", len(df_all),
                  help="Total companies fetched and scored")
        k2.metric("Showing",  len(df_filt),
                  help="After applying your filters above")
        k3.metric("Strong Buy / Buy",
                  len(df_all[df_all["Signal"].isin(["STRONG BUY","BUY"])]),
                  help="Stocks we think look attractively priced right now")
        avg_sc = df_all["Score"].mean()
        k4.metric("Market Avg Score", f"{avg_sc:.0f} / 100",
                  help="Average value score across all screened stocks. Below 50 = market looks expensive.")
        st.markdown("")

        # Signal distribution mini-chart
        sig_counts = df_all["Signal"].value_counts().reindex(
            ["STRONG BUY","BUY","HOLD","AVOID"], fill_value=0)
        sig_colors_map = {"STRONG BUY":"#16a34a","BUY":"#4ade80","HOLD":"#ca8a04","AVOID":"#dc2626"}
        sc_fig = go.Figure(go.Bar(
            x=sig_counts.index.tolist(), y=sig_counts.values.tolist(),
            marker_color=[sig_colors_map[s] for s in sig_counts.index],
            text=sig_counts.values.tolist(), textposition="outside",
        ))
        sc_fig.update_layout(
            title="How the market looks right now — signal breakdown",
            height=240, yaxis_title="Number of stocks",
            margin={"t":50,"b":20,"l":10,"r":10}, showlegend=False,
        )
        st.plotly_chart(sc_fig, use_container_width=True)

        # ── Top 10 Value Picks ────────────────────────────────
        st.markdown("#### 🏆 Top Value Picks")
        if df_filt.empty:
            st.info("No stocks match your current filters. Try selecting 'All stocks'.")
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

                with st.container():
                    cc1, cc2, cc3, cc4, cc5, cc6 = st.columns([2.2, 1, 1, 1, 1, 0.9])
                    with cc1:
                        st.markdown(f"**{int(row['Rank'])}. {row['Company']}**  \n`{row['Ticker']}`")
                        expl = row.get("Explanation","")
                        st.caption(expl[:130] + ("…" if len(expl) > 130 else ""))
                    with cc2:
                        st.metric("Price", _fmt(row["Price (₹)"]))
                    with cc3:
                        g_label = _fmt(graham) if graham else "N/A"
                        mos_str = f"{mos:+.1f}% vs Graham" if graham else ""
                        st.metric("Fair Value", g_label, delta=mos_str if mos_str else None,
                                  delta_color="normal" if mos >= 0 else "inverse")
                    with cc4:
                        st.metric("ROE",  f"{roe:.1f}%" if roe is not None else "N/A")
                        st.metric("P/E",  f"{pe:.1f}×" if pe is not None else "N/A")
                    with cc5:
                        st.metric("Score", f"{score}/100")
                        st.markdown(f"{emoji} **{signal}**")
                    with cc6:
                        # "Analyse" button — loads this stock in the Deep Analysis tab
                        if st.button("📈 Deep Dive", key=f"dd_{row['Ticker']}", use_container_width=True,
                                     help="Load this stock in the Deep Analysis tab"):
                            st.session_state.analysis_ticker = row["Ticker"]
                            st.toast(f"✅ {row['Company']} loaded — switch to the 📈 Deep Analysis tab!", icon="✅")
                st.divider()

        # ── Full ranked table ─────────────────────────────────
        st.markdown("#### 📋 Full Results Table")
        display_cols = [
            "Rank","Ticker","Company","Price (₹)","Graham No.",
            "MoS %","ROE (%)","P/E","D/E","Score","Signal","Data Quality"
        ]
        display_df = df_filt[[c for c in display_cols if c in df_filt.columns]].copy()
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # ── Quick stock opener ────────────────────────────────
        st.markdown("")
        qa, qb = st.columns([3, 1])
        with qa:
            quick_pick = st.selectbox(
                "🔍 Select any stock from the list to open its full analysis",
                ["— pick a stock —"] + df_filt["Company"].tolist(),
                label_visibility="visible",
            )
        with qb:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("📈 Open Analysis", type="primary", use_container_width=True):
                if quick_pick != "— pick a stock —":
                    match = df_filt[df_filt["Company"] == quick_pick]
                    if not match.empty:
                        st.session_state.analysis_ticker = match.iloc[0]["Ticker"]
                        st.toast(f"✅ {quick_pick} loaded — switch to the 📈 Deep Analysis tab!", icon="✅")
                else:
                    st.warning("Pick a stock first.")

        # ── Export ────────────────────────────────────────────
        st.markdown("")
        st.download_button(
            "⬇️ Download Results as CSV",
            data=screener_to_csv(df_filt),
            file_name="alphaforge_screener.csv",
            mime="text/csv",
            help="Opens in Excel or Google Sheets",
        )

        # ── Add to portfolio ──────────────────────────────────
        st.markdown("")
        st.markdown("#### ➕ Add to Portfolio Builder")
        add_labels = st.multiselect(
            "Select stocks to add to your portfolio",
            options=df_filt["Company"].tolist(),
            help="Stocks you pick here will appear in the Portfolio Builder tab.",
        )
        if add_labels and st.button("Add to Portfolio →", type="secondary"):
            existing = {r["Company"] for r in st.session_state.portfolio_rows}
            added = 0
            for lbl in add_labels:
                match = df_filt[df_filt["Company"] == lbl]
                if not match.empty and lbl not in existing:
                    st.session_state.portfolio_rows.append(match.iloc[0].to_dict())
                    existing.add(lbl)
                    added += 1
            st.success(f"Added {added} stock(s) to your Portfolio. Switch to the 💼 Portfolio Builder tab.")
    else:
        st.info("👆 Click **Run Screener** above to analyse all stocks and see ranked results.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — DEEP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
with tab_analysis:
    st.markdown("### Single-Stock Deep Analysis")

    # ── Stock selector ────────────────────────────────────────
    da_col1, da_col2, da_col3 = st.columns([3, 1.5, 1])
    with da_col1:
        chosen = st.selectbox(
            "🔍 Select a stock",
            ["— choose —"] + SORTED_LABELS,
            help="Type to filter by company name."
        )
    with da_col2:
        custom_t = st.text_input("Or enter ticker", placeholder="e.g. ZOMATO.NS")
    with da_col3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        analyse_btn = st.button("Analyse 🚀", type="primary", use_container_width=True)

    TICKER = None
    if custom_t.strip():
        TICKER = custom_t.strip().upper()
    elif chosen != "— choose —":
        TICKER = STOCKS[chosen]

    if analyse_btn and TICKER is None:
        st.warning("Please select a stock or enter a ticker.")

    if TICKER and analyse_btn:
        st.session_state.analysis_ticker = TICKER

    if st.session_state.analysis_ticker:
        TICKER = st.session_state.analysis_ticker

        with st.spinner(f"Loading **{TICKER}** …"):
            info = fetch_stock_data(TICKER)
            hist = fetch_price_history(TICKER)

        if not info:
            st.error(f"No data found for **{TICKER}**. Check the ticker format.")
            st.stop()

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

        fcf_ps = (fcf_total / shares_out) if (fcf_total and shares_out and shares_out > 0) else None
        graham = calculate_graham(eps, bvps)
        ratios = calculate_ratios(info)
        wacc   = estimate_wacc(info)

        # Quick signal
        from screener import score_stock as _sc
        quick_data = _sc(TICKER, name, info)
        q_signal   = quick_data.get("Signal","")
        q_score    = quick_data.get("Score", 0)
        q_emoji    = quick_data.get("Signal Emoji","")

        # ── Company header ────────────────────────────────────
        st.markdown(f"### {name}")
        if sector: st.caption(f"{sector}  ·  {industry}  ·  `{TICKER}`")

        hd1, hd2, hd3 = st.columns([1, 1, 3])
        with hd1:
            st.plotly_chart(score_donut(q_score), use_container_width=True)
        with hd2:
            st.metric("Value Score", f"{q_score}/100")
            st.markdown(f"**Signal:** {q_emoji} **{q_signal}**")
        with hd3:
            st.markdown("**Investment Rationale**")
            st.markdown(quick_data.get("Explanation",""))

        st.divider()

        # ── Sub-tabs ──────────────────────────────────────────
        ov, val, dcf_tab, sens = st.tabs([
            "🏠 Overview", "📐 Valuation", "💹 DCF", "🔬 Sensitivity"
        ])

        # ── Overview ─────────────────────────────────────────
        with ov:
            o1,o2,o3,o4,o5 = st.columns(5)
            o1.metric("Price", _fmt(price))
            cap = "N/A"
            if mkt_cap:
                if mkt_cap >= 1e12: cap = f"₹{mkt_cap/1e12:.2f}T"
                elif mkt_cap >= 1e9: cap = f"₹{mkt_cap/1e9:.2f}B"
                else: cap = f"₹{mkt_cap/1e6:.0f}M"
            o2.metric("Market Cap", cap)
            o3.metric("Trailing EPS", _fmt(eps))
            o4.metric("Book Value", _fmt(bvps))
            wh = safe_get(info,"fiftyTwoWeekHigh"); wl = safe_get(info,"fiftyTwoWeekLow")
            o5.metric("52W Range", f"₹{wl:,.0f}–₹{wh:,.0f}" if wh and wl else "N/A")

            st.markdown("")
            if not hist.empty:
                st.plotly_chart(make_hist_chart(hist, TICKER), use_container_width=True)
            else:
                st.info("Historical data unavailable.")

            desc = safe_get(info, "longBusinessSummary")
            if desc:
                with st.expander("About the company"):
                    st.write(desc)

        # ── Valuation ─────────────────────────────────────────
        with val:
            st.markdown("#### Graham Number")
            if graham is None:
                st.warning("Graham Number unavailable — EPS or Book Value is negative/missing.")
            else:
                mos_pct  = (graham - price) / graham * 100
                is_under = price < graham

                if is_under:
                    st.success(f"✅ **Undervalued** — {mos_pct:.1f}% below Graham Number.")
                    st.balloons()
                else:
                    st.error(f"🔴 **Overvalued** — {abs(mos_pct):.1f}% above Graham Number.")

                v1, v2, v3 = st.columns(3)
                v1.metric("Current Price", _fmt(price))
                v2.metric("Graham Number", _fmt(graham),
                          delta=f"₹{abs(graham-price):,.0f} {'headroom' if is_under else 'excess'}",
                          delta_color="normal" if is_under else "inverse")
                v3.metric("Margin of Safety" if is_under else "Premium",
                          f"{abs(mos_pct):.1f}%",
                          delta_color="normal" if is_under else "inverse")

                gc, bc = st.columns(2)
                with gc:
                    st.plotly_chart(make_gauge(price, graham, "Price vs Graham Number"),
                                    use_container_width=True)
                with bc:
                    st.plotly_chart(make_bar_comp(
                        ["Current Price","Graham Number"], [price, graham],
                        ["#3b82f6","#22c55e" if is_under else "#ef4444"],
                        "Price vs Graham Number (₹)"), use_container_width=True)

                with st.expander("🧮 Formula"):
                    st.markdown(f"""
`Graham Number = √(22.5 × EPS × BVPS)`  
= √(22.5 × {eps:.2f} × {bvps:.2f}) = √{22.5*eps*bvps:,.0f} = **₹{graham:,.2f}**
""")

            st.divider()
            st.markdown("#### Key Ratios")
            r1,r2,r3,r4 = st.columns(4)
            pe  = ratios.get("P/E (Trailing)")
            pb  = ratios.get("P/B")
            roe = ratios.get("ROE (%)")
            rc  = ratios.get("ROIC (%)")
            de  = ratios.get("Debt / Equity")
            eg  = ratios.get("EPS Growth (%)")
            r1.metric("P/E (TTM)",   f"{pe:.1f}×" if pe else "N/A")
            r1.metric("P/E (Fwd)",   f"{ratios.get('P/E (Forward)'):.1f}×" if ratios.get('P/E (Forward)') else "N/A")
            r2.metric("P/B",         f"{pb:.2f}×" if pb else "N/A")
            r2.metric("EPS Growth",  f"{eg:+.1f}%" if eg is not None else "N/A")
            r3.metric("ROE",         f"{roe:.1f}%" if roe is not None else "N/A")
            r3.metric("ROIC",        f"{rc:.1f}%" if rc is not None else "N/A")
            r4.metric("Debt/Equity", f"{de:.2f}×" if de is not None else "N/A")
            r4.metric("Div Yield",   f"{ratios.get('Dividend Yield (%)') or 0:.2f}%" )

        # ── DCF ───────────────────────────────────────────────
        with dcf_tab:
            st.markdown("#### 3-Stage DCF Valuation")

            # Fallback FCF → EPS
            if not fcf_ps or fcf_ps <= 0:
                if eps and eps > 0:
                    fcf_ps = eps
                    st.info(f"FCF data unavailable — using Trailing EPS (₹{eps:.2f}) as FCF proxy.")
                else:
                    fcf_ps = 1.0
                    st.warning("No FCF or EPS data. Defaulting FCF to ₹1. Please adjust manually.")

            d1, d2, d3 = st.columns(3)
            with d1:
                fcf_in = st.number_input("Base FCF/Share (₹)", 0.01, 50000.0,
                                          float(round(fcf_ps, 2)), 1.0)
                g1p = st.slider("Stage 1 Growth %", 0, 50, 20)
                yr1 = st.slider("Stage 1 Years",    1, 10,  5)
            with d2:
                g2p = st.slider("Stage 2 End Growth %", 0, 20, 10)
                yr2 = st.slider("Stage 2 Years",        1, 10,  5)
                gTp = st.slider("Terminal Growth %",    1, 10,  4)
            with d3:
                wp  = st.slider("WACC %", 5, 25, int(round(wacc*100)),
                                 help=f"Auto-estimated: {wacc*100:.1f}% (β={beta:.2f})")
                st.markdown(f"**WACC estimate:** {wacc*100:.1f}%  \n"
                             f"Rf=7.2%, ERP=7%, β={beta:.2f}")

            g1,g2,gT,w = g1p/100, g2p/100, gTp/100, wp/100
            res = calculate_dcf(fcf_in, g1, yr1, g2, yr2, gT, w)

            if not res:
                st.error("WACC must exceed terminal growth rate.")
            else:
                iv = res["intrinsic_value"]
                dp = (iv - price) / iv * 100
                du = price < iv
                if du:
                    st.success(f"✅ DCF Intrinsic Value **₹{iv:,.0f}** vs Price ₹{price:,.0f}  |  MoS {abs(dp):.1f}%")
                else:
                    st.error(f"🔴 DCF Intrinsic Value **₹{iv:,.0f}** vs Price ₹{price:,.0f}  |  Premium {abs(dp):.1f}%")

                dc1,dc2,dc3,dc4 = st.columns(4)
                dc1.metric("Intrinsic Value", _fmt(iv))
                dc2.metric("PV Stage 1",      _fmt(res["pv_stage1"]))
                dc3.metric("PV Stage 2",      _fmt(res["pv_stage2"]))
                dc4.metric("PV Terminal",     _fmt(res["pv_terminal"]))

                ch1,ch2 = st.columns(2)
                with ch1: st.plotly_chart(make_dcf_waterfall(res), use_container_width=True)
                with ch2: st.plotly_chart(make_gauge(price, iv, "Price vs DCF Value"),
                                           use_container_width=True)

                with st.expander("📋 Year-by-year cash flows"):
                    rows = [{"Year":yr,"Nominal FCF":f"₹{f:,.2f}","PV":f"₹{pv:,.2f}"}
                            for yr,f,pv in res["stage_cashflows"]]
                    rows.append({"Year":"Terminal","Nominal FCF":f"₹{res['terminal_value']:,.2f}",
                                 "PV":f"₹{res['pv_terminal']:,.2f}"})
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Sensitivity ───────────────────────────────────────
        with sens:
            st.markdown("#### Sensitivity Analysis — DCF vs WACC & Terminal Growth")
            if not res:
                st.warning("Complete the DCF tab first.")
            else:
                base_w = wp / 100
                w_range = [round(base_w - 0.03 + i*0.01, 3) for i in range(7)]
                w_range = [x for x in w_range if 0.05 <= x <= 0.25]
                g_range = [round(0.02 + i*0.01, 2) for i in range(6)]

                with st.spinner("Computing …"):
                    sdf = run_sensitivity(fcf_in, g1, yr1, g2, yr2, w_range, g_range)

                st.plotly_chart(make_sensitivity_heatmap(sdf, price), use_container_width=True)

                fmt_df = sdf.copy()
                for col in fmt_df.columns:
                    fmt_df[col] = fmt_df[col].apply(lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—")
                st.dataframe(fmt_df, use_container_width=True)
    else:
        st.info("Select a stock and click **Analyse** to begin.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — PORTFOLIO BUILDER
# ═══════════════════════════════════════════════════════════════════════════
with tab_portfolio:
    st.markdown("### Portfolio Builder")
    st.caption(
        "Build a hypothetical equal-weight portfolio from screener results.  "
        "Run the Screener first, then add stocks via the Screener tab — or search below."
    )

    # Allow manual add directly in portfolio tab too
    if st.session_state.screener_df is not None:
        df_scr = st.session_state.screener_df
        all_names = df_scr["Company"].tolist()
        current_in_portfolio = [r["Company"] for r in st.session_state.portfolio_rows]

        manual_add = st.multiselect(
            "Add stocks from screener",
            options=[n for n in all_names if n not in current_in_portfolio],
            max_selections=10,
        )
        if manual_add and st.button("➕ Add to Portfolio", type="secondary"):
            existing = {r["Company"] for r in st.session_state.portfolio_rows}
            for lbl in manual_add:
                match = df_scr[df_scr["Company"] == lbl]
                if not match.empty and lbl not in existing:
                    st.session_state.portfolio_rows.append(match.iloc[0].to_dict())
            st.rerun()
    else:
        st.info("Run the Screener tab first to enable stock selection.")

    # ── Remove stocks ─────────────────────────────────────────
    if st.session_state.portfolio_rows:
        remove_names = st.multiselect(
            "Remove stocks from portfolio",
            options=[r["Company"] for r in st.session_state.portfolio_rows],
        )
        if remove_names and st.button("🗑️ Remove Selected", type="secondary"):
            st.session_state.portfolio_rows = [
                r for r in st.session_state.portfolio_rows
                if r["Company"] not in remove_names
            ]
            st.rerun()

    if not st.session_state.portfolio_rows:
        st.info("Your portfolio is empty. Add stocks from the Screener tab.")
    else:
        port_df  = build_portfolio(st.session_state.portfolio_rows)
        metrics  = compute_portfolio_metrics(port_df)

        st.divider()
        st.markdown("#### Portfolio Metrics")

        pm1,pm2,pm3,pm4,pm5 = st.columns(5)
        pm1.metric("Stocks", metrics["n_stocks"])
        pm2.metric("Avg Score", f"{metrics['avg_score']:.1f}/100")
        pm3.metric("Avg MoS", f"{metrics['avg_mos']:+.1f}%")
        pm4.metric("Avg Beta",  f"{metrics['avg_beta']:.2f}")
        pm5.metric("Risk Level", metrics["risk_level"])

        roe_v = metrics.get("avg_roe")
        dq_v  = metrics.get("avg_data_quality")
        pm_x1, pm_x2 = st.columns(2)
        if roe_v: pm_x1.metric("Avg ROE", f"{roe_v:.1f}%")
        if dq_v:  pm_x2.metric("Avg Data Quality", f"{int(dq_v)}/100")

        st.markdown("")

        # ── Holdings table ────────────────────────────────────
        st.markdown("#### Holdings")
        disp_cols = ["Ticker","Company","Price (₹)","Weight (%)","Score","Signal","MoS (%)","ROE (%)","Beta"]
        st.dataframe(port_df[[c for c in disp_cols if c in port_df.columns]],
                     use_container_width=True, hide_index=True)

        st.markdown("")

        # ── Allocation pie ────────────────────────────────────
        pie_col, bar_col = st.columns(2)
        with pie_col:
            pie = go.Figure(go.Pie(
                labels=port_df["Company"].str[:20].tolist(),
                values=port_df["Weight (%)"].tolist(),
                hole=0.45, textinfo="label+percent",
            ))
            pie.update_layout(title="Portfolio Allocation", height=340,
                               margin={"t":60,"b":10,"l":10,"r":10}, showlegend=False)
            st.plotly_chart(pie, use_container_width=True)

        with bar_col:
            # Score comparison bar
            sc_bar = go.Figure(go.Bar(
                x=port_df["Company"].str[:20].tolist(),
                y=port_df["Score"].tolist(),
                marker_color=[
                    "#16a34a" if s == "STRONG BUY" else
                    "#4ade80" if s == "BUY" else
                    "#ca8a04" if s == "HOLD" else "#dc2626"
                    for s in port_df["Signal"].tolist()
                ],
                text=port_df["Score"].tolist(), textposition="outside",
            ))
            sc_bar.update_layout(title="Value Score by Holding", height=340,
                                  yaxis_range=[0,110], yaxis_title="Score",
                                  margin={"t":60,"b":30,"l":10,"r":10},
                                  xaxis_tickangle=-30)
            st.plotly_chart(sc_bar, use_container_width=True)

        # ── Signal distribution ───────────────────────────────
        sc_counts = metrics.get("signal_counts", {})
        if sc_counts:
            sig_order = ["STRONG BUY","BUY","HOLD","AVOID"]
            sig_cols  = st.columns(len(sig_order))
            sig_emoji = {"STRONG BUY":"🟢","BUY":"🟩","HOLD":"🟡","AVOID":"🔴"}
            for col, sig in zip(sig_cols, sig_order):
                count = sc_counts.get(sig, 0)
                col.metric(f"{sig_emoji[sig]} {sig}", count)

        st.markdown("")

        # ── Per-stock explanations ────────────────────────────
        with st.expander("📝 Investment Rationale — All Holdings"):
            for _, row in port_df.iterrows():
                st.markdown(f"**{row['Company']}** (`{row['Ticker']}`)"
                            f" — Score: {row['Score']}/100 · {row['Signal']}")
                st.markdown(row.get("Explanation",""))
                st.divider()

        # ── Export ────────────────────────────────────────────
        st.download_button(
            "⬇️ Download Portfolio (CSV)",
            data=portfolio_to_csv(port_df),
            file_name="portfolio.csv",
            mime="text/csv",
        )


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚠️ **Disclaimer:** For educational purposes only — not financial advice.  "
    "All valuations are model-based estimates. Consult a qualified financial adviser "
    "before making any investment decisions."
)
st.markdown(
    "<div style='text-align:center;color:#64748b;font-size:0.82rem;padding-top:8px'>"
    "Created by <strong>Dhruv Vaniawala</strong> · "
    "<a href='mailto:uwddhruv@gmail.com' style='color:#64748b'>uwddhruv@gmail.com</a>"
    "</div>",
    unsafe_allow_html=True,
)
