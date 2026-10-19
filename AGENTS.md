# Agent guide — Bharat Desk

## Product

Indian **Nifty 50** research desk: daily-close LSTM hints, macro tape, **INR paper trading** only. Not a broker; not investment advice.

## Repo map

| Area | Path |
|------|------|
| API | `backend/main.py` |
| Market data | `backend/market_data.py`, `universe.py` |
| Model | `backend/train_lstm.py`, `predictor.py`, `artifacts/` |
| Paper book | `backend/portfolio.py` |
| UI | `frontend/` (Next.js 15) |
| API contract | [API_SPEC.md](API_SPEC.md), [openapi.json](openapi.json) |
| Model facts | [MODEL_CARD.md](MODEL_CARD.md) |

## Commands

```bash
python -m pytest -q
python backend/scripts/export_openapi.py
python backend/scripts/run_backtest.py --symbol RELIANCE.NS
docker compose up --build
python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
cd frontend && pnpm install && pnpm dev --hostname 0.0.0.0 --port 3000
cd frontend && pnpm test:e2e
```

## Rules for changes

1. **Do not** invent API fields—match `backend/main.py` and refresh OpenAPI export.
2. **Do not** claim model performance without updating `metrics.json` / MODEL_CARD.
3. Yahoo via `yfinance`; set `YF_DISABLE_CURL_CFFI=1` where TensorFlow shares the process.
4. Tests: mock market/predictor in API tests; no live Yahoo in CI pytest.
5. Phased delivery: see [TASKS.md](TASKS.md) and log in [PROGRESS.md](PROGRESS.md).

## Branch / PR

Feature work on `cursor/*` branches; CI runs pytest + OpenAPI export + frontend Playwright (mocked API).
