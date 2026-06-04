"""
valuation_models.py
-------------------
Pure financial calculation functions — zero Streamlit dependencies.

Functions
---------
calculate_graham(eps, bvps)
calculate_ratios(info)
estimate_wacc(info)
calculate_dcf(fcf, g1, yr1, g2, yr2, gT, wacc)
run_sensitivity(fcf, g1, yr1, g2, yr2, wacc_range, terminal_range)
"""

import math
import pandas as pd
from data_loader import safe_get


# ─────────────────────────────────────────────────────────────
# GRAHAM NUMBER
# ─────────────────────────────────────────────────────────────

def calculate_graham(eps: float | None, bvps: float | None) -> float | None:
    """Compute the Benjamin Graham Number: √(22.5 × EPS × BVPS).

    Graham's rule: never pay more than 15× earnings (P/E) or 1.5× book
    value (P/B).  Multiplying those limits gives the constant 22.5.

    Parameters
    ----------
    eps : float | None
        Trailing-twelve-month earnings per share (₹).
    bvps : float | None
        Book value per share (₹).

    Returns
    -------
    float | None
        Graham Number in ₹, or None if inputs are invalid/negative.
    """
    if eps is None or bvps is None:
        return None
    if eps <= 0 or bvps <= 0:
        return None
    return math.sqrt(22.5 * eps * bvps)


# ─────────────────────────────────────────────────────────────
# RATIO ANALYSIS
# ─────────────────────────────────────────────────────────────

def calculate_ratios(info: dict) -> dict:
    """Extract and compute key valuation & profitability ratios.

    Ratios returned
    ---------------
    P/E (Trailing), P/E (Forward), P/B,
    ROE (%), ROIC (%), Debt / Equity,
    EPS Growth (%), Dividend Yield (%)

    Parameters
    ----------
    info : dict
        Raw yfinance ``.info`` dictionary.

    Returns
    -------
    dict
        ``{ ratio_name: float | None }``  — None when data unavailable.
    """
    price     = safe_get(info, "currentPrice") or safe_get(info, "regularMarketPrice")
    eps_ttm   = safe_get(info, "trailingEps")
    eps_fwd   = safe_get(info, "forwardEps")
    bvps      = safe_get(info, "bookValue")
    roe       = safe_get(info, "returnOnEquity")      # decimal
    total_debt= safe_get(info, "totalDebt", 0) or 0
    total_cash= safe_get(info, "totalCash", 0) or 0
    shares    = safe_get(info, "sharesOutstanding")
    net_inc   = safe_get(info, "netIncomeToCommon")
    pe_ttm    = safe_get(info, "trailingPE")
    pe_fwd    = safe_get(info, "forwardPE")
    pb        = safe_get(info, "priceToBook")
    div_yield = safe_get(info, "dividendYield")

    # P/E (trailing)
    if pe_ttm is None and price and eps_ttm and eps_ttm > 0:
        pe_ttm = price / eps_ttm

    # P/E (forward)
    if pe_fwd is None and price and eps_fwd and eps_fwd > 0:
        pe_fwd = price / eps_fwd

    # P/B
    if pb is None and price and bvps and bvps > 0:
        pb = price / bvps

    # ROE %
    roe_pct = roe * 100 if roe is not None else None

    # ROIC = Net Income / Invested Capital
    roic_pct = None
    if net_inc and shares and bvps and shares > 0 and bvps > 0:
        equity = bvps * shares
        inv_cap = equity + total_debt - total_cash
        if inv_cap > 0:
            roic_pct = (net_inc / inv_cap) * 100

    # Debt / Equity
    de = None
    if shares and bvps and bvps > 0 and shares > 0:
        equity = bvps * shares
        if equity > 0:
            de = total_debt / equity

    # EPS growth (TTM → Forward, 1-yr proxy)
    eps_growth = None
    if eps_ttm and eps_fwd and eps_ttm > 0:
        eps_growth = ((eps_fwd / eps_ttm) - 1) * 100

    # Dividend yield %
    div_pct = div_yield * 100 if div_yield else None

    def _r(v, d=2):
        return round(v, d) if v is not None else None

    return {
        "P/E (Trailing)":     _r(pe_ttm),
        "P/E (Forward)":      _r(pe_fwd),
        "P/B":                _r(pb),
        "ROE (%)":            _r(roe_pct),
        "ROIC (%)":           _r(roic_pct),
        "Debt / Equity":      _r(de),
        "EPS Growth (%)":     _r(eps_growth),
        "Dividend Yield (%)": _r(div_pct),
    }


# ─────────────────────────────────────────────────────────────
# WACC ESTIMATION
# ─────────────────────────────────────────────────────────────

def estimate_wacc(info: dict) -> float:
    """Estimate WACC using CAPM + simplified debt cost.

    Uses India 10Y Gsec (~7.2%) as risk-free rate and
    Damodaran's ERP for India (~7%).

    Parameters
    ----------
    info : dict
        yfinance ``.info`` dict.

    Returns
    -------
    float
        WACC as a decimal (e.g. 0.12 = 12 %).
    """
    RF, ERP, TAX = 0.072, 0.070, 0.25
    beta       = max(0.5, min(safe_get(info, "beta", 1.0) or 1.0, 2.5))
    ke         = RF + beta * ERP
    kd         = 0.08 * (1 - TAX)
    market_cap = safe_get(info, "marketCap") or 0
    total_debt = safe_get(info, "totalDebt", 0) or 0

    if market_cap > 0:
        V    = market_cap + total_debt
        wacc = ke * (market_cap / V) + kd * (total_debt / V)
    else:
        wacc = ke

    return round(wacc, 4)


# ─────────────────────────────────────────────────────────────
# DCF  (3-stage)
# ─────────────────────────────────────────────────────────────

def calculate_dcf(
    fcf_per_share:   float,
    growth_stage1:   float,
    years_stage1:    int,
    growth_stage2:   float,
    years_stage2:    int,
    terminal_growth: float,
    wacc:            float,
) -> dict:
    """Three-stage Discounted Cash Flow valuation per share.

    Stage 1 — High Growth   : FCF grows at ``growth_stage1`` for ``years_stage1`` yrs.
    Stage 2 — Transition    : Growth declines linearly to ``terminal_growth``.
    Stage 3 — Terminal Value: Gordon Growth Model perpetuity.

    Parameters
    ----------
    fcf_per_share : float   Base FCF/share (₹).
    growth_stage1 : float   Stage-1 growth rate (decimal).
    years_stage1  : int     Stage-1 years.
    growth_stage2 : float   Ending growth of Stage-2 transition (decimal).
    years_stage2  : int     Stage-2 years.
    terminal_growth: float  Perpetuity growth rate (decimal).
    wacc          : float   Discount rate (decimal).

    Returns
    -------
    dict  Keys: intrinsic_value, pv_stage1, pv_stage2, pv_terminal,
                terminal_value, stage_cashflows.
          Empty dict if WACC ≤ terminal_growth.
    """
    if wacc <= terminal_growth or fcf_per_share <= 0:
        return {}

    cashflows, fcf = [], fcf_per_share
    pv1 = pv2 = 0.0

    for yr in range(1, years_stage1 + 1):
        fcf = fcf * (1 + growth_stage1)
        pv  = fcf / (1 + wacc) ** yr
        pv1 += pv
        cashflows.append((f"Y{yr}", fcf, pv))

    # Stage 2 — linearly interpolate from growth_stage1 DOWN to growth_stage2
    # (not terminal_growth, which is a separate perpetuity assumption)
    step = (growth_stage1 - growth_stage2) / max(years_stage2, 1)
    g_s2 = growth_stage1
    for i in range(1, years_stage2 + 1):
        g_s2 -= step
        yr   = years_stage1 + i
        fcf  = fcf * (1 + g_s2)
        pv   = fcf / (1 + wacc) ** yr
        pv2 += pv
        cashflows.append((f"Y{yr}", fcf, pv))

    total_yrs   = years_stage1 + years_stage2
    tv          = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_tv       = tv / (1 + wacc) ** total_yrs
    iv          = pv1 + pv2 + pv_tv

    return {
        "intrinsic_value": round(iv, 2),
        "pv_stage1":       round(pv1, 2),
        "pv_stage2":       round(pv2, 2),
        "pv_terminal":     round(pv_tv, 2),
        "terminal_value":  round(tv, 2),
        "stage_cashflows": cashflows,
    }


# ─────────────────────────────────────────────────────────────
# SENSITIVITY
# ─────────────────────────────────────────────────────────────

def run_sensitivity(
    fcf_per_share:  float,
    growth_stage1:  float,
    years_stage1:   int,
    growth_stage2:  float,
    years_stage2:   int,
    wacc_range:     list[float],
    terminal_range: list[float],
) -> pd.DataFrame:
    """Sensitivity table: DCF intrinsic value vs WACC and terminal growth.

    Rows = WACC values, Columns = terminal growth rates.
    Cell values = DCF intrinsic value per share (₹).
    """
    rows = {}
    for w in wacc_range:
        row = {}
        for g in terminal_range:
            col = f"{g*100:.1f}%"
            if w <= g:
                row[col] = float("nan")
            else:
                res = calculate_dcf(fcf_per_share, growth_stage1, years_stage1,
                                    growth_stage2, years_stage2, g, w)
                row[col] = res.get("intrinsic_value", float("nan"))
        rows[f"{w*100:.1f}%"] = row

    df = pd.DataFrame(rows).T
    df.index.name   = "WACC →"
    df.columns.name = "Terminal Growth →"
    return df
