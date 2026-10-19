# Bharat Desk

Next-day Nifty 50 forecasts, research backtests with India delivery costs, and a paper trading book in INR. Built for education and research — **not investment advice**, not SEBI-registered, and **no live broker** connectivity.

When evaluation artifacts are present, the API can serve a **LightGBM champion** for live quotes and quantile bands; **research backtests** use the committed **LSTM** bundle in `backend/artifacts/`. See [MODEL_CARD.md](MODEL_CARD.md).

## What it does

- Daily Nifty 50 quotes plus macro tape (Nifty, Sensex, Bank Nifty, India VIX, USD/INR, Brent, gold, US indices)
- `/research` — single-name and portfolio long-only backtests, equity curves, JSON/CSV export
- Paper buys and sells of whole shares at the latest close (optional India costs via `PAPER_APPLY_INDIA_COSTS`)
- Runtime config at `GET /api/config` (data provider, CORS documented in [DEPLOY.md](DEPLOY.md))

Quotes refresh about every 15 minutes. History is cached ~12 hours. `yfinance` is unofficial and can fail; use `MARKET_DATA_FAILOVER` and NSE CSV bundles per [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md).

## Run locally

```bash
pip install -r backend/requirements.txt
python backend/train_lstm.py   # if artifacts missing
python -m uvicorn main:app --app-dir backend --port 8000
```

```bash
cd frontend && pnpm install && pnpm dev
```

Open `http://localhost:3000`.

### Docker (demo)

```bash
docker compose up --build
```

### Tests

```bash
cd backend && python -m pytest -q
cd frontend && pnpm test:e2e
```

## Changelog

### v0.1.0 (2026-10-19)

- Env-based `CORS_ORIGINS`, request IDs, research backtest concurrency limit
- Data failover, OHLCV validation, governance runbooks (data, corp actions, universe)
- Paper book backup script, compose volumes, drift-check workflow
- Backtest `fill=next_close`, optional paper India costs, MODEL_CARD link on Research
- Architecture delta: [ARCHITECTURE_DELTA.md](ARCHITECTURE_DELTA.md)

## Layout

```text
backend/main.py           FastAPI (desk + optional evaluation routes)
backend/research.py       API backtest helpers
backend/artifacts/        Production LSTM bundle
frontend/                 Next.js desk + /research
```

Legacy Streamlit demo: `main.py` at repo root.
