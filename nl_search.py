"""Natural Language Search for NSE stocks.

Parses free-text queries like "undervalued healthcare stocks with low pe and high roce"
into structured filter criteria, then runs the screener on matching stocks.
"""

from __future__ import annotations

import re
from typing import Any

from stocks import SECTOR_PEERS, INDUSTRY_PEERS, STOCKS

# ── Keyword lexicons ─────────────────────────────────────────────────────────

SECTOR_ALIASES: dict[str, list[str]] = {
    "technology":       ["tech", "it", "software", "digital", "infotech", "information technology"],
    "financial services": ["bank", "banks", "finance", "nbfc", "insurance", "fintech", "lending", "asset management"],
    "healthcare":       ["pharma", "pharmaceutical", "pharmaceuticals", "medicine", "drug", "hospital", "hospitals", "medical", "health", "biotech"],
    "consumer cyclical": ["auto", "automotive", "car", "vehicles", "retail", "fashion", "luxury", "apparel", "jewellery", "titan", "trent", "food service", "restaurant", "travel", "airline", "airlines"],
    "consumer defensive": ["fmcg", "consumer", "food", "beverage", "tobacco", "personal care", "household", "nestle", "itc", "hul", "hindustan unilever"],
    "energy":           ["oil", "gas", "petroleum", "coal", "mining", "energy"],
    "utilities":        ["power", "electric", "electricity", "renewable", "solar", "wind", "grid", "ntpc", "powergrid", "adani green"],
    "basic materials":  ["steel", "metal", "metals", "aluminium", "aluminum", "iron", "cement", "paint", "chemical", "grasim", "ultratech", "tata steel", "jsw steel"],
    "industrials":      ["infra", "infrastructure", "construction", "engineering", "defence", "defense", "aerospace", "logistics", "ports", "shipping", "lt", "larsen", "bel", "hal"],
    "communication services": ["telecom", "telecommunication", "internet", "media", "bharti", "airtel", "naukri", "nykaa"],
}

METRIC_ALIASES: dict[str, list[str]] = {
    "pe":       ["pe", "p/e", "price to earnings", "price-earnings", "valuation"],
    "pb":       ["pb", "p/b", "price to book", "price-book", "book value"],
    "roe":      ["roe", "return on equity", "return equity", "equity returns"],
    "roce":     ["roce", "return on capital employed", "capital returns"],
    "de":       ["de", "d/e", "debt", "debt to equity", "debt-equity", "leverage", "debt ratio"],
    "eps":      ["eps", "earnings per share", "earnings"],
    "growth":   ["growth", "revenue growth", "earnings growth", "profit growth", "cagr"],
    "dividend": ["dividend", "yield", "dividend yield", "payout"],
    "beta":     ["beta", "volatility", "risk"],
    "graham":   ["graham", "graham number", "margin of safety", "mos", "intrinsic value"],
    "score":    ["score", "value score", "opportunity score", "rating", "rank"],
}

# Qualifiers that can appear near a metric
# Each entry: { "_direction": "lt|gt" }
QUALIFIER_THRESHOLDS: dict[str, dict[str, Any]] = {
    "low":       {"_direction": "lt"},
    "high":      {"_direction": "gt"},
    "cheap":     {"_direction": "lt"},
    "expensive": {"_direction": "gt"},
    "strong":    {"_direction": "gt"},
    "weak":      {"_direction": "lt"},
    "good":      {"_direction": "gt"},
    "bad":       {"_direction": "lt"},
    "safe":      {"_direction": "lt"},
    "risky":     {"_direction": "gt"},
}

# Default thresholds per metric (metric_key -> {qualifier: threshold_value})
METRIC_DEFAULTS: dict[str, dict[str, Any]] = {
    "pe":       {"low": 15, "high": 25, "cheap": 15, "expensive": 30, "safe": 15, "risky": 30},
    "pb":       {"low": 2, "high": 3, "cheap": 2, "expensive": 4, "safe": 2, "risky": 4},
    "roe":      {"low": 0.10, "high": 0.15, "strong": 0.15, "weak": 0.10, "good": 0.15, "bad": 0.10},
    "roce":     {"low": 0.10, "high": 0.15, "strong": 0.15, "weak": 0.10, "good": 0.15, "bad": 0.10},
    "de":       {"low": 0.5, "high": 1.0, "safe": 0.5, "risky": 1.0},
    "eps":      {"low": 10, "high": 50, "strong": 50, "weak": 10},
    "growth":   {"low": 0.05, "high": 0.15, "strong": 0.15, "weak": 0.05, "good": 0.15, "bad": 0.05},
    "dividend": {"low": 0.01, "high": 0.02, "strong": 0.02, "weak": 0.01},
    "beta":     {"low": 0.8, "high": 1.2, "safe": 0.8, "risky": 1.2},
    "graham":   {"low": 0.3, "high": 0.5, "cheap": 0.3, "expensive": 0.5, "strong": 0.3},
    "score":    {"low": 40, "high": 60, "strong": 60, "weak": 40, "good": 60, "bad": 40},
}

# Broad qualifiers that apply to a predefined set of metrics
BROAD_QUALIFIERS: dict[str, dict[str, Any]] = {
    "undervalued": {
        "pe": {"op": "lt", "value": 15},
        "pb": {"op": "lt", "value": 2},
        "graham": {"op": "gt", "value": 0.3},
        "score": {"op": "gt", "value": 60},
    },
    "overvalued": {
        "pe": {"op": "gt", "value": 30},
        "pb": {"op": "gt", "value": 4},
        "graham": {"op": "lt", "value": 0.5},
    },
    "cheap": {
        "pe": {"op": "lt", "value": 15},
        "pb": {"op": "lt", "value": 2},
        "graham": {"op": "gt", "value": 0.3},
    },
    "expensive": {
        "pe": {"op": "gt", "value": 30},
        "pb": {"op": "gt", "value": 4},
        "graham": {"op": "lt", "value": 0.5},
    },
}

SIGNAL_WORDS: dict[str, list[str]] = {
    "strong_buy": ["strong buy", "must buy", "conviction buy", "best buy"],
    "buy":        ["buy", "accumulate", "add", "positive", "attractive"],
    "hold":       ["hold", "neutral", "fair", "average", "wait"],
    "avoid":      ["avoid", "sell", "reduce", "negative", "stay away", "skip"],
}


# ── Helpers ────────────────────────────────────────────────────────────────────────────────────

def _word_match(text: str, word: str) -> bool:
    """Check if word appears as a whole word in text (case-insensitive)."""
    pattern = r'\b' + re.escape(word.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))


def _find_qualifiers_near_metric(q: str, metric_alias: str) -> list[str]:
    """Find all qualifiers that appear within a window of words around the metric."""
    words = q.lower().split()
    metric_words = metric_alias.lower().split()
    qualifiers = list(QUALIFIER_THRESHOLDS.keys())
    found = []
    for i in range(len(words)):
        chunk = " ".join(words[i:i + len(metric_words)])
        if chunk == metric_alias.lower():
            window_start = max(0, i - 5)
            window_end = min(len(words), i + len(metric_words) + 5)
            for w in words[window_start:window_end]:
                if w in qualifiers and w not in found:
                    found.append(w)
    return found


# ── Query parsing ─────────────────────────────────────────────────────────────

def parse_nl_query(query: str) -> dict[str, Any]:
    """Parse a natural-language stock query into filter criteria.

    Returns
    -------
    dict
        {
            "sectors":   list of sector keys to filter,
            "tickers":   deduped list of ticker symbols (or None for all),
            "metrics":   dict of metric -> {"op": "lt|gt", "value": float},
            "signals":   list of signal keys (strong_buy, buy, hold, avoid),
            "explanation": human-readable summary of what was parsed,
        }
    """
    q = query.lower().strip()
    if not q:
        return {"sectors": [], "tickers": None, "metrics": {}, "signals": [], "explanation": "No query provided"}

    criteria: dict[str, Any] = {
        "sectors": [],
        "tickers": None,
        "metrics": {},
        "signals": [],
        "explanation": "",
    }
    matched_parts: list[str] = []

    # ── 1. Sector / Industry detection ────────────────────────────
    found_sectors = set()
    for sector, aliases in SECTOR_ALIASES.items():
        all_names = [sector] + aliases
        for name in all_names:
            if _word_match(q, name):
                found_sectors.add(sector)
                matched_parts.append(f"sector: {sector}")
                break
    criteria["sectors"] = list(found_sectors)

    # ── 2. Industry (yfinance string) detection ───────────────────
    found_industries = set()
    for industry, tickers in INDUSTRY_PEERS.items():
        industry_lower = industry.lower()
        if industry_lower in q:
            found_industries.add(industry)
            matched_parts.append(f"industry: {industry}")
        else:
            industry_words = [w for w in industry_lower.replace("-", " ").replace("&", " ").split() if len(w) > 3]
            if len(industry_words) >= 2:
                matches = sum(1 for w in industry_words if _word_match(q, w))
                if matches >= 2:
                    found_industries.add(industry)
                    matched_parts.append(f"industry: {industry}")

    # ── 3. Build ticker list from sectors + industries ────────────
    ticker_pool = set()
    if found_sectors:
        for s in found_sectors:
            if s in SECTOR_PEERS:
                ticker_pool.update(SECTOR_PEERS[s])
    if found_industries:
        for ind in found_industries:
            if ind in INDUSTRY_PEERS:
                ticker_pool.update(INDUSTRY_PEERS[ind])
    if ticker_pool:
        criteria["tickers"] = sorted(ticker_pool)
    else:
        criteria["tickers"] = list(STOCKS.values())

    # ── 4. Metric + qualifier detection (nearby pairing) ─────────────
    for metric_key, aliases in METRIC_ALIASES.items():
        for alias in aliases:
            if alias in q:
                nearby_quals = _find_qualifiers_near_metric(q, alias)
                for qual in nearby_quals:
                    defaults = METRIC_DEFAULTS.get(metric_key, {})
                    val = defaults.get(qual)
                    if val is not None:
                        direction = QUALIFIER_THRESHOLDS[qual]["_direction"]
                        criteria["metrics"][metric_key] = {"op": direction, "value": val}
                        matched_parts.append(f"{qual} {metric_key}")
                        break
                break

    # ── 5. Broad qualifiers (undervalued, overvalued, cheap, expensive)
    for broad_qual, broad_metrics in BROAD_QUALIFIERS.items():
        if _word_match(q, broad_qual):
            for m, rule in broad_metrics.items():
                if m not in criteria["metrics"]:
                    criteria["metrics"][m] = rule
            matched_parts.append(f"broad: {broad_qual}")

    # ── 6. Signal detection ──────────────────────────────────────
    for signal, phrases in SIGNAL_WORDS.items():
        for phrase in phrases:
            if phrase in q:
                if signal not in criteria["signals"]:
                    criteria["signals"].append(signal)
                matched_parts.append(f"signal: {signal}")
                break

    # ── 7. Build explanation ──────────────────────────────────────
    parts_desc = []
    if criteria["sectors"]:
        parts_desc.append(f"Sectors: {', '.join(criteria['sectors'])}")
    if criteria["metrics"]:
        metric_desc = []
        for m, rule in criteria["metrics"].items():
            op_str = "<" if rule["op"] == "lt" else ">"
            val = rule["value"]
            if isinstance(val, float) and val < 1:
                val_str = f"{val:.0%}"
            else:
                val_str = f"{val:.1f}" if isinstance(val, float) else str(val)
            metric_desc.append(f"{m.upper()} {op_str} {val_str}")
        parts_desc.append("Filters: " + "; ".join(metric_desc))
    if criteria["signals"]:
        parts_desc.append(f"Signals: {', '.join(s.replace('_', ' ').title() for s in criteria['signals'])}")
    if not parts_desc:
        parts_desc.append("No specific filters detected — showing all stocks by score")

    criteria["explanation"] = " | ".join(parts_desc)
    return criteria


# ── Filter execution ─────────────────────────────────────────────────────────────

def apply_nl_filters(stock_results: list[dict], criteria: dict[str, Any]) -> list[dict]:
    """Filter a list of scored stock dicts by parsed NL criteria.

    Each stock_results item is a dict from ``score_stock()`` with keys:
    ``Ticker``, ``Company``, ``Score``, ``Signal``, ``P/E``, ``D/E``, ``ROE (%)``, etc.
    """
    filtered = []
    metrics = criteria.get("metrics", {})
    signals = criteria.get("signals", [])

    for stock in stock_results:
        ok = True
        for metric, rule in metrics.items():
            val = _get_metric_value(stock, metric)
            if val is None:
                ok = False
                break
            op = rule["op"]
            threshold = rule["value"]
            if op == "lt" and not (val < threshold):
                ok = False
                break
            if op == "gt" and not (val > threshold):
                ok = False
                break

        if not ok:
            continue

        if signals:
            stock_signal = stock.get("Signal", "").lower().replace(" ", "_")
            if stock_signal not in signals:
                continue

        filtered.append(stock)

    filtered.sort(key=lambda x: x.get("Score", 0), reverse=True)
    return filtered


def _get_metric_value(stock: dict, metric: str) -> float | None:
    """Extract a normalized metric value from a stock dict."""
    mapping = {
        "pe": "P/E",
        "pb": "P/B",
        "roe": "ROE (%)",
        "roce": "ROIC (%)",
        "de": "D/E",
        "eps": "EPS",
        "growth": "EPS Growth (%)",
        "dividend": "Dividend Yield (%)",
        "beta": "Beta",
        "graham": "MoS %",
        "score": "Score",
    }
    key = mapping.get(metric, metric)
    val = stock.get(key)
    if val is None:
        return None
    if metric in ("roe", "roce", "growth", "dividend"):
        try:
            return float(val) / 100.0
        except (TypeError, ValueError):
            return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ── Quick test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_queries = [
        "undervalued healthcare stocks with low pe and high roce",
        "cheap pharma companies with strong ROE",
        "IT stocks with low debt",
        "banks with high dividend yield",
        "auto stocks to buy",
        "low risk FMCG stocks",
        "steel companies with good growth",
        "overvalued tech stocks to avoid",
        "high score infra stocks",
        "pharma stocks with low pe",
    ]
    for q in test_queries:
        crit = parse_nl_query(q)
        print(f"\nQuery: {q}")
        print(f"  Sectors: {crit['sectors']}")
        print(f"  Tickers: {len(crit['tickers'])} stocks")
        print(f"  Metrics: {crit['metrics']}")
        print(f"  Signals: {crit['signals']}")
        print(f"  -> {crit['explanation']}")
