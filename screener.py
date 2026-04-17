"""
screener.py
-----------
Stock screening, scoring, signal generation, and explainability.

Public API
----------
data_quality_score(info)          -> dict
score_stock(ticker, name, info)   -> dict
generate_signal(score)            -> tuple[str, str, str]  (signal, emoji, css_color)
generate_explanation(data)        -> str
run_screener(stock_dict, progress_bar, status_text) -> pd.DataFrame
"""

import pandas as pd
from data_loader import safe_get, batch_fetch_stocks
from valuation_models import calculate_graham, calculate_ratios


# ─────────────────────────────────────────────────────────────
# DATA QUALITY SCORE  (0-100)
# ─────────────────────────────────────────────────────────────

def data_quality_score(info: dict) -> dict:
    """Rate the completeness of a stock's yfinance data.

    Each critical financial field awards points.  Missing or inconsistent
    data is penalised so the analyst knows how much to trust the valuation.

    Parameters
    ----------
    info : dict
        yfinance ``.info`` dictionary.

    Returns
    -------
    dict with keys ``score`` (int 0-100) and ``detail`` (dict field→bool).
    """
    checks = {
        "Current Price":  safe_get(info, "currentPrice") is not None
                          or safe_get(info, "regularMarketPrice") is not None,
        "EPS (Trailing)": safe_get(info, "trailingEps") is not None,
        "Book Value":     safe_get(info, "bookValue") is not None,
        "Free Cash Flow": safe_get(info, "freeCashflow") is not None,
        "ROE":            safe_get(info, "returnOnEquity") is not None,
        "Beta":           safe_get(info, "beta") is not None,
        "P/E Ratio":      safe_get(info, "trailingPE") is not None,
        "Market Cap":     safe_get(info, "marketCap") is not None,
    }
    weights = {
        "Current Price": 20, "EPS (Trailing)": 20, "Book Value": 15,
        "Free Cash Flow": 15, "ROE": 15, "Beta": 5, "P/E Ratio": 5,
        "Market Cap": 5,
    }
    score = sum(weights[k] for k, v in checks.items() if v)
    return {"score": score, "detail": checks}


# ─────────────────────────────────────────────────────────────
# VALUE OPPORTUNITY SCORE  (0-100)
# ─────────────────────────────────────────────────────────────

def score_stock(ticker: str, name: str, info: dict) -> dict:
    """Compute a composite Value Opportunity Score for a single stock.

    Scoring breakdown (total = 100 pts)
    ------------------------------------
    Graham MoS  — 40 pts  (how far below Graham Number the stock trades)
    ROE Quality — 25 pts  (management efficiency)
    P/E Score   — 20 pts  (earnings valuation)
    D/E Score   — 15 pts  (balance-sheet safety)

    Parameters
    ----------
    ticker : str    NSE ticker symbol, e.g. ``"RELIANCE.NS"``.
    name   : str    Human-readable company name.
    info   : dict   yfinance ``.info`` dictionary.

    Returns
    -------
    dict
        All inputs, scores, ratios, signal, and explanation fields.
    """
    price  = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    eps    = safe_get(info, "trailingEps")
    bvps   = safe_get(info, "bookValue")
    roe    = safe_get(info, "returnOnEquity")     # decimal
    beta   = safe_get(info, "beta", 1.0) or 1.0
    ratios = calculate_ratios(info)
    graham = calculate_graham(eps, bvps)
    dq     = data_quality_score(info)

    pe = ratios.get("P/E (Trailing)")
    de = ratios.get("Debt / Equity")

    # ── Graham MoS score (0-40) ───────────────────────────────
    mos_pct = 0.0
    if graham and price:
        mos_pct = (graham - price) / graham * 100   # + = undervalued

    if graham and price and mos_pct > 0:
        if mos_pct >= 40:   g_score = 40
        elif mos_pct >= 25: g_score = 30
        elif mos_pct >= 10: g_score = 20
        else:               g_score = 10
    else:
        g_score = 0   # overvalued by Graham

    # ── ROE quality (0-25) ───────────────────────────────────
    roe_pct = (roe or 0) * 100
    if roe and roe_pct >= 25:   r_score = 25
    elif roe and roe_pct >= 20: r_score = 20
    elif roe and roe_pct >= 15: r_score = 15
    elif roe and roe_pct >= 10: r_score = 10
    elif roe and roe_pct > 0:   r_score = 5
    else:                        r_score = 0

    # ── P/E score (0-20) ────────────────────────────────────
    if pe is None:              pe_score = 5   # neutral when unknown
    elif pe <= 0:               pe_score = 0
    elif pe <= 15:              pe_score = 20
    elif pe <= 25:              pe_score = 15
    elif pe <= 35:              pe_score = 10
    elif pe <= 50:              pe_score = 5
    else:                       pe_score = 0

    # ── D/E score (0-15) ────────────────────────────────────
    if de is None:              de_score = 10  # no debt info → neutral
    elif de <= 0.0:             de_score = 15  # debt-free
    elif de <= 0.5:             de_score = 13
    elif de <= 1.0:             de_score = 9
    elif de <= 2.0:             de_score = 5
    else:                       de_score = 0

    total_score = g_score + r_score + pe_score + de_score

    # ── Signal ───────────────────────────────────────────────
    signal, emoji, color = generate_signal(total_score)

    # ── Explanation ──────────────────────────────────────────
    explanation = generate_explanation({
        "name": name, "price": price, "graham": graham,
        "mos_pct": mos_pct, "roe_pct": roe_pct,
        "pe": pe, "de": de, "g_score": g_score,
        "r_score": r_score, "pe_score": pe_score,
        "total_score": total_score,
    })

    return {
        "Ticker":       ticker,
        "Company":      name,
        "Price (₹)":    round(price, 2) if price else None,
        "Graham No.":   round(graham, 2) if graham else None,
        "MoS %":        round(mos_pct, 1),
        "ROE (%)":      round(roe_pct, 1) if roe else None,
        "P/E":          round(pe, 1) if pe else None,
        "D/E":          round(de, 2) if de is not None else None,
        "Beta":         round(beta, 2),
        "Score":        total_score,
        "G-Score":      g_score,
        "ROE-Score":    r_score,
        "PE-Score":     pe_score,
        "DE-Score":     de_score,
        "Signal":       signal,
        "Signal Emoji": emoji,
        "Signal Color": color,
        "Data Quality": dq["score"],
        "Explanation":  explanation,
    }


# ─────────────────────────────────────────────────────────────
# SIGNAL GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_signal(score: float) -> tuple[str, str, str]:
    """Map a 0-100 Value Opportunity Score to an investment signal.

    Parameters
    ----------
    score : float
        Composite score from ``score_stock()``.

    Returns
    -------
    tuple[str, str, str]
        ``(signal_text, emoji, css_color_hex)``
    """
    if score >= 70:
        return "STRONG BUY", "🟢", "#16a34a"
    elif score >= 50:
        return "BUY",         "🟩", "#4ade80"
    elif score >= 30:
        return "HOLD",        "🟡", "#ca8a04"
    else:
        return "AVOID",       "🔴", "#dc2626"


# ─────────────────────────────────────────────────────────────
# EXPLANATION GENERATOR
# ─────────────────────────────────────────────────────────────

def generate_explanation(data: dict) -> str:
    """Generate a short, investor-friendly explanation for the valuation verdict.

    Identifies the dominant driver (Graham / ROE / P/E) and explains the
    key reason behind the signal in plain language.

    Parameters
    ----------
    data : dict
        Dict of scoring inputs/outputs from ``score_stock()``.

    Returns
    -------
    str
        1–3 sentence explanation suitable for a non-technical reader.
    """
    parts = []

    # Main driver
    scores = {
        "Graham valuation": data.get("g_score", 0),
        "ROE quality":      data.get("r_score", 0),
        "P/E ratio":        data.get("pe_score", 0),
    }
    driver = max(scores, key=scores.get)

    # Graham component
    mos = data.get("mos_pct", 0)
    graham = data.get("graham")
    price  = data.get("price")
    if graham and price:
        if mos > 0:
            parts.append(
                f"Trades {mos:.1f}% below its Graham Number (₹{graham:,.0f}), "
                f"offering a potential margin of safety."
            )
        else:
            parts.append(
                f"Trades {abs(mos):.1f}% above its Graham Number (₹{graham:,.0f}), "
                f"suggesting the price has baked in a premium."
            )

    # ROE component
    roe = data.get("roe_pct", 0)
    if roe and roe > 15:
        parts.append(f"Strong ROE of {roe:.1f}% indicates quality capital allocation.")
    elif roe and 5 < roe <= 15:
        parts.append(f"Moderate ROE of {roe:.1f}% — adequate but not exceptional.")
    elif roe is not None:
        parts.append(f"Weak ROE of {roe:.1f}% raises questions about profitability.")

    # P/E component
    pe = data.get("pe")
    if pe:
        if pe <= 15:
            parts.append(f"Low P/E of {pe:.1f}× is within Graham's comfort zone.")
        elif pe <= 30:
            parts.append(f"P/E of {pe:.1f}× implies a moderate growth premium.")
        else:
            parts.append(f"High P/E of {pe:.1f}× indicates significant growth expectations already priced in.")

    # Key driver highlight
    parts.append(f"Primary signal driver: **{driver}**.")

    return "  \n".join(parts)


# ─────────────────────────────────────────────────────────────
# SCREENER RUNNER
# ─────────────────────────────────────────────────────────────

def run_screener(
    stock_dict: dict[str, str],
    progress_bar=None,
    status_text=None,
) -> pd.DataFrame:
    """Screen all stocks in ``stock_dict`` and return a ranked DataFrame.

    Uses parallel fetching (via ``batch_fetch_stocks``) then scores each
    stock with ``score_stock()``.  Results are sorted by Score descending.

    Parameters
    ----------
    stock_dict : dict[str, str]
        ``{ "Company Name": "TICKER.NS" }`` mapping.
    progress_bar : st.delta_generator.DeltaGenerator | None
        Streamlit progress bar widget to update during fetch.
    status_text : st.delta_generator.DeltaGenerator | None
        Streamlit empty() widget for status messages.

    Returns
    -------
    pd.DataFrame
        Ranked screener results.  Empty DataFrame if all fetches fail.
    """
    tickers = list(stock_dict.values())
    label_map = {v: k for k, v in stock_dict.items()}   # ticker → name
    total = len(tickers)

    # Progress callback (safe — Streamlit widgets are updated from main thread)
    def _progress(done, tot, ticker):
        if progress_bar is not None:
            progress_bar.progress(done / tot)
        if status_text is not None:
            status_text.text(f"Analysing {done}/{tot} — {label_map.get(ticker, ticker)}")

    # Parallel fetch (individual results are cached by data_loader)
    info_map = batch_fetch_stocks(tickers, max_workers=15, progress_cb=_progress)

    # Score each stock that returned data
    rows = []
    for ticker, info in info_map.items():
        name = label_map.get(ticker, ticker)
        try:
            row = score_stock(ticker, name, info)
            rows.append(row)
        except Exception:
            pass   # Skip stocks that error during scoring

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df
