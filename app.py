# ============================================================
# Graham Number Stock Analyser — Indian Stocks (NSE format)
# ============================================================
# Benjamin Graham's formula:  Graham Number = √(22.5 × EPS × BVPS)
#   EPS  = Earnings Per Share (trailing 12 months)
#   BVPS = Book Value Per Share
#   22.5 = 15 (max P/E Graham allowed) × 1.5 (max P/B Graham allowed)
#
# Price < Graham Number → potentially UNDERVALUED (good for value investors)
# Price > Graham Number → potentially OVERVALUED  (trading above fair value)
# ============================================================

import math                    # math.sqrt() for the Graham Number formula
import streamlit as st         # Main web framework — turns Python into a web app
import yfinance as yf          # Fetches live stock data from Yahoo Finance
import pandas as pd            # DataFrames for table display
import plotly.graph_objects as go  # Interactive charts

# ─────────────────────────────────────────────────────────────
# PAGE CONFIGURATION  (must be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Graham Number Analyser",
    page_icon="📈",
    layout="wide"       # "wide" uses the full browser width for a dashboard feel
)

# ─────────────────────────────────────────────────────────────
# MASTER STOCK LIST
# Each entry: "Company Name — TICKER.NS"
# st.selectbox() lets the user type to filter this list (built-in autocomplete).
# ─────────────────────────────────────────────────────────────
STOCKS = {
    # Format:  "Display label": "TICKER.NS"
    "Reliance Industries": "RELIANCE.NS",
    "Tata Consultancy Services (TCS)": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Hindustan Unilever (HUL)": "HINDUNILVR.NS",
    "State Bank of India (SBI)": "SBIN.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro (L&T)": "LT.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Axis Bank": "AXISBANK.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Maruti Suzuki": "MARUTI.NS",
    "HCL Technologies": "HCLTECH.NS",
    "Sun Pharmaceutical": "SUNPHARMA.NS",
    "Wipro": "WIPRO.NS",
    "UltraTech Cement": "ULTRACEMCO.NS",
    "Titan Company": "TITAN.NS",
    "Nestle India": "NESTLEIND.NS",
    "Power Grid Corporation": "POWERGRID.NS",
    "NTPC": "NTPC.NS",
    "Mahindra & Mahindra (M&M)": "M&M.NS",
    "Tech Mahindra": "TECHM.NS",
    "Bajaj Auto": "BAJAJ-AUTO.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Dr. Reddy's Laboratories": "DRREDDY.NS",
    "Cipla": "CIPLA.NS",
    "Adani Ports": "ADANIPORTS.NS",
    "Adani Enterprises": "ADANIENT.NS",
    "Adani Green Energy": "ADANIGREEN.NS",
    "Adani Power": "ADANIPOWER.NS",
    "Coal India": "COALINDIA.NS",
    "ONGC": "ONGC.NS",
    "Indian Oil Corporation (IOC)": "IOC.NS",
    "Bharat Petroleum (BPCL)": "BPCL.NS",
    "Hindustan Petroleum (HPCL)": "HPCL.NS",
    "Tata Steel": "TATASTEEL.NS",
    "JSW Steel": "JSWSTEEL.NS",
    "Hindalco Industries": "HINDALCO.NS",
    "Vedanta": "VEDL.NS",
    "Grasim Industries": "GRASIM.NS",
    "Shree Cement": "SHREECEM.NS",
    "ACC": "ACC.NS",
    "Ambuja Cements": "AMBUJACEM.NS",
    "Pidilite Industries": "PIDILITIND.NS",
    "Godrej Consumer Products": "GODREJCP.NS",
    "Dabur India": "DABUR.NS",
    "Marico": "MARICO.NS",
    "Colgate-Palmolive India": "COLPAL.NS",
    "Havells India": "HAVELLS.NS",
    "Voltas": "VOLTAS.NS",
    "Crompton Greaves Consumer": "CROMPTON.NS",
    "Dixon Technologies": "DIXON.NS",
    "Tata Power": "TATAPOWER.NS",
    "Torrent Power": "TORNTPOWER.NS",
    "NHPC": "NHPC.NS",
    "Indraprastha Gas (IGL)": "IGL.NS",
    "Petronet LNG": "PETRONET.NS",
    "Gail India": "GAIL.NS",
    "Hero MotoCorp": "HEROMOTOCO.NS",
    "Eicher Motors (Royal Enfield)": "EICHERMOT.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "HDFC Life Insurance": "HDFCLIFE.NS",
    "SBI Life Insurance": "SBILIFE.NS",
    "ICICI Prudential Life": "ICICIPRULI.NS",
    "LIC of India": "LICI.NS",
    "Muthoot Finance": "MUTHOOTFIN.NS",
    "Cholamandalam Finance": "CHOLAFIN.NS",
    "Shriram Finance": "SHRIRAMFIN.NS",
    "SBI Cards": "SBICARD.NS",
    "HDFC AMC": "HDFCAMC.NS",
    "Nippon India AMC (NAM India)": "NAM-INDIA.NS",
    "Divi's Laboratories": "DIVISLAB.NS",
    "Biocon": "BIOCON.NS",
    "Apollo Hospitals": "APOLLOHOSP.NS",
    "Max Healthcare": "MAXHEALTH.NS",
    "Fortis Healthcare": "FORTIS.NS",
    "Lupin": "LUPIN.NS",
    "Aurobindo Pharma": "AUROPHARMA.NS",
    "Zydus Lifesciences": "ZYDUSLIFE.NS",
    "Abbott India": "ABBOTINDIA.NS",
    "Tata Consumer Products": "TATACONSUM.NS",
    "United Spirits (Diageo India)": "UNITDSPR.NS",
    "VBL (Varun Beverages)": "VBL.NS",
    "Zomato": "ZOMATO.NS",
    "Swiggy": "SWIGGY.NS",
    "Nykaa (FSN E-Commerce)": "NYKAA.NS",
    "PB Fintech (Policybazaar)": "POLICYBZR.NS",
    "One97 (Paytm)": "PAYTM.NS",
    "Delhivery": "DELHIVERY.NS",
    "InterGlobe Aviation (IndiGo)": "INDIGO.NS",
    "SpiceJet": "SPICEJET.NS",
    "Indian Railway Finance (IRFC)": "IRFC.NS",
    "Rail Vikas Nigam (RVNL)": "RVNL.NS",
    "IRCTC": "IRCTC.NS",
    "Bharat Electronics (BEL)": "BEL.NS",
    "HAL (Hindustan Aeronautics)": "HAL.NS",
    "Bharat Dynamics (BDL)": "BDL.NS",
    "Mazagon Dock": "MAZDOCK.NS",
    "NHPC": "NHPC.NS",
    "Tata Elxsi": "TATAELXSI.NS",
    "Persistent Systems": "PERSISTENT.NS",
    "Mphasis": "MPHASIS.NS",
    "LTIMindtree": "LTIM.NS",
    "Coforge": "COFORGE.NS",
    "Zensar Technologies": "ZENSARTECH.NS",
    "Oracle Financial Services (OFSS)": "OFSS.NS",
    "Hindustan Zinc": "HINDZINC.NS",
    "National Aluminium (NALCO)": "NATIONALUM.NS",
    "NMDC": "NMDC.NS",
    "Motherson Sumi Wiring": "MSUMI.NS",
    "Samvardhana Motherson (SAMIL)": "MOTHERSON.NS",
    "Bosch India": "BOSCHLTD.NS",
    "MRF Tyres": "MRF.NS",
    "Apollo Tyres": "APOLLOTYRE.NS",
    "CEAT Tyres": "CEATLTD.NS",
    "Page Industries (Jockey)": "PAGEIND.NS",
    "Trent (Westside / Zudio)": "TRENT.NS",
    "Avenue Supermarts (DMart)": "DMART.NS",
    "Jubilant Foodworks (Domino's)": "JUBLFOOD.NS",
    "Restaurant Brands (Burger King)": "RBA.NS",
    "Westlife Foodworld (McDonald's)": "WESTLIFE.NS",
    "Info Edge (Naukri / 99acres)": "NAUKRI.NS",
    "Just Dial": "JUSTDIAL.NS",
    "Indiamart Intermesh": "INDIAMART.NS",
    "Newgen Software": "NEWGEN.NS",
    "Tanla Platforms": "TANLA.NS",
}

# Sort the display labels alphabetically so the dropdown is easy to scan
SORTED_LABELS = sorted(STOCKS.keys())

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
# Two-column layout: big title on the left, info badge on the right
col_title, col_badge = st.columns([3, 1])

with col_title:
    # st.markdown with HTML lets us style the title more richly
    st.markdown("## 📈 Graham Number Stock Analyser")
    st.markdown(
        "Discover whether an Indian stock is **undervalued** or **overvalued** "
        "using Benjamin Graham's classic formula — the bedrock of value investing."
    )

with col_badge:
    # A small info box explaining the formula at a glance
    st.info("**Formula**\n\n√(22.5 × EPS × Book Value)", icon="🧮")

st.divider()

# ─────────────────────────────────────────────────────────────
# STOCK SELECTION  (autocomplete dropdown)
# ─────────────────────────────────────────────────────────────
# st.columns() divides the row into proportional-width columns.
# [3, 1] means the left column is 3× wider than the right column.
col_select, col_custom = st.columns([3, 1])

with col_select:
    # st.selectbox() renders a dropdown. When the user starts typing,
    # Streamlit filters the list in real time — this IS the autocomplete behaviour.
    chosen_label = st.selectbox(
        label="🔍 Search & select a stock",
        options=["— choose a company —"] + SORTED_LABELS,   # First item is the placeholder
        index=0,                                              # Start with the placeholder selected
        help="Start typing the company name to filter the list instantly."
    )

with col_custom:
    # Optional manual override for stocks not in the list
    custom_ticker = st.text_input(
        label="Or type a ticker",
        placeholder="e.g. ZOMATO.NS",
        help="Not in the list? Type the NSE ticker directly (format: SYMBOL.NS)"
    )

# Determine the final ticker symbol to use:
# Custom text input takes priority over the dropdown selection.
if custom_ticker.strip():
    # The user typed their own ticker — use that (upper-cased for Yahoo Finance)
    ticker_symbol = custom_ticker.strip().upper()
    display_source = f"Custom: {ticker_symbol}"
elif chosen_label != "— choose a company —":
    # The user picked from the dropdown — look up its ticker in our dictionary
    ticker_symbol = STOCKS[chosen_label]
    display_source = chosen_label
else:
    # Nothing selected yet
    ticker_symbol = None
    display_source = None

# ─────────────────────────────────────────────────────────────
# ANALYSE BUTTON
# ─────────────────────────────────────────────────────────────
# Centre the button using a column trick
_, col_btn, _ = st.columns([2, 1, 2])    # Three columns: left spacer, button, right spacer
with col_btn:
    analyse_clicked = st.button(
        "Analyse Stock 🚀",
        type="primary",
        use_container_width=True   # Button stretches to fill its column
    )

st.divider()

# ─────────────────────────────────────────────────────────────
# ANALYSIS  — runs only when the button is clicked and a stock is chosen
# ─────────────────────────────────────────────────────────────
if analyse_clicked:

    if ticker_symbol is None:
        # Nothing was selected — nudge the user
        st.warning("Please select a stock from the dropdown or type a ticker symbol.")

    else:
        # ── Fetch data from Yahoo Finance ────────────────────
        # st.spinner() shows an animated loading indicator while data is being downloaded.
        with st.spinner(f"Fetching live data for **{display_source}** …"):
            stock = yf.Ticker(ticker_symbol)    # Create a Ticker object for this symbol
            info  = stock.info                  # .info is a dict with all financial fields

        # ── Pull the three key values ────────────────────────
        current_price = info.get("currentPrice")      # Latest traded price (₹)
        eps           = info.get("trailingEps")        # Earnings Per Share — last 12 months (₹)
        bvps          = info.get("bookValue")          # Book Value Per Share (₹)
        company_name  = info.get("longName", ticker_symbol)  # Full company name

        # Additional colour for the header badge
        sector        = info.get("sector", "")
        industry      = info.get("industry", "")

        # ── Validation ───────────────────────────────────────
        missing = []
        if current_price is None: missing.append("Current Price")
        if eps           is None: missing.append("EPS (trailing)")
        if bvps          is None: missing.append("Book Value Per Share")

        if missing:
            st.error(
                f"⚠️ Could not retrieve: **{', '.join(missing)}** for `{ticker_symbol}`.\n\n"
                "Check the ticker is correct and the company has published financials."
            )

        elif eps <= 0 or bvps <= 0:
            st.warning(
                f"**{company_name}** reports negative EPS ({eps:.2f}) or "
                f"negative Book Value ({bvps:.2f}). "
                "Graham's formula requires a profitable company — skipping calculation."
            )

        else:
            # ── Calculate the Graham Number ──────────────────
            # The formula: √(22.5 × EPS × BVPS)
            graham_number = math.sqrt(22.5 * eps * bvps)

            # ── Determine valuation verdict ──────────────────
            if current_price < graham_number:
                # Stock price is BELOW intrinsic value — possibly a bargain
                pct_diff         = ((graham_number - current_price) / graham_number) * 100
                verdict          = "Undervalued"
                verdict_emoji    = "✅"
                verdict_colour   = "green"
                verdict_detail   = (
                    f"Trading **{pct_diff:.1f}% below** the Graham Number — "
                    "may offer a margin of safety for value investors."
                )
            else:
                # Stock price is ABOVE intrinsic value — possibly expensive
                pct_diff         = ((current_price - graham_number) / graham_number) * 100
                verdict          = "Overvalued"
                verdict_emoji    = "🔴"
                verdict_colour   = "red"
                verdict_detail   = (
                    f"Trading **{pct_diff:.1f}% above** the Graham Number — "
                    "may be priced above its intrinsic value."
                )

            # ─────────────────────────────────────────────────
            # RESULT HEADER
            # ─────────────────────────────────────────────────
            st.markdown(f"### {verdict_emoji} {company_name}")
            if sector:
                st.caption(f"{sector}  ·  {industry}  ·  `{ticker_symbol}`")

            # Verdict banner — green for undervalued, red for overvalued
            if verdict == "Undervalued":
                st.success(f"**Verdict: {verdict}** — {verdict_detail}")
                st.balloons()   # Celebratory animation for a good finding!
            else:
                st.error(f"**Verdict: {verdict}** — {verdict_detail}")

            st.markdown("")   # Breathing room

            # ─────────────────────────────────────────────────
            # METRIC CARDS (three side-by-side KPI boxes)
            # st.metric() displays a big number with an optional delta indicator.
            # ─────────────────────────────────────────────────
            m1, m2, m3 = st.columns(3)    # Three equal-width columns

            with m1:
                # Current market price — no delta (it is the reference)
                st.metric(
                    label="📊 Current Market Price",
                    value=f"₹ {current_price:,.2f}"
                )

            with m2:
                # Graham Number — show the gap vs current price as delta
                delta_value = graham_number - current_price   # positive = above price
                st.metric(
                    label="🧮 Graham Number",
                    value=f"₹ {graham_number:,.2f}",
                    # delta shows the difference; delta_color inverts meaning:
                    #   "inverse" makes a positive delta GREEN (good — gap means undervalued)
                    delta=f"₹ {abs(delta_value):,.2f} {'above price' if delta_value > 0 else 'below price'}",
                    delta_color="inverse" if verdict == "Overvalued" else "normal"
                )

            with m3:
                # Margin of safety / premium percentage
                label_text = "🛡️ Margin of Safety" if verdict == "Undervalued" else "📛 Premium to Fair Value"
                st.metric(
                    label=label_text,
                    value=f"{pct_diff:.1f}%",
                    # Positive margin = undervalued = good → normal (green)
                    # Positive premium = overvalued = bad → inverse (red)
                    delta="vs Graham Number",
                    delta_color="normal" if verdict == "Undervalued" else "inverse"
                )

            st.markdown("")

            # ─────────────────────────────────────────────────
            # VISUAL GAUGE — how far is the price from fair value?
            # We use a Plotly bullet / gauge chart.
            # ─────────────────────────────────────────────────
            # Gauge range: from 0 to (2 × higher of the two values)
            # Current price pointer vs Graham Number reference line
            max_range = max(current_price, graham_number) * 1.6   # 60% headroom

            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=current_price,          # The needle points at current price
                number={"prefix": "₹", "valueformat": ",.0f"},   # Format the number
                delta={
                    "reference": graham_number,   # Delta compared against Graham Number
                    "prefix": "₹",
                    "valueformat": ",.0f",
                    "increasing": {"color": "red"},    # Price rising above GN is bad
                    "decreasing": {"color": "green"}   # Price falling below GN is good
                },
                title={"text": "Current Price vs Graham Number", "font": {"size": 16}},
                gauge={
                    "axis": {
                        "range": [0, max_range],
                        "tickformat": "₹,.0f",
                        "tickfont": {"size": 11}
                    },
                    # Colour the gauge arc:
                    #   0 → Graham Number → green zone (undervalued territory)
                    #   Graham Number → max → red zone (overvalued territory)
                    "steps": [
                        {"range": [0, graham_number], "color": "rgba(0,200,100,0.15)"},
                        {"range": [graham_number, max_range], "color": "rgba(255,80,80,0.15)"}
                    ],
                    # A bold line at the Graham Number (fair value boundary)
                    "threshold": {
                        "line": {"color": "darkblue", "width": 3},
                        "thickness": 0.85,
                        "value": graham_number
                    },
                    "bar": {"color": "steelblue", "thickness": 0.3}
                }
            ))
            # Remove extra whitespace around the gauge
            gauge_fig.update_layout(
                height=280,
                margin={"t": 50, "b": 20, "l": 30, "r": 30}
            )
            # st.plotly_chart() renders any Plotly figure interactively
            st.plotly_chart(gauge_fig, use_container_width=True)

            # ─────────────────────────────────────────────────
            # BAR CHART — Current Price vs Graham Number side by side
            # ─────────────────────────────────────────────────
            bar_fig = go.Figure()

            # Bar 1: Current Market Price
            bar_fig.add_trace(go.Bar(
                name="Current Market Price",
                x=["Valuation Comparison"],
                y=[current_price],
                marker_color="steelblue",
                text=[f"₹ {current_price:,.2f}"],   # Label on the bar
                textposition="outside"
            ))

            # Bar 2: Graham Number (fair value)
            bar_fig.add_trace(go.Bar(
                name="Graham Number (Fair Value)",
                x=["Valuation Comparison"],
                y=[graham_number],
                marker_color="mediumseagreen" if verdict == "Undervalued" else "tomato",
                text=[f"₹ {graham_number:,.2f}"],
                textposition="outside"
            ))

            bar_fig.update_layout(
                title="Current Price vs Graham Number",
                barmode="group",       # Side-by-side bars (not stacked)
                yaxis_title="Price (₹)",
                legend_title="Legend",
                height=350,
                margin={"t": 50, "b": 20, "l": 20, "r": 20},
                yaxis_tickprefix="₹",
                yaxis_tickformat=","
            )
            st.plotly_chart(bar_fig, use_container_width=True)

            # ─────────────────────────────────────────────────
            # SUMMARY TABLE
            # ─────────────────────────────────────────────────
            st.markdown("#### 📋 Summary")

            # Build the summary as a pandas DataFrame for clean table rendering
            summary_df = pd.DataFrame({
                "Metric": [
                    "Current Market Price",
                    "EPS — Trailing 12 Months",
                    "Book Value Per Share",
                    "Graham Number (Fair Value)",
                    "Valuation Verdict"
                ],
                "Value": [
                    f"₹ {current_price:,.2f}",
                    f"₹ {eps:,.2f}",
                    f"₹ {bvps:,.2f}",
                    f"₹ {graham_number:,.2f}",
                    f"{verdict_emoji} {verdict}"
                ]
            })

            # Render as a non-editable, full-width table without row numbers
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

            # ─────────────────────────────────────────────────
            # FORMULA BREAKDOWN (inside an expander — keeps it tidy)
            # st.expander() hides content until the user clicks to expand it.
            # ─────────────────────────────────────────────────
            with st.expander("🧮 Show formula step-by-step"):
                st.markdown(
                    f"""
**Graham Number = √(22.5 × EPS × Book Value Per Share)**

| Step | Calculation | Result |
|------|-------------|--------|
| EPS | Trailing twelve months | **₹ {eps:,.2f}** |
| Book Value Per Share | From balance sheet | **₹ {bvps:,.2f}** |
| 22.5 × EPS × BVPS | {22.5} × {eps:.2f} × {bvps:.2f} | **{22.5 * eps * bvps:,.2f}** |
| Graham Number | √({22.5 * eps * bvps:,.2f}) | **₹ {graham_number:,.2f}** |
| Current Price | Live market price | **₹ {current_price:,.2f}** |
| Verdict | Price {'<' if current_price < graham_number else '>'} Graham Number | **{verdict}** |

> **Why 22.5?** Benjamin Graham set a rule: never pay more than 15× earnings (P/E) 
> or 1.5× book value (P/B). Multiply those limits together: 15 × 1.5 = **22.5**.
                    """
                )

            # ─────────────────────────────────────────────────
            # DISCLAIMER
            # ─────────────────────────────────────────────────
            st.divider()
            st.caption(
                "⚠️ For educational purposes only. Not financial advice. "
                "The Graham Number is one tool among many — always do your own research "
                "and consult a qualified financial adviser before investing."
            )
