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

## Graham Number Stock Analyser (app.py)

- Takes an NSE-format Indian stock ticker (e.g. `RELIANCE.NS`)
- Fetches current price, trailing EPS, and book value per share via yfinance
- Calculates Graham Number: `sqrt(22.5 × EPS × BVPS)`
- Shows undervalued/overvalued verdict with margin of safety or premium %
- Displays a summary table and formula breakdown
- All code is heavily commented for beginners

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
