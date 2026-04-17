"""
valuation.py
------------
Pure financial calculation functions — no Streamlit dependencies.

Functions
---------
calculate_graham(eps, bvps)                -> float | None
calculate_ratios(info)                     -> dict
estimate_wacc(info)                        -> float
calculate_dcf(fcf, g1, yr1, g2, yr2, gT, wacc) -> dict
run_sensitivity(fcf, g1, yr1, g2, yr2,
                wacc_range, terminal_range) -> pd.DataFrame
"""

import math
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# calculate_graham
# ---------------------------------------------------------------------------
def calculate_graham(eps: float, bvps: float) -> float | None:
    """Compute the Benjamin Graham Number.

    The Graham Number is a theoretical upper bound on the price a defensive
    investor should pay, derived from Graham's rule that P/E ≤ 15 and P/B ≤ 1.5.
    Multiplying the limits gives the constant 22.5 (15 × 1.5).

    Parameters
    ----------
    eps : float
        Trailing-twelve-month earnings per share.
    bvps : float
        Book value per share.

    Returns
    -------
    float | None
        Graham Number (₹), or None if inputs are invalid (negative/zero).
    """
    if eps is None or bvps is None:
        return None
    if eps <= 0 or bvps <= 0:
        return None
    return math.sqrt(22.5 * eps * bvps)


# ---------------------------------------------------------------------------
# calculate_ratios
# ---------------------------------------------------------------------------
def calculate_ratios(info: dict) -> dict:
    """Extract and compute key valuation and profitability ratios from yfinance info.

    Ratios computed
    ---------------
    - P/E  (Price / Trailing EPS)
    - Forward P/E  (Price / Forward EPS)
    - P/B  (Price / Book Value Per Share)
    - ROE  (Return on Equity, %)
    - ROIC (Return on Invested Capital, %)  — estimated from net income & invested capital
    - Debt / Equity
    - EPS Growth  (trailing EPS vs forward EPS annualised, %)
    - Dividend Yield (%)

    Parameters
    ----------
    info : dict
        Raw yfinance .info dictionary for a ticker.

    Returns
    -------
    dict
        Mapping of ratio name -> value (float or None).  None means the data
        was not available or could not be computed.
    """
    from data import safe_get

    price   = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    eps_ttm = safe_get(info, "trailingEps")
    eps_fwd = safe_get(info, "forwardEps")
    bvps    = safe_get(info, "bookValue")
    roe     = safe_get(info, "returnOnEquity")      # decimal (e.g. 0.18 = 18%)
    total_debt  = safe_get(info, "totalDebt", 0)
    total_cash  = safe_get(info, "totalCash", 0)
    shares      = safe_get(info, "sharesOutstanding")
    net_income  = safe_get(info, "netIncomeToCommon")
    pe_ttm      = safe_get(info, "trailingPE")
    pe_fwd      = safe_get(info, "forwardPE")
    pb          = safe_get(info, "priceToBook")
    div_yield   = safe_get(info, "dividendYield")   # decimal

    # -- P/E (trailing) — prefer yfinance value, fall back to manual calc
    if pe_ttm is None and price and eps_ttm and eps_ttm > 0:
        pe_ttm = price / eps_ttm

    # -- P/E (forward)
    if pe_fwd is None and price and eps_fwd and eps_fwd > 0:
        pe_fwd = price / eps_fwd

    # -- P/B
    if pb is None and price and bvps and bvps > 0:
        pb = price / bvps

    # -- ROE (convert from decimal to %)
    roe_pct = roe * 100 if roe is not None else None

    # -- ROIC  =  Net Income / Invested Capital
    #    Invested Capital ≈ Total Equity + Total Debt − Cash
    roic_pct = None
    if net_income and shares and bvps and shares > 0 and bvps > 0:
        total_equity    = bvps * shares
        invested_cap    = total_equity + (total_debt or 0) - (total_cash or 0)
        if invested_cap > 0:
            roic_pct = (net_income / invested_cap) * 100

    # -- Debt / Equity
    de_ratio = None
    if total_debt is not None and shares and bvps and bvps > 0 and shares > 0:
        equity = bvps * shares
        if equity > 0:
            de_ratio = total_debt / equity

    # -- EPS growth (TTM → Forward, annualised proxy)
    eps_growth = None
    if eps_ttm and eps_fwd and eps_ttm > 0:
        eps_growth = ((eps_fwd / eps_ttm) - 1) * 100

    # -- Dividend yield (%)
    div_yield_pct = div_yield * 100 if div_yield else None

    return {
        "P/E (Trailing)":   round(pe_ttm, 2)      if pe_ttm      is not None else None,
        "P/E (Forward)":    round(pe_fwd, 2)       if pe_fwd      is not None else None,
        "P/B":              round(pb, 2)            if pb          is not None else None,
        "ROE (%)":          round(roe_pct, 2)       if roe_pct     is not None else None,
        "ROIC (%)":         round(roic_pct, 2)      if roic_pct    is not None else None,
        "Debt / Equity":    round(de_ratio, 2)      if de_ratio    is not None else None,
        "EPS Growth (%)":   round(eps_growth, 2)    if eps_growth  is not None else None,
        "Dividend Yield (%)": round(div_yield_pct, 2) if div_yield_pct is not None else None,
    }


# ---------------------------------------------------------------------------
# estimate_wacc
# ---------------------------------------------------------------------------
def estimate_wacc(info: dict) -> float:
    """Estimate WACC using CAPM for equity with a simplified debt adjustment.

    Uses the Indian 10-year government bond yield (~7.2 %) as the risk-free rate
    and Damodaran's equity risk premium for India (~7 %).

    WACC = Ke × (E / V) + Kd × (1 - t) × (D / V)
    where Ke = Rf + β × ERP

    If any input is unavailable the function falls back gracefully.

    Parameters
    ----------
    info : dict
        Raw yfinance .info dictionary.

    Returns
    -------
    float
        Estimated WACC as a decimal (e.g. 0.12 = 12 %).
    """
    from data import safe_get

    RISK_FREE   = 0.072   # India 10Y Gsec yield (approx)
    ERP         = 0.070   # Equity Risk Premium for India (Damodaran)
    TAX_RATE    = 0.25    # Approximate corporate tax rate in India

    beta = safe_get(info, "beta", 1.0)
    beta = max(0.5, min(beta, 2.5))   # Clamp to a sane range

    # Cost of equity via CAPM
    ke = RISK_FREE + beta * ERP

    # Simple debt cost (assume 8% pre-tax cost of debt for Indian corporates)
    kd_pretax = 0.08
    kd        = kd_pretax * (1 - TAX_RATE)

    total_debt  = safe_get(info, "totalDebt", 0) or 0
    market_cap  = safe_get(info, "marketCap")

    if market_cap and market_cap > 0:
        V  = market_cap + total_debt
        we = market_cap / V
        wd = total_debt / V
        wacc = ke * we + kd * wd
    else:
        # Fallback: pure equity company
        wacc = ke

    return round(wacc, 4)


# ---------------------------------------------------------------------------
# calculate_dcf
# ---------------------------------------------------------------------------
def calculate_dcf(
    fcf_per_share:   float,
    growth_stage1:   float,   # Stage-1 annual growth rate (decimal)
    years_stage1:    int,     # Duration of Stage 1
    growth_stage2:   float,   # Stage-2 ending growth rate (decimal)
    years_stage2:    int,     # Duration of Stage 2 (transition)
    terminal_growth: float,   # Perpetuity growth rate (decimal)
    wacc:            float,   # Discount rate (decimal)
) -> dict:
    """Three-stage Discounted Cash Flow (DCF) valuation.

    Stage 1 — High Growth  : FCF grows at ``growth_stage1`` for ``years_stage1`` years.
    Stage 2 — Transition   : Growth rate declines linearly from ``growth_stage1``
                             to ``terminal_growth`` over ``years_stage2`` years.
    Stage 3 — Stable       : Terminal value via Gordon Growth Model.

    Parameters
    ----------
    fcf_per_share : float
        Base free-cash-flow per share (₹).
    growth_stage1 : float
        Annual FCF growth rate for Stage 1 (decimal, e.g. 0.20 for 20 %).
    years_stage1 : int
        Number of years in Stage 1.
    growth_stage2 : float
        Ending growth rate for Stage 2 / terminal transition (decimal).
    years_stage2 : int
        Number of years in Stage 2.
    terminal_growth : float
        Perpetuity growth rate for terminal value (decimal, e.g. 0.04).
    wacc : float
        Weighted Average Cost of Capital (decimal).

    Returns
    -------
    dict with keys:
        ``intrinsic_value``  — DCF fair value per share (₹)
        ``pv_stage1``        — PV of Stage-1 cash flows
        ``pv_stage2``        — PV of Stage-2 cash flows
        ``pv_terminal``      — PV of Terminal Value
        ``stage_cashflows``  — list of (year, fcf, pv) tuples for all explicit years
        ``terminal_value``   — raw (undiscounted) terminal value
    """
    if wacc <= terminal_growth:
        # Gordon Growth Model requires WACC > terminal growth
        return {}

    cashflows = []   # List of (year_label, nominal_fcf, pv)
    fcf = fcf_per_share
    pv_stage1 = 0.0
    pv_stage2 = 0.0

    # ── Stage 1: high growth ──────────────────────────────────
    for yr in range(1, years_stage1 + 1):
        fcf = fcf * (1 + growth_stage1)
        pv  = fcf / (1 + wacc) ** yr
        pv_stage1 += pv
        cashflows.append((f"Y{yr}", fcf, pv))

    # ── Stage 2: linear growth transition ────────────────────
    # Growth declines evenly from growth_stage1 → terminal_growth
    step = (growth_stage1 - terminal_growth) / max(years_stage2, 1)
    g2   = growth_stage1   # Start of Stage-2 growth
    for i in range(1, years_stage2 + 1):
        g2  -= step
        yr   = years_stage1 + i
        fcf  = fcf * (1 + g2)
        pv   = fcf / (1 + wacc) ** yr
        pv_stage2 += pv
        cashflows.append((f"Y{yr}", fcf, pv))

    # ── Stage 3: terminal value (Gordon Growth Model) ─────────
    total_years  = years_stage1 + years_stage2
    terminal_fcf = fcf * (1 + terminal_growth)   # First year of stable-growth FCF
    terminal_val = terminal_fcf / (wacc - terminal_growth)
    pv_terminal  = terminal_val / (1 + wacc) ** total_years

    intrinsic_value = pv_stage1 + pv_stage2 + pv_terminal

    return {
        "intrinsic_value": round(intrinsic_value, 2),
        "pv_stage1":       round(pv_stage1, 2),
        "pv_stage2":       round(pv_stage2, 2),
        "pv_terminal":     round(pv_terminal, 2),
        "terminal_value":  round(terminal_val, 2),
        "stage_cashflows": cashflows,
    }


# ---------------------------------------------------------------------------
# run_sensitivity
# ---------------------------------------------------------------------------
def run_sensitivity(
    fcf_per_share:   float,
    growth_stage1:   float,
    years_stage1:    int,
    growth_stage2:   float,
    years_stage2:    int,
    wacc_range:      list[float],     # e.g. [0.08, 0.09, …, 0.15]
    terminal_range:  list[float],     # e.g. [0.02, 0.03, …, 0.07]
) -> pd.DataFrame:
    """Generate a sensitivity table of DCF intrinsic values.

    Varies WACC (rows) and terminal growth rate (columns) to show how
    sensitive the DCF valuation is to these two key assumptions.

    Parameters
    ----------
    fcf_per_share : float
        Base FCF per share.
    growth_stage1 : float
        Stage-1 growth rate (held constant across the table).
    years_stage1 : int
        Stage-1 duration.
    growth_stage2 : float
        Stage-2 ending growth rate.
    years_stage2 : int
        Stage-2 duration.
    wacc_range : list[float]
        List of WACC values to iterate over (rows).
    terminal_range : list[float]
        List of terminal growth values to iterate over (columns).

    Returns
    -------
    pd.DataFrame
        Rows = WACC values, Columns = terminal growth rates.
        Cell values = DCF intrinsic value per share (₹).
    """
    rows = {}
    for w in wacc_range:
        row = {}
        for g in terminal_range:
            if w <= g:
                row[f"{g*100:.1f}%"] = float("nan")
                continue
            result = calculate_dcf(
                fcf_per_share, growth_stage1, years_stage1,
                growth_stage2, years_stage2, g, w
            )
            row[f"{g*100:.1f}%"] = result.get("intrinsic_value", float("nan"))
        rows[f"{w*100:.1f}%"] = row

    df = pd.DataFrame(rows).T   # WACC as rows, terminal growth as columns
    df.index.name   = "WACC →"
    df.columns.name = "Terminal Growth →"
    return df
