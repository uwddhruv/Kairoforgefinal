# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.
Also includes a Python Streamlit application for Indian stock analysis.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)
- **Python app**: Streamlit + yfinance + pandas (Graham Number stock analyser)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally
- `streamlit run app.py --server.port 5000` — run the Graham Number stock analyser

## Equity Research Dashboard (Python — app.py)

Full-featured NSE stock valuation and screening platform.

### Architecture (modular)
| File                 | Role |
|----------------------|------|
| `app.py`             | Main Streamlit UI — 3 tabs |
| `data_loader.py`     | yfinance fetch with caching + parallel batch |
| `valuation_models.py`| Graham, DCF (3-stage), WACC, sensitivity |
| `screener.py`        | Value Opportunity Score, signals, explanations |
| `portfolio.py`       | Equal-weight portfolio metrics + CSV export |
| `stocks.py`          | NSE stock universe (~120 Nifty stocks) |

### 3 Main Tabs
1. **📊 Screener** — Parallel Nifty screener, Value Opportunity Score (0-100), signal badges (STRONG BUY → AVOID), CSV export
2. **📈 Deep Analysis** — Graham Number, 3-stage DCF, ratio analysis, sensitivity heatmap, explainability text, price history
3. **💼 Portfolio Builder** — Equal-weight hypothetical portfolio, avg score/MoS/beta, risk flag, allocation pie, CSV export

### Scoring System (0-100 pts)
- Graham MoS: 40 pts  |  ROE quality: 25 pts  |  P/E: 20 pts  |  D/E: 15 pts
- STRONG BUY ≥70, BUY 50-69, HOLD 30-49, AVOID <30

### Run
`bash run.sh`  (port 5000, headless, CORS/XSRF disabled for Replit proxy)

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
