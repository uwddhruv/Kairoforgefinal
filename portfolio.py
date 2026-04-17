"""
portfolio.py
------------
Portfolio simulation and analytics.

Public API
----------
build_portfolio(selected_rows)           -> pd.DataFrame
compute_portfolio_metrics(portfolio_df)  -> dict
portfolio_to_csv(portfolio_df)           -> str   (CSV string)
"""

import io
import pandas as pd


# ─────────────────────────────────────────────────────────────
# BUILD  — equal-weight portfolio from screener rows
# ─────────────────────────────────────────────────────────────

def build_portfolio(selected_rows: list[dict]) -> pd.DataFrame:
    """Create an equal-weight hypothetical portfolio from screener results.

    Each stock receives an equal allocation (1/N of portfolio).

    Parameters
    ----------
    selected_rows : list[dict]
        List of row dicts from the screener DataFrame (one per stock).

    Returns
    -------
    pd.DataFrame
        Portfolio table with columns:
        Ticker, Company, Price, Weight (%), Score, Signal, MoS %, ROE (%), Beta.
    """
    if not selected_rows:
        return pd.DataFrame()

    n      = len(selected_rows)
    weight = round(100 / n, 2)

    rows = []
    for r in selected_rows:
        rows.append({
            "Ticker":      r.get("Ticker", ""),
            "Company":     r.get("Company", ""),
            "Price (₹)":   r.get("Price (₹)"),
            "Weight (%)":  weight,
            "Score":       r.get("Score", 0),
            "Signal":      r.get("Signal", ""),
            "MoS (%)":     r.get("MoS %", 0),
            "ROE (%)":     r.get("ROE (%)", None),
            "Beta":        r.get("Beta", 1.0),
            "Data Quality":r.get("Data Quality", 0),
            "Explanation": r.get("Explanation", ""),
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# METRICS  — portfolio-level summary
# ─────────────────────────────────────────────────────────────

def compute_portfolio_metrics(portfolio_df: pd.DataFrame) -> dict:
    """Compute aggregate metrics for a portfolio DataFrame.

    Parameters
    ----------
    portfolio_df : pd.DataFrame
        Output of ``build_portfolio()``.

    Returns
    -------
    dict with keys:
        avg_score, avg_mos, avg_beta, avg_roe, avg_data_quality,
        risk_level, risk_color, signal_counts, n_stocks.
    """
    if portfolio_df.empty:
        return {}

    n   = len(portfolio_df)
    avg = lambda col: portfolio_df[col].dropna().mean()

    avg_score = avg("Score")
    avg_mos   = avg("MoS (%)")
    avg_beta  = avg("Beta")
    avg_roe   = avg("ROE (%)") if "ROE (%)" in portfolio_df.columns else None
    avg_dq    = avg("Data Quality")

    # Risk classification based on avg beta
    if avg_beta < 0.8:
        risk_level = "LOW"
        risk_color = "#16a34a"
    elif avg_beta < 1.2:
        risk_level = "MEDIUM"
        risk_color = "#ca8a04"
    else:
        risk_level = "HIGH"
        risk_color = "#dc2626"

    signal_counts = portfolio_df["Signal"].value_counts().to_dict()

    return {
        "avg_score":       round(avg_score, 1),
        "avg_mos":         round(avg_mos, 1),
        "avg_beta":        round(avg_beta, 2),
        "avg_roe":         round(avg_roe, 1) if avg_roe is not None else None,
        "avg_data_quality":round(avg_dq, 0),
        "risk_level":      risk_level,
        "risk_color":      risk_color,
        "signal_counts":   signal_counts,
        "n_stocks":        n,
    }


# ─────────────────────────────────────────────────────────────
# EXPORT — CSV string for st.download_button
# ─────────────────────────────────────────────────────────────

def portfolio_to_csv(portfolio_df: pd.DataFrame) -> str:
    """Serialise the portfolio DataFrame to a UTF-8 CSV string.

    Parameters
    ----------
    portfolio_df : pd.DataFrame
        Output of ``build_portfolio()``.

    Returns
    -------
    str
        CSV content as a string (use with ``st.download_button``).
    """
    buf = io.StringIO()
    portfolio_df.to_csv(buf, index=False)
    return buf.getvalue()


def screener_to_csv(screener_df: pd.DataFrame) -> str:
    """Serialise screener results to a UTF-8 CSV string.

    Parameters
    ----------
    screener_df : pd.DataFrame
        Output of ``run_screener()``.

    Returns
    -------
    str
        CSV content (use with ``st.download_button``).
    """
    # Drop internal columns not useful for external export
    export_cols = [
        "Rank", "Ticker", "Company", "Price (₹)", "Graham No.", "MoS %",
        "ROE (%)", "P/E", "D/E", "Beta", "Score", "Signal", "Data Quality",
    ]
    cols = [c for c in export_cols if c in screener_df.columns]
    buf  = io.StringIO()
    screener_df[cols].to_csv(buf, index=False)
    return buf.getvalue()
