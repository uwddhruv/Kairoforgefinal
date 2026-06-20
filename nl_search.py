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
    "Technology":            ["tech", "it", "software", "digital", "infotech", "information technology"],
    "Financial Services":    ["bank", "banks", "finance", "nbfc", "insurance", "fintech", "lending", "asset management"],
    "Healthcare":            ["pharma", "pharmaceutical", "pharmaceuticals", "medicine", "drug", "hospital", "hospitals", "medical", "health", "biotech"],
    "Consumer Cyclical":     ["auto", "automotive", "car", "vehicles", "retail", "fashion", "luxury", "apparel", "jewellery", "titan", "trent", "food service", "restaurant", "travel", "airline", "airlines"],
    "Consumer Defensive":    ["fmcg", "consumer", "food", "beverage", "tobacco", "personal care", "household", "nestle", "itc", "hul", "hindustan unilever"],
    "Energy":                ["oil", "gas", "petroleum", "coal", "mining", "energy"],
    "Utilities":             ["power", "electric", "electricity", "renewable", "solar", "wind", "grid", "ntpc", "powergrid", "adani green"],
    "Basic Materials":       ["steel", "metal", "metals", "aluminium", "aluminum", "iron", "cement", "paint", "chemical", "grasim", "ultratech", "tata steel", "jsw steel"],
    "Industrials":           ["infra", "infrastructure", "construction", "engineering", "defence", "defense", "aerospace", "logistics", "ports", "shipping", "lt", "larsen", "bel", "hal"],
    "Communication Services": ["telecom", "telecommunication", "internet", "media", "bharti", "airtel", "naukri", "nykaa"],
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
    "pe":       {"low": 25, "high": 30, "cheap": 25, "expensive": 35, "safe": 25, "risky": 35},
    "pb":       {"low": 3, "high": 4, "cheap": 3, "expensive": 5, "safe": 3, "risky": 5},
    "roe":      {"low": 0.10, "high": 0.15, "strong": 0.15, "weak": 0.10, "good": 0.15, "bad": 0.10},
    "roce":     {"low": 0.10, "high": 0.15, "strong": 0.15, "weak": 0.10, "good": 0.15, "bad": 0.10},
    "de":       {"low": 0.5, "high": 1.0, "safe": 0.5, "risky": 1.0},
    "eps":      {"low": 10, "high": 50, "strong": 50, "weak": 10},
    "growth":   {"low": 0.05, "high": 0.15, "strong": 0.15, "weak": 0.05, "good": 0.15, "bad": 0.05},
    "dividend": {"low": 0.01, "high": 0.02, "strong": 0.02, "weak": 0.01},
    "beta":     {"low": 0.8, "high": 1.2, "safe": 0.8, "risky": 1.2},
    "graham":   {"low": 0.1, "high": 0.5, "cheap": 0.1, "expensive": 0.5, "strong": 0.1},
    "score":    {"low": 40, "high": 50, "strong": 50, "weak": 40, "good": 50, "bad": 35},
}

# Broad qualifiers that apply to a predefined set of metrics
BROAD_QUALIFIERS: dict[str, dict[str, Any]] = {
    "undervalued": {
        "pe": {"op": "lt", "value": 25},
        "score": {"op": "gt", "value": 40},
    },
    "overvalued": {
        "pe": {"op": "gt", "value": 30},
    },
    "cheap": {
        "pe": {"op": "lt", "value": 25},
        "score": {"op": "gt", "value": 40},
    },
    "expensive": {
        "pe": {"op": "gt", "value": 30},
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


def _find_closest_qualifier(q: str, metric_alias: str) -> str | None:
    """Find the qualifier closest to the metric in the query.

    For a phrase like "low pe and high roce", when looking for the qualifier
    near "pe", it finds "low" (distance 0). When looking for the qualifier
    near "roce", it finds "high" (distance 0) and ignores "low" (distance 5).
    """
    words = q.lower().split()
    metric_words = metric_alias.lower().split()
    qualifiers = set(QUALIFIER_THRESHOLDS.keys())
    closest_qual = None
    closest_dist = float("inf")

    for i in range(len(words)):
        chunk = " ".join(words[i:i + len(metric_words)])
        if chunk == metric_alias.lower():
            # Metric found at index i. Find the closest qualifier.
            for j, w in enumerate(words):
                if w in qualifiers:
                    # Distance from qualifier to metric start
                    dist = abs(j - i)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_qual = w
    return closest_qual


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

    # ── 4. Metric + qualifier detection (closest-pairing) ────────────
    for metric_key, aliases in METRIC_ALIASES.items():
        matched = False
        for alias in aliases:
            if _word_match(q, alias):
                qual = _find_closest_qualifier(q, alias)
                if qual:
                    defaults = METRIC_DEFAULTS.get(metric_key, {})
                    val = defaults.get(qual)
                    if val is not None:
                        direction = QUALIFIER_THRESHOLDS[qual]["_direction"]
                        criteria["metrics"][metric_key] = {"op": direction, "value": val}
                        matched_parts.append(f"{qual} {metric_key}")
                        matched = True
                        break
            # If the alias is a substring but not a word match, try exact word match
            elif len(alias) >= 3 and alias in q:
                qual = _find_closest_qualifier(q, alias)
                if qual:
                    defaults = METRIC_DEFAULTS.get(metric_key, {})
                    val = defaults.get(qual)
                    if val is not None:
                        direction = QUALIFIER_THRESHOLDS[qual]["_direction"]
                        criteria["metrics"][metric_key] = {"op": direction, "value": val}
                        matched_parts.append(f"{qual} {metric_key}")
                        matched = True
                        break
        if matched:
            continue

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

    **Lenient rule**: if a stock is missing the data for a metric, we skip
    that filter rather than reject the stock. Indian stocks often have
    incomplete yfinance data, so this avoids false negatives.
    """
    filtered = []
    metrics = criteria.get("metrics", {})
    signals = criteria.get("signals", [])

    for stock in stock_results:
        ok = True
        for metric, rule in metrics.items():
            val = _get_metric_value(stock, metric)
            if val is None:
                # Missing data for this metric → skip this filter (lenient)
                continue
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
    """Extract a normalized metric value from a stock dict.

    ``score_stock()`` returns these keys: Price (₹), Graham No., MoS %,
    ROE (%), P/E, D/E, Beta, Score.
    """
    mapping = {
        "pe": "P/E",
        "pb": "Graham No.",
        "roe": "ROE (%)",
        "roce": "ROE (%)",
        "de": "D/E",
        "eps": "Graham No.",
        "growth": "Score",
        "dividend": "Score",
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
