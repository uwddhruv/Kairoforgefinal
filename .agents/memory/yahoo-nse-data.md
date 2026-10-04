---
name: Yahoo NSE valuation fields
description: Yahoo Finance often omits free cash flow and total shares from .info for NSE-listed stocks.
---

For NSE tickers, Yahoo Finance `.info` can omit `freeCashflow` and `sharesOutstanding` even when annual cash-flow statements and reported share counts are available. The annual statement may provide a `Free Cash Flow` row; otherwise FCF can only be computed from operating cash flow and capital expenditure for the same period. Total shares may come from the balance sheet or Yahoo share history.

Do not use `floatShares` as the denominator: it is only the publicly tradable float and can inflate FCF per share. Do not substitute EPS or a made-up amount for FCF. Show the statement period/source, and withhold the DCF when required values remain unavailable.

**Why:** Live Yahoo Finance checks showed missing summary FCF and share-count fields across multiple large NSE tickers, while statement data was available.

**How to apply:** Prefer Yahoo's TTM FCF and total shares when present. Fall back to the latest reported annual FCF and a total-share count only when the summary fields are absent. Treat the FCF line cautiously for banks and other financial institutions because deposits and lending flows can make an industrial-style FCF DCF misleading.