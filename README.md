# KAIROFORGE — Institutional-Grade Equity Research Terminal for Indian Markets

A dark-themed, production-ready **Streamlit** application for screening and analysing **NSE-listed Indian stocks** (Nifty universe). Built with live Yahoo Finance data, real-time scoring, and a multi-tab valuation workflow.

---

## Quick Start

```bash
bash run.sh
```

The app runs on **port 5000** (headless, Replit-friendly). The `run.sh` script automatically sets the correct public domain for WebSocket.

## Screenshots

### Value Screener — Landing Page
> Full-page terminal landing with animated hero, feature cards, stats row, and investment signal legend.

### Value Screener — Results
> Ranked table of all 120+ stocks with **Value Opportunity Score (0–100)** and color-coded signals.

### Stock Analysis — DCF & Price Target
> 3-stage DCF with sliders, sensitivity heatmap, and bull/base/bear price targets.

---

## Architecture

| File | Role | Lines |
|------|------|-------|
| `app.py` | Main UI — sidebar nav, screener, stock analysis, tabs, charts, HTML report generator | ~1,900 |
| `data_loader.py` | yfinance fetch layer with **5-min cache** + parallel batch loading | ~200 |
| `valuation_models.py` | Graham Number, ratio analysis, WACC estimation, **3-stage DCF**, sensitivity heatmap | ~280 |
| `screener.py` | Value Opportunity Score (0–100), signal engine (STRONG BUY → AVOID), explainability | ~350 |
| `portfolio.py` | CSV export helpers for screener results | ~160 |
| `stocks.py` | NSE stock universe (~120 Nifty stocks) + **industry/sector peer mappings** | ~350 |
| `.streamlit/config.toml` | Dark terminal theme (bg #080d1a, primary #3b82f6) | ~14 |
| `run.sh` | Entry point — sets Replit domain and runs `streamlit run app.py` | ~15 |

---

## Key Features

### 1. Value Screener
- **120+ Nifty stocks** fetched in parallel via **15-thread thread pool**
- **5-minute cache** per ticker — no redundant API calls
- **4 scoring pillars** (100 pts total):
  - Graham Number Margin of Safety — **40 pts**
  - ROE Quality — **25 pts**
  - P/E Ratio — **20 pts**
  - Debt/Equity — **15 pts**
- **4 investment signals:** ≥70 → STRONG BUY · 50–69 → BUY · 30–49 → HOLD · <30 → AVOID
- Filter by signal strength and data quality
- CSV export
- Signal distribution chart

### 2. Stock Analysis (7 Tabs)
| Tab | What It Shows |
|-----|--------------|
| **Overview** | Price, market cap, EPS, book value, 52-week range, 5-year price chart with 50/200 SMA |
| **Valuation** | Graham Number analysis, gauge chart, P/E, P/B, ROE, ROIC, D/E, EPS growth, dividend yield |
| **DCF Model** | 3-stage DCF with adjustable sliders (growth rates, WACC, terminal). Auto-estimated WACC via CAPM |
| **Sensitivity** | WACC × Terminal Growth heatmap showing intrinsic value under all combinations |
| **Price Target** | Bull/Base/Bear scenarios with visual range bar, upside %, waterfall chart |
| **News & Sentiment** | Live Yahoo Finance headlines with keyword-based sentiment (positive/neutral/negative) |
| **Peer Comparison** | Side-by-side radar chart + table vs sector/industry peers |

### 3. HTML Research Report
- **Downloadable self-contained HTML report** per stock
- All ratios, DCF, Graham Number, signal, and explanation
- Print-ready — open in any browser

---

## Data Model

### Value Opportunity Score
```
Total Score (0-100) = Graham MoS (40) + ROE (25) + P/E (20) + D/E (15)

Signal thresholds:
  >= 70 → STRONG BUY
  >= 50 → BUY
  >= 30 → HOLD
  < 30  → AVOID
```

### 3-Stage DCF
```
Stage 1: High Growth — FCF grows at g1 for n1 years
Stage 2: Transition — growth declines linearly from g1 to g2
Stage 3: Terminal Value — Gordon Growth perpetuity at gT

WACC = ke * (E/V) + kd * (D/V)
  ke = Rf + β * ERP    (CAPM)
  Rf = 7.2% (India 10Y G-sec)
  ERP = 7.0% (Damodaran India)
  kd = 8% * (1 - 25%) (post-tax cost of debt)
```

### Graham Number
```
Graham Number = √(22.5 × EPS × Book Value per Share)
```

---

## File Reference

### `app.py` (Main UI)
- **Sidebar**: Logo, navigation, stock count, quick-load indicator
- **`render_screener()`**: Two-state — `_render_landing()` (initial) and `_render_screener_results()` (after run)
- **`render_analysis()`**: Stock analysis with 7 sub-tabs
- **Chart factories**: `make_gauge()`, `make_bar_comp()`, `make_hist_chart()`, `make_dcf_waterfall()`, `make_sensitivity_heatmap()`, `score_donut()`
- **`generate_html_report()`**: Self-contained HTML report builder
- **`hero_card()`**, **`kpi_tiles()`**, **`screener_table()`**: Custom HTML component helpers
- **`_score_headline()`**, **`_time_ago()`**: News sentiment and time formatting

### `data_loader.py` (Fetch Layer)
- **`fetch_stock_data(ticker)`**: Returns yfinance `.info` dict (5-min cache)
- **`fetch_price_history(ticker, period)`**: Returns OHLCV DataFrame
- **`fetch_news(ticker)`**: Returns cleaned news articles with `title`, `publisher`, `link`, `time`
- **`batch_fetch_stocks(tickers)`**: Parallel 15-thread fetch with progress callback
- **`safe_get(info, key, default)`**: Returns value only if present and finite (handles NaN/±Inf)

### `valuation_models.py` (Calculations)
- **`calculate_graham(eps, bvps)`**: Returns Graham Number or None
- **`calculate_ratios(info)`**: Returns 8 ratios including P/E, P/B, ROE, ROIC, D/E, EPS growth, dividend yield
- **`estimate_wacc(info)`**: Returns WACC using CAPM + simplified debt cost
- **`calculate_dcf(fcf, g1, n1, g2, n2, gT, wacc)`**: Returns dict with intrinsic value, PV breakdown, cash flow table
- **`run_sensitivity(fcf, g1, n1, g2, n2, wacc_range, gT_range)`**: Returns DataFrame heatmap

### `screener.py` (Scoring Engine)
- **`data_quality_score(info)`**: 0–100 completeness rating
- **`score_stock(ticker, name, info)`**: Full 0–100 score + explanation
- **`generate_signal(score)`**: Maps score to signal/emoji/hex color
- **`generate_explanation(data)`**: Plain-English rationale
- **`run_screener(stock_dict)`**: Parallel fetch + score, sorted by Score desc

### `stocks.py` (Universe)
- **`STOCKS`**: 120+ Nifty tickers
- **`INDUSTRY_PEERS`**: Exact yfinance industry strings mapped to ticker lists
- **`SECTOR_PEERS`**: Broader sector groupings
- **`TICKER_TO_NAME`**: Reverse lookup for peer comparison

---

## Security Considerations

- **HTML escaping**: All external strings (yfinance API responses, user-entered tickers) are escaped via `html.escape()` before embedding in `unsafe_allow_html=True` blocks
- **Link sanitization**: News links are validated to `http://` or `https://` only — `javascript:` and `data:` URIs are stripped
- **No secrets in code**: No API keys — uses public Yahoo Finance data

---

## Dependencies

```
streamlit
yfinance
pandas
plotly
```

Dependencies are installed via Replit's package manager (`.pythonlibs/`). No external API keys required.

---

## Author

**Dhruv Vaniawala**  
✉️ uwddhruv@gmail.com

> ⚠️ For educational purposes only — not financial advice.
> Data sourced from Yahoo Finance. Accuracy not guaranteed.
