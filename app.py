# ============================================================
# Graham Number Stock Analyser — Indian Stocks (NSE format)
# ============================================================
# Benjamin Graham's formula helps value investors decide whether
# a stock is trading below its intrinsic (fair) value.
#
# Formula: Graham Number = sqrt(22.5 × EPS × BVPS)
#   - 22.5 = 15 (max P/E) × 1.5 (max P/B) — Graham's own rule
#   - EPS  = Earnings Per Share (trailing twelve months)
#   - BVPS = Book Value Per Share
#
# If Current Price < Graham Number → stock is UNDERVALUED
# If Current Price > Graham Number → stock is OVERVALUED
# ============================================================

import math          # Used for math.sqrt() to compute the Graham Number
import streamlit as st  # Streamlit — turns this script into an interactive web app
import yfinance as yf   # yfinance — downloads stock data from Yahoo Finance
import pandas as pd     # pandas — used to build and display the summary table

# ── Page configuration ───────────────────────────────────────
# st.set_page_config() must be the first Streamlit call in the script.
# It sets the browser tab title and the layout width.
st.set_page_config(
    page_title="Graham Number Analyser",  # Text shown on the browser tab
    layout="centered"                     # Keep everything in a centred column
)

# ── App title & description ──────────────────────────────────
st.title("Graham Number Stock Analyser")   # Large heading shown at the top of the page

st.markdown(
    """
    Enter an **NSE-listed Indian stock ticker** (e.g. `RELIANCE.NS`, `TCS.NS`, `INFY.NS`)
    to calculate its **Graham Number** — a measure of intrinsic value developed by
    Benjamin Graham, the father of value investing.

    **Formula:** `Graham Number = √(22.5 × EPS × Book Value Per Share)`
    """
)

# ── Horizontal rule for visual separation ───────────────────
st.divider()

# ── Ticker input ─────────────────────────────────────────────
# st.text_input() renders a single-line text box.
# The user types the NSE ticker here (Yahoo Finance format adds ".NS" suffix).
ticker_input = st.text_input(
    label="Stock Ticker (NSE format)",   # Label shown above the text box
    placeholder="e.g. RELIANCE.NS",      # Greyed-out hint inside the box
    help="Use the Yahoo Finance format: TICKER.NS — e.g. TCS.NS, HDFC.NS, INFY.NS"
)

# ── Analyse button ───────────────────────────────────────────
# st.button() renders a clickable button.
# All analysis logic runs only when the button is clicked (returns True).
analyse_clicked = st.button("Analyse Stock", type="primary")

# ── Main logic block ─────────────────────────────────────────
# We only run the analysis when the user has typed something AND clicked the button.
if analyse_clicked and ticker_input.strip():

    # ticker_input.strip() removes any accidental leading/trailing spaces
    ticker_symbol = ticker_input.strip().upper()   # Also upper-case for consistency

    # Show a spinner with a status message while data is being fetched.
    # Everything indented inside "with st.spinner()" runs while the spinner is visible.
    with st.spinner(f"Fetching data for **{ticker_symbol}** …"):

        # ── Download stock information from Yahoo Finance ────
        # yf.Ticker() creates a Ticker object for the given symbol.
        # The object exposes .info — a dictionary with dozens of financial fields.
        stock = yf.Ticker(ticker_symbol)

        # .info returns a plain Python dict; we fetch it once to reuse below.
        info = stock.info

    # ── Extract the three values we need ────────────────────
    # dict.get(key, default) returns the value for 'key' if it exists,
    # otherwise it returns the default.  We use None as the default so we
    # can detect missing data explicitly.

    current_price = info.get("currentPrice")          # Latest market price (₹)
    eps           = info.get("trailingEps")           # EPS for the last 12 months (₹)
    bvps          = info.get("bookValue")             # Book value per share (₹)
    company_name  = info.get("longName", ticker_symbol)  # Human-readable company name

    # ── Validate that all three values exist and are usable ─
    # Graham Number requires EPS > 0 and BVPS > 0.
    # A negative or zero value would make the square root invalid.
    missing = []   # Collect names of any missing fields

    if current_price is None:
        missing.append("Current Price")
    if eps is None:
        missing.append("EPS (trailing)")
    if bvps is None:
        missing.append("Book Value Per Share")

    if missing:
        # st.error() shows a red error banner
        st.error(
            f"Could not retrieve the following data for **{ticker_symbol}**: "
            f"{', '.join(missing)}.\n\n"
            "Please check that the ticker is correct (e.g. `RELIANCE.NS`) "
            "and that the company has published earnings."
        )

    elif eps <= 0 or bvps <= 0:
        # Graham's formula only works for profitable companies with positive book value.
        st.warning(
            f"**{company_name}** has a negative or zero EPS ({eps}) "
            f"or Book Value ({bvps}). "
            "The Graham Number cannot be calculated for loss-making companies."
        )

    else:
        # ── All values are present and positive — compute! ──

        # Graham Number = square root of (22.5 × EPS × BVPS)
        # 22.5 comes from Graham's rule: P/E ≤ 15  and  P/B ≤ 1.5
        #                                15 × 1.5 = 22.5
        graham_number = math.sqrt(22.5 * eps * bvps)

        # ── Valuation verdict ────────────────────────────────
        # Compare the current market price to the Graham Number.
        # If price is below Graham Number, the stock may be undervalued.
        if current_price < graham_number:
            # margin_of_safety = how much cheaper the stock is vs Graham Number (%)
            margin_of_safety = ((graham_number - current_price) / graham_number) * 100
            verdict          = "Undervalued"
            verdict_detail   = (
                f"The stock is trading **{margin_of_safety:.1f}% below** its Graham Number. "
                "It may offer a margin of safety for value investors."
            )
        else:
            # premium = how much more expensive the stock is vs Graham Number (%)
            premium        = ((current_price - graham_number) / graham_number) * 100
            verdict        = "Overvalued"
            verdict_detail = (
                f"The stock is trading **{premium:.1f}% above** its Graham Number. "
                "It may be priced above its intrinsic value."
            )

        # ── Display company name & verdict ───────────────────
        st.subheader(company_name)   # Show company name as a section heading

        # Choose colour: green for undervalued, red for overvalued
        if verdict == "Undervalued":
            st.success(f"Verdict: **{verdict}**  —  {verdict_detail}")
        else:
            st.error(f"Verdict: **{verdict}**  —  {verdict_detail}")

        # ── Summary table ────────────────────────────────────
        # Build a pandas DataFrame with one row per metric.
        # DataFrames display as nicely formatted HTML tables in Streamlit.

        summary_data = {
            "Metric": [
                "Current Market Price (₹)",
                "EPS — Trailing Twelve Months (₹)",
                "Book Value Per Share (₹)",
                "Graham Number (₹)",
                "Valuation Verdict"
            ],
            "Value": [
                f"₹ {current_price:,.2f}",        # Format with commas & 2 decimal places
                f"₹ {eps:,.2f}",
                f"₹ {bvps:,.2f}",
                f"₹ {graham_number:,.2f}",
                verdict                            # "Undervalued" or "Overvalued"
            ]
        }

        # pd.DataFrame() converts the dict into a table.
        # Keys become column names; list values become rows.
        df = pd.DataFrame(summary_data)

        # st.dataframe() renders the DataFrame as an interactive HTML table.
        # hide_index=True removes the default 0, 1, 2 … row numbers on the left.
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ── Formula breakdown ─────────────────────────────────
        # Show users the exact numbers that went into the calculation.
        st.markdown("#### Formula Breakdown")
        st.markdown(
            f"Graham Number = √(22.5 × EPS × BVPS)  \n"
            f"= √(22.5 × {eps:.2f} × {bvps:.2f})  \n"
            f"= √({22.5 * eps * bvps:,.2f})  \n"
            f"= **₹ {graham_number:,.2f}**"
        )

        # ── Disclaimer ───────────────────────────────────────
        st.divider()
        st.caption(
            "⚠️ This tool is for educational purposes only and does not constitute "
            "financial advice. Always do your own research before making any "
            "investment decisions."
        )

elif analyse_clicked and not ticker_input.strip():
    # User clicked the button without typing anything
    st.warning("Please enter a stock ticker before clicking Analyse.")
