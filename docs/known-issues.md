# Known issues

The Evaluation and Backtest route split is fixed. Items below are still open. Historical figures cited here are the committed ones in [evaluation-reports.md](evaluation-reports.md).

## Evaluation and Backtest documents

Fixed in iteration 2. `frontend/middleware.ts` proxies `/api/*` only. `/evaluation` and `/backtest` stay on Next when `API_ORIGIN` is set. The pages fetch `GET /api/evaluation` and `GET /api/legacy/backtest`. FastAPI `GET /evaluation` and `GET /backtest` still return the same JSON.

`GET /evaluation` and `GET /api/evaluation` replace bare `NaN` with JSON `null`. The file on disk is unchanged. The Evaluation page prints that the momentum row is the pre-fix same-return score, not a lagged baseline and not a champion.

## The stored momentum row is still 1.0

`scripts/run_evaluation.py` now lags the momentum sign via `momentum_directional_accuracy` in `ml/metrics.py`. `backend/models/evaluation_report.json` still records pooled momentum `directional_accuracy` **1.0** and non-strict `NaN` MAPE, and `champion_model` **arima_111**. The file was not regenerated. The HTTP response keeps directional accuracy 1.0 and sends `null` for that row's MAPE and RMSE.

## The hint bar is not the live bar

Champion hints are scored on `backend/data/ohlcv_panel.csv` (last date **2026-10-16** for every panel symbol in this checkout). The quote can be a later session. The payload now says which bar it used. It does not rescore the live close.

Names in `backend/universe.py` that are absent from the panel (BSE, ETERNAL, INDIGO, JIOFIN, MAXHEALTH, TATACONSUM) get no champion hint. They are not labeled LSTM. `GET /api/predict/{symbol}` for those names returns 404 `No champion forecast for this symbol`. If the champion stack cannot load at all, hints fall back to the returns LSTM with `model` `lstm`.

## Research is a different model from the hint

`/api/research/backtest` calls `predicted_returns_from_windows` → `_predict_scaled` (returns LSTM, [MODEL_CARD.md](../MODEL_CARD.md)). The desk hint, when champion files exist, is LightGBM. The research page still says LSTM. That is accurate for the backtest and is not the Markets column.

## Not taken up here

- Same-calendar `sp500` and `crude` on the LightGBM feature row (US close versus NSE close).
- Per-name calibration. The shown hit rate is the pooled LightGBM figure.
- Paper-book identity, optional desk token, and mark-to-market at fill. [API_SPEC.md](../API_SPEC.md) still describes one shared book.
- LSTM retune, a new model, or an automatic promote. [RETRAIN_POLICY.md](../RETRAIN_POLICY.md) and [CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md) stand.
