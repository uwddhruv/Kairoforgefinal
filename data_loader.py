"""
data_loader.py
--------------
Data-fetching layer with Streamlit caching and parallel batch support.

Public API
----------
fetch_stock_data(ticker)                    -> dict
fetch_price_history(ticker, period)         -> pd.DataFrame
batch_fetch_stocks(tickers, max_workers, progress_cb) -> dict[str, dict]
safe_get(info, key, default)               -> any
"""

import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st
import yfinance as yf


# ─────────────────────────────────────────────────────────────
# INDIVIDUAL FETCH  (cached 5 minutes)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(ticker: str) -> dict:
    """Fetch fundamental data (.info dict) for a single NSE ticker.

    Results are cached for 5 minutes so repeated lookups are instant.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker, e.g. ``"RELIANCE.NS"``.

    Returns
    -------
    dict
        The raw yfinance ``.info`` dictionary, or ``{}`` on failure.
    """
    try:
        info = yf.Ticker(ticker).info
        if not info:
            return {}
        # A valid ticker always has at least one price field
        has_price = (
            info.get("currentPrice") is not None
            or info.get("regularMarketPrice") is not None
        )
        return info if has_price else {}
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch OHLCV history for a ticker.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker.
    period : str
        yfinance period string — ``"5y"``, ``"1y"``, ``"6mo"`` etc.

    Returns
    -------
    pd.DataFrame
        OHLCV DataFrame indexed by date, or empty DataFrame on failure.
    """
    try:
        hist = yf.Ticker(ticker).history(period=period)
        return hist if not hist.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────
# BATCH FETCH  (parallel, uses individual cached calls)
# ─────────────────────────────────────────────────────────────

def batch_fetch_stocks(
    tickers: list[str],
    max_workers: int = 15,
    progress_cb=None,
) -> dict[str, dict]:
    """Fetch .info dicts for many tickers in parallel using a thread pool.

    Each individual fetch is still cached via ``fetch_stock_data``, so
    stocks already in cache return immediately without hitting the network.

    Parameters
    ----------
    tickers : list[str]
        List of Yahoo Finance ticker symbols.
    max_workers : int
        Maximum concurrent threads (default 15).
    progress_cb : callable | None
        Optional callback called after each completed fetch.
        Signature: ``progress_cb(completed: int, total: int, ticker: str)``

    Returns
    -------
    dict[str, dict]
        Mapping of ticker → info dict.  Tickers that failed are omitted.
    """
    results: dict[str, dict] = {}
    total = len(tickers)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_stock_data, t): t for t in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                info = future.result()
                if info:
                    results[ticker] = info
            except Exception:
                pass
            completed += 1
            if progress_cb is not None:
                progress_cb(completed, total, ticker)

    return results


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def safe_get(info: dict, key: str, default=None):
    """Return ``info[key]`` if present and finite, else ``default``.

    Parameters
    ----------
    info : dict
        yfinance ``.info`` dict.
    key : str
        Field name.
    default : any
        Fallback value when field is absent, None, NaN, or ±Inf.
    """
    val = info.get(key)
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
    except (TypeError, ValueError):
        pass
    return val
