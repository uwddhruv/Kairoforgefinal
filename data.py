"""
data.py
-------
Data-fetching layer.  All functions use Streamlit's @st.cache_data decorator
so that repeated requests for the same ticker reuse cached results (TTL = 5 min).

Public API
----------
fetch_stock_data(ticker)       -> dict  (yfinance .info)
fetch_price_history(ticker)    -> pd.DataFrame  (5-year OHLCV)
"""

import streamlit as st
import yfinance as yf
import pandas as pd


# ---------------------------------------------------------------------------
# fetch_stock_data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(ticker: str) -> dict:
    """Fetch fundamental data for a single NSE ticker from Yahoo Finance.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker symbol, e.g. ``"RELIANCE.NS"``.

    Returns
    -------
    dict
        The raw ``.info`` dictionary returned by yfinance.
        Returns an empty dict if the request fails or the ticker is invalid.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # Sanity check: a valid ticker always has at least a currentPrice or
        # regularMarketPrice.  An invalid ticker returns a near-empty dict.
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            return {}
        return info
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# fetch_price_history
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch OHLCV price history for a ticker.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker symbol.
    period : str
        yfinance period string — ``"5y"``, ``"1y"``, ``"6mo"``, etc.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns [Open, High, Low, Close, Volume].
        The index is a DatetimeIndex.  Returns an empty DataFrame on failure.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist if not hist.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# safe_get  (helper)
# ---------------------------------------------------------------------------
def safe_get(info: dict, key: str, default=None):
    """Return info[key] if present and not None/NaN, else default.

    Parameters
    ----------
    info : dict
        The .info dict from yfinance.
    key : str
        Field name to look up.
    default : any
        Value to return when the field is absent or falsy.
    """
    val = info.get(key)
    # yfinance sometimes returns "Infinity" or NaN floats
    if val is None:
        return default
    try:
        import math
        if math.isnan(float(val)) or math.isinf(float(val)):
            return default
    except (TypeError, ValueError):
        pass
    return val
