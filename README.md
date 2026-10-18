# Indian Stock Market Predictor

LSTM Keras model for **next-session NSE close** forecasting from a 60-day adjusted-close window, exposed via **FastAPI** and a **Next.js** UI (plus Streamlit demos).

## Overview

The app targets **Nifty 50** names on NSE (Yahoo tickers `*.NS`). Historical daily data is fetched with **yfinance**, trained with **per-symbol MinMaxScalers** and a shared LSTM, then served from bundled CSV + model artifacts. The UI lists symbols from `GET /symbols`, shows prices in **INR**, and labels the quote card as **latest close** (end-of-day CSV), not a live exchange tape.

## Architecture

```text
data/nifty50_symbols.csv  →  scripts/fetch_nifty.py  →  backend/data/nifty50_closes.csv
                                      │
                              scripts/train.py
                                      │
                    backend/models/nifty_lstm.keras + scalers.joblib + metrics.json
                                      │
                         FastAPI (backend/main.py)
                                      │
                              Next.js frontend
```

Legacy US artifacts (`stock_predictor_model.h5`, `top50_stocks_data.csv`) remain in `backend/` for history but are **not** used by the API.

## Tech stack

- **ML**: TensorFlow / Keras, scikit-learn, joblib
- **Data**: yfinance (NSE `.NS`, `auto_adjust=True`)
- **API**: FastAPI, CORS via `ALLOWED_ORIGINS` (default `http://localhost:3000`)
- **UI**: Next.js (TypeScript, Tailwind, Recharts)
- **Demos**: Streamlit upload (`main.py`), yfinance NSE ticker demo (`main2.py`, no API keys)

## Features

- Nifty 50 symbol list with names and sectors
- `GET /predict`, `/chart`, `/realtime`, `/symbols`
- Symbol aliases: `RELIANCE`, `reliance.ns`, `RELIANCE.NS`
- **Confidence** = `clip(1 − symbol_test_MAPE, 0, 0.99)` from `metrics.json` (error proxy, not a probability)
- Deterministic `/realtime` from last two CSV closes

## Honest limitations

- **Not trading advice.** Educational / portfolio use only.
- Quotes and charts are **EOD historical** data baked into `nifty50_closes.csv`, not live NSE feeds.
- Nifty membership is **pinned** in `data/nifty50_symbols.csv`; refresh data manually when the index changes.
- Yahoo Finance can rate-limit or return gaps; see `backend/data/fetch_report.json` after fetch.
- CI runs **pytest without TensorFlow** (mocked model/scalers). Training and smoke tests need TensorFlow locally.

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Data and training (first time or refresh)

```bash
python3 scripts/fetch_nifty.py
python3 scripts/train.py
```

### 3. API

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
pnpm install
cp .env.example .env.local   # optional: NEXT_PUBLIC_API_URL
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

### Streamlit

```bash
streamlit run main.py          # CSV upload (₹ labels; needs model beside app or adjust paths)
streamlit run main2.py         # yfinance .NS demo in INR
```

### Tests and smoke

```bash
pytest tests/ -q
python3 scripts/smoke_predict.py   # requires trained artifacts + TensorFlow
```

## Project structure

```text
data/                    Pinned Nifty 50 list
scripts/                 fetch_nifty.py, train.py, smoke_predict.py
backend/
  main.py                FastAPI app
  data/                  nifty50_closes.csv, fetch_report.json
  models/                nifty_lstm.keras, scalers.joblib, metrics.json
frontend/                Next.js dashboard
tests/                   Mocked API tests (no TF in CI)
main.py, main2.py        Streamlit demos
Stock_Market_Predictor.ipynb   Original US notebook (reference)
```

## Future improvements

- Scheduled data refresh and GitHub Actions (pytest-only CI)
- Docker Compose for API + frontend
- Optional delayed live quote endpoint with caching
- BSE `.BO` or Nifty Next 50 expansion
