# Indian Stock Market Predictor (NSE Trading Desk)

Research-grade **paper-trading** stack for Nifty 50 names: honest walk-forward evaluation, champion **LightGBM** on engineered features, FastAPI, and a Next.js trading desk. **Not investment advice.** No broker connectivity.

## Honest headline metrics (80/20 chronological holdout, all 50 symbols)

| Model | Directional accuracy | MAPE % | RMSE (₹, avg) |
|-------|---------------------|--------|---------------|
| ARIMA(1,1,1) (best direction on holdout) | **~0.507** | ~11.8 | ~332 |
| MA(20) | **~0.506** | ~3.55 | ~115 |
| **LightGBM (deployed for quantiles)** | ~0.471 | **~1.42** | **~47.5** |
| Persistence (close, MAPE) | ~0.50 (zero-return dir.) | **~1.23** | **~42.6** |
| Legacy 60d LSTM (trained) | — | **1.39** pooled MAPE | — |
| GRU (RELIANCE sample) | ~0.543 | N/A (return scale) | — |

LightGBM **does not** beat simple MA(20)/ARIMA on directional accuracy here; it is kept for **feature-rich forecasts and p10–p90 bands**. MAPE ~1.4% is **not** better than persistence (~1.23%) on price. This is **not** competitive with professional quant systems.

Full table: run the API `GET /evaluation` or open `/evaluation` in the UI after `scripts/run_evaluation.py`.

## Features

- OHLCV + RSI, MACD, Bollinger, ATR, volume z-score, MA ratio
- Macro: Nifty, India VIX, USD/INR, crude, S&P 500 (daily returns)
- **Quantile bands** (p10/p50/p90) on next-day return
- **Paper backtest**: long/flat on signal, 10 bps cost + 5 bps slippage vs symbol buy-and-hold and Nifty benchmark
- Watchlist, candlestick desk, evaluation and backtest pages

## Architecture

```text
scripts/fetch_ohlcv.py → backend/data/ohlcv_panel.csv + macro_series.csv
scripts/run_evaluation.py → baselines + LightGBM/GRU compare → evaluation_report.json + champion_lgbm.txt
backend/inference.py + main.py → /predict /ohlcv /evaluation /backtest
frontend → Desk · Evaluation · Backtest
```

## Quick start

```bash
pip install -r requirements.txt
python3 scripts/fetch_ohlcv.py      # if panel missing
python3 scripts/run_evaluation.py   # ~minutes; writes champion + report
cd backend && uvicorn main:app --reload --port 8000
cd frontend && pnpm install && pnpm dev
```

Tests (no TensorFlow in CI):

```bash
pytest tests/ -q
```

## Paper trading disclaimer

This project is for **education and research**. Predictions use **Yahoo Finance EOD** data. Backtests are **simulated** with simplified costs. Do not use for live trading decisions.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/fetch_nifty.py` | Legacy close-only CSV |
| `scripts/train.py` | Legacy LSTM |
| `scripts/fetch_ohlcv.py` | Full OHLCV + macro panel |
| `scripts/run_evaluation.py` | Baselines, champion train, backtest stats |
| `scripts/smoke_predict.py` | One-symbol smoke test |

## Future work

- Multi-fold walk-forward, sector indices, scheduled refresh
- ONNX export, Docker Compose
