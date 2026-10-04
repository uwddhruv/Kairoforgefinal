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


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_statement_metrics(ticker: str) -> dict:
    """Fetch missing annual FCF and total-share-count values from Yahoo statements.

    Yahoo often omits ``freeCashflow`` from ``.info`` for NSE tickers while
    providing it on the annual cash-flow statement. If the statement has no
    FCF row, compute it only when both operating cash flow and capital
    expenditure are present for the same reporting period. Total shares fall
    back to reported shares outstanding in the balance sheet or Yahoo's share
    history; free-float shares are deliberately not used.
    """
    try:
        provider = yf.Ticker(ticker)
    except Exception:
        return {}
    try:
        frame = provider.cashflow
    except Exception:
        frame = pd.DataFrame()
    try:
        balance_sheet = provider.balance_sheet
    except Exception:
        balance_sheet = pd.DataFrame()

    def normalize(label) -> str:
        return "".join(char.lower() for char in str(label) if char.isalnum())

    def period_value(value):
        try:
            timestamp = pd.Timestamp(value)
            return -1 if pd.isna(timestamp) else timestamp.value
        except (TypeError, ValueError, OverflowError):
            return -1

    def period_label(value):
        try:
            timestamp = pd.Timestamp(value)
            return str(value) if pd.isna(timestamp) else timestamp.date().isoformat()
        except (TypeError, ValueError, OverflowError):
            return str(value)

    def ordered_columns(statement):
        if not isinstance(statement, pd.DataFrame) or statement.empty:
            return []
        return sorted(statement.columns, key=period_value, reverse=True)

    def statement_value(statement, row, column):
        if row is None:
            return None
        try:
            value = float(statement.loc[row, column])
        except (TypeError, ValueError, OverflowError, KeyError):
            return None
        return value if math.isfinite(value) else None

    result = {}

    if isinstance(frame, pd.DataFrame) and not frame.empty:
        row_lookup = {normalize(label): label for label in frame.index}
        fcf_row = row_lookup.get("freecashflow")
        operating_row = row_lookup.get("operatingcashflow")
        capex_row = (
            row_lookup.get("capitalexpenditurereported")
            or row_lookup.get("capitalexpenditure")
            or row_lookup.get("capitalexpenditures")
        )
        columns = ordered_columns(frame)

        if fcf_row is not None:
            for column in columns:
                value = statement_value(frame, fcf_row, column)
                if value is not None:
                    result.update(
                        value=value,
                        period=period_label(column),
                        source="Yahoo annual cash-flow statement",
                    )
                    break

        # CapEx is a cash outflow; subtract its absolute value regardless of
        # the sign convention Yahoo uses in the source statement.
        if "value" not in result and operating_row is not None and capex_row is not None:
            for column in columns:
                operating_cash = statement_value(frame, operating_row, column)
                capital_spend = statement_value(frame, capex_row, column)
                if operating_cash is not None and capital_spend is not None:
                    result.update(
                        value=operating_cash - abs(capital_spend),
                        period=period_label(column),
                        source="Calculated from operating cash flow less capital expenditure",
                    )
                    break

    # Prefer the newest dated reported total-share count. Never use floatShares:
    # it is only the tradable float and would inflate per-share cash flow.
    share_candidates = []
    if isinstance(balance_sheet, pd.DataFrame) and not balance_sheet.empty:
        balance_rows = {normalize(label): label for label in balance_sheet.index}
        share_row = (
            balance_rows.get("ordinarysharesnumber")
            or balance_rows.get("shareissued")
        )
        for column in ordered_columns(balance_sheet):
            shares = statement_value(balance_sheet, share_row, column)
            if shares is not None and shares > 0:
                share_candidates.append((
                    period_value(column), shares, period_label(column),
                    "Yahoo balance sheet",
                ))
                break

    try:
        share_history = provider.get_shares_full()
    except Exception:
        share_history = None
    if isinstance(share_history, pd.Series) and not share_history.empty:
        for date, raw_shares in sorted(
            share_history.items(), key=lambda item: period_value(item[0]), reverse=True
        ):
            try:
                shares = float(raw_shares)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(shares) and shares > 0:
                share_candidates.append((
                    period_value(date), shares, period_label(date),
                    "Yahoo share history",
                ))
                break

    if share_candidates:
        _, shares, share_period, share_source = max(
            share_candidates, key=lambda item: item[0]
        )
        result.update(
            shares_outstanding=shares,
            shares_period=share_period,
            shares_source=share_source,
        )

    return result


@st.cache_data(ttl=600, show_spinner=False)
def fetch_news(ticker: str) -> list[dict]:
    """Fetch recent news articles for a ticker via yfinance.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker, e.g. ``"RELIANCE.NS"``.

    Returns
    -------
    list[dict]
        Each item has keys: title, publisher, link, providerPublishTime.
        Returns empty list on failure or when no news is available.
    """
    try:
        raw = yf.Ticker(ticker).news or []
        if not isinstance(raw, (list, tuple)):
            return []

        out = []
        seen_titles = set()
        for raw_item in raw:
            if not isinstance(raw_item, dict):
                continue
            # yfinance may return content nested under a 'content' key.
            item = raw_item.get("content", raw_item)
            if not isinstance(item, dict):
                continue
            raw_title = item.get("title")
            title = raw_title.strip() if isinstance(raw_title, str) else ""
            if not title:
                continue

            normalized_title = " ".join(
                "".join(
                    char if char.isalnum() else " "
                    for char in title.casefold()
                ).split()
            )
            if normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)

            provider = item.get("provider")
            provider_name = (
                provider.get("displayName", "")
                if isinstance(provider, dict)
                else item.get("publisher", "")
            )
            canonical_url = item.get("canonicalUrl")
            link = (
                canonical_url.get("url", "")
                if isinstance(canonical_url, dict)
                else item.get("link", "")
            )
            out.append({
                "title":     title,
                "publisher": provider_name if isinstance(provider_name, str) else "",
                "link":      link if isinstance(link, str) else "",
                "time":      item.get("pubDate") or item.get("providerPublishTime"),
            })
        return out
    except Exception:
        return []


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
