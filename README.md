# Stock Market Predictor

LSTM-style Keras model for **next-day close** forecasting from historical OHLCV windows, exposed via **FastAPI** and a **Next.js** UI (plus a Streamlit prototype).

## Overview

Given recent close prices (60-day window), the model predicts the next close. The FastAPI service serves `/predict`, `/chart`, and a demo `/realtime` endpoint over a bundled top-50 stocks CSV. A Next.js frontend consumes the API; `main.py` is an alternate Streamlit upload flow.

## Architecture

```text
CSV / upload  →  MinMaxScaler + Keras model (.h5)
                      │
         ┌────────────┴────────────┐
    FastAPI (backend/)        Streamlit (main.py)
         │
    Next.js frontend
```

## Tech stack

- **ML**: TensorFlow / Keras, scikit-learn (`MinMaxScaler`), joblib
- **API**: FastAPI, CORS for `localhost:3000`
- **UI**: Next.js (TypeScript, Tailwind), Streamlit prototype
- **Data**: `top50_stocks_data.csv`, sample CSV for demos

## Features

- Next-day close prediction from last 60 closes
- Chart series endpoint for the UI
- Symbol-based lookup against bundled historical CSV
- Streamlit path for ad-hoc CSV upload (requires `Close` column)

## Honest limitations

- Trained / served on **historical CSV**, not live market feeds
- `/realtime` **simulates** small price jitter for demo UX — not a live exchange quote
- `confidence` returned by the API is a **placeholder random value** for UI wiring — do not treat as model calibration
- Educational / portfolio project, not trading advice

## Getting started

### API

```bash
cd backend
# ensure stock_predictor_model.h5 + scaler.save + top50_stocks_data.csv are present
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install   # or npm install
pnpm dev
```

### Streamlit prototype

```bash
# from repo root; place model + scaler beside main.py or adjust paths
streamlit run main.py
```

## Project structure

```text
backend/     FastAPI + model artifacts + CSV
frontend/    Next.js app
main.py      Streamlit upload demo
Stock_Market_Predictor.ipynb   training / exploration notebook
```

## Future improvements

- Replace dummy confidence with real validation metrics
- Wire live market data (with clear caching / rate limits)
- Document training recipe and eval metrics in-repo
