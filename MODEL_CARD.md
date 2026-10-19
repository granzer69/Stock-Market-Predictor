# Model card — Bharat Desk next-day LSTM

**Artifact location:** [backend/artifacts/](backend/artifacts/) (`model.keras`, `scaler.joblib`, `metrics.json`)  
**Training script:** [backend/train_lstm.py](backend/train_lstm.py)  
**Inference:** [backend/predictor.py](backend/predictor.py)

Values below are taken from committed `metrics.json` unless labeled as structural facts from code.

---

## Model details

| Item | Value |
|------|--------|
| Type | Stacked LSTM (Keras Sequential) |
| Layers | LSTM(32) → Dropout(0.2) → LSTM(16) → Dropout(0.2) → Dense(8) → Dense(1) |
| Optimizer | Adam, lr=1e-3 |
| Loss | MSE on scaled target |
| Training epochs | 8 (default), early stopping on `val_loss` |
| Input window | **60** trading days |
| Input features | **1** — daily log return of close, clipped to ±0.2 |
| Target | Next-day log return |
| Scaler | `StandardScaler` fit on all training-window return values (pooled across symbols) |
| Universe | Nifty 50 (`.NS`), 5y daily history via Yahoo at train time |
| Pooled training rows | **46,635** (per `metrics.json`) |
| Symbols in holdout eval | **50** |

---

## Holdout evaluation (committed metrics)

| Metric | Value |
|--------|--------|
| Holdout fraction | 0.2 (last 20% of each symbol’s windows, time-ordered) |
| Directional accuracy | **0.4820** (~48.2%) |
| MAE (log return) | **0.012032** |
| Naive MAE (predict 0 return) | **0.012005** |
| Signal threshold (BUY/SELL) | **0.003** (0.3% move) |
| Last trained (UTC) | **2026-10-18T19:18:36.779819+00:00** |

The model’s holdout error is **not better** than predicting zero return on average. Directional accuracy is **below 50%**.

Per-symbol holdout stats are in `metrics.json` under `per_symbol`.

---

## Intended use

- Research and education UI: next-close **hint** on Nifty 50 names.
- **Not** for live trading, investment advice, or regulatory distribution.
- Paper orders in the app do **not** use model output for execution—only user clicks at last close.

---

## Out of scope (not in model)

- Intraday prices, order book, derivatives.
- Fundamentals, news, FII/DII flows, index/macro inputs (shown in UI tape only).
- Cross-sectional ranking or portfolio optimization.
- Transaction costs, slippage, open-gap fills.

---

## Known limitations (code + metrics)

1. **Data:** Yahoo Finance via `yfinance`; unofficial, may lag or fail; `YF_DISABLE_CURL_CFFI=1` in API process.
2. **Training:** `model.fit(..., shuffle=True)` shuffles windows across time and symbols (optimistic train/val; holdout slice is temporal per symbol).
3. **Single global model** for all tickers; no per-sector heads.
4. **Confidence** shown in API/UI is holdout **directional hit rate**, not calibrated probability.
5. **Comparison chart** on symbol page replays one-step predictions on recent history for UX; not a fresh OOS test.
6. Retrain is manual (`python backend/train_lstm.py`); no automated drift monitoring.

---

## How to reproduce training

```bash
pip install -r backend/requirements.txt
python backend/train_lstm.py
```

Requires network access to Yahoo. Overwrites `backend/artifacts/`.
