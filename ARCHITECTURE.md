# Architecture — Bharat Desk (as-built)

**Status:** Phase 0 as-built. Iteration 1 (forecast provenance) is in [docs/architecture.md](docs/architecture.md). See [CODEBASE_AUDIT.md](CODEBASE_AUDIT.md) for the 2026-10-19 inspection.

## System context

```text
                    ┌─────────────────────────────────────┐
                    │  Browser (Markets / Stock / Portfolio) │
                    └──────────────────┬──────────────────┘
                                       │ HTTP (port 3000)
                    ┌──────────────────▼──────────────────┐
                    │  Next.js 15 (frontend/)              │
                    │  - App Router pages                  │
                    │  - rewrite: /api/* → :8000/api/*     │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  FastAPI (backend/main.py)           │
                    │  - market_data.PriceCache            │
                    │  - predictor.Predictor               │
                    │  - portfolio.PaperBook (SQLite)      │
                    └───────┬─────────────────┬───────────┘
                            │                 │
              ┌─────────────▼─────┐   ┌───────▼────────┐
              │ yfinance (Yahoo)   │   │ artifacts/     │
              │ + disk cache       │   │ model.keras    │
              └────────────────────┘   │ scaler.joblib  │
                                       │ metrics.json   │
                                       └────────────────┘
```

## Module map

| Path | Responsibility |
|------|----------------|
| [frontend/app/](frontend/app/) | Routes: `/`, `/portfolio`, `/stock/[symbol]` |
| [frontend/components/](frontend/components/) | UI: tape, table, charts, ticket, portfolio |
| [frontend/lib/api.ts](frontend/lib/api.ts) | Fetch wrapper; default same-origin |
| [backend/main.py](backend/main.py) | HTTP API, lifespan wiring |
| [backend/universe.py](backend/universe.py) | Nifty 50 + macro symbol registry |
| [backend/market_data.py](backend/market_data.py) | Yahoo download, normalize OHLCV, cache |
| [backend/features.py](backend/features.py) | 60-day log-return windows, signal threshold |
| [backend/train_lstm.py](backend/train_lstm.py) | Offline training → `artifacts/` |
| [backend/predictor.py](backend/predictor.py) | Load model; batch summaries + per-symbol detail |
| [backend/portfolio.py](backend/portfolio.py) | Paper ledger |
| [backend/tests/](backend/tests/) | Unit tests (cache, features, portfolio) |

## Data flow

### Overview request

1. Client `GET /api/market/overview`.
2. `get_quotes(Nifty 50)` — memory/disk/ Yahoo `5d`.
3. `get_histories(Nifty 50, 2y)` — memory/disk/ Yahoo.
4. `predictor.summaries(histories)` — when `champion_lgbm.txt` is present, each hint is `inference.predict_symbol` (LightGBM on the frozen panel). The payload keeps that forecast's `as_of`, base close, and model id `lightgbm`. It does not copy the live bar onto the forecast. If the champion stack is not available, this step is one LSTM forward per symbol on the last window.
5. Merge quote + metadata + prediction. The quote keeps the live session. `predictor.summary()` is the separate model-summary object (LSTM card metrics plus the evaluation report). Research backtests do not use this hint; they call `DeskPredictor._predict_scaled`.

### Order flow

1. Client `POST /api/orders` with ticker or symbol resolved via `universe.resolve`.
2. Latest quote price from cache/Yahoo.
3. `PaperBook.place_order` — transactional SQLite update.
4. Snapshot row appended to equity curve table.

## Runtime dependencies

- Python 3.12+ (verified in audit environment), TensorFlow for inference/training.
- Node/pnpm for frontend.
- Network egress to Yahoo (unless cache fully satisfies request).

## Non-goals (current code)

- Broker connectivity, live orders, SEBI registration.
- Intraday bars, order book, derivatives chain.
- Multi-user auth, horizontal scale, managed DB.

## Legacy components (same repo, separate entrypoints)

- [main.py](main.py) — Streamlit + US `.h5` model.
- [backend/top50_stocks_data.csv](backend/top50_stocks_data.csv) + old `.h5` — pre-Bharat demo.

## Deployment pattern (documented, not automated)

1. Train or ship committed `backend/artifacts/`.
2. `uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000`
3. `pnpm dev --hostname 0.0.0.0 --port 3000` (or production build + same rewrite rules).

Single-port access: use Next on 3000 only; API proxied.
