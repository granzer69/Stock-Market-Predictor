# Bharat Desk

Next-day Nifty 50 forecasts from a log-return LSTM, with a paper trading book in INR. Built for research and practice. It is not investment advice, not a SEBI-registered product, and it does not send orders to a broker.

## What it does

- Daily NSE closes for the Nifty 50, plus Nifty, Sensex, Bank Nifty, India VIX, USD/INR, Brent, gold, the S&P 500, and Nasdaq
- A single LSTM that predicts the next session's log return, then converts that to a close
- Holdout directional accuracy and error versus a flat forecast, shown in the UI
- Candlesticks, volume, SMA 20/50, and a dashed next-close line
- Paper buys and sells of whole shares at the latest close, starting from ₹10,00,000

Quotes refresh about every 15 minutes. History is cached for about 12 hours. `yfinance` is an unofficial source and can fail or lag the exchange.

## Run

```bash
pip install -r backend/requirements.txt
python backend/train_lstm.py
python -m uvicorn main:app --app-dir backend --port 8000
```

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

### Docker (demo)

```bash
docker compose up --build
```

API on port 8000, UI on 3000 (`API_ORIGIN` rewrites `/api` to the API container).

### Research CLI

```bash
python backend/scripts/run_backtest.py --symbol RELIANCE.NS
python backend/scripts/walk_forward_report.py
WF_AS_OF_DATE=2024-06-01 python backend/scripts/walk_forward_retrain.py
```

## Layout

```text
backend/universe.py       Nifty 50 and macro symbols
backend/market_data.py    download + disk cache
backend/features.py       return windows shared by train and inference
backend/train_lstm.py     writes artifacts/model.keras, scaler, metrics
backend/predictor.py      next close, signal, recent actual-vs-predicted
backend/portfolio.py      SQLite paper book
backend/main.py           FastAPI
frontend/                 Next.js desk
main.py                   older Streamlit CSV upload demo
```

Signals are `BUY` or `SELL` only when the predicted move is beyond 0.3%. Otherwise the hint is `HOLD`. Confidence on a name is that name's holdout directional hit rate.
