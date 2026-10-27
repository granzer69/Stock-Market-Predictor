# Known issues

Left open on purpose in iteration 1. Historical figures cited here are the committed ones in [evaluation-reports.md](evaluation-reports.md).

## Next iteration — `/evaluation` and `/backtest` collide with the pages

`frontend/middleware.ts` rewrites `/evaluation` and `/backtest` to the API when `API_ORIGIN` is set, so the Next pages do not render under the documented Docker and Vercel setup. Locally, without that variable, the page loads and then fetches the same path, which is HTML. Playwright does not open those routes. The evaluation JSON also contains bare `NaN` for momentum MAPE, which `JSON.parse` rejects.

This iteration does not change that routing.

## The stored momentum row is still 1.0

`scripts/run_evaluation.py` now lags the momentum sign. `backend/models/evaluation_report.json` still records pooled momentum `directional_accuracy` **1.0** and non-strict `NaN` MAPE, and `champion_model` **arima_111**. The file was not regenerated. `/evaluation` still returns it.

## The hint bar is not the live bar

Champion hints are scored on `backend/data/ohlcv_panel.csv` (last date **2026-10-16** for every panel symbol in this checkout). The quote can be a later session. The payload now says which bar it used. It does not rescore the live close.

Names in `backend/universe.py` that are absent from the panel (BSE, ETERNAL, INDIGO, JIOFIN, MAXHEALTH, TATACONSUM) get no champion hint. They are not backfilled from the LSTM.

## Research is a different model from the hint

`/api/research/backtest` calls `predicted_returns_from_windows` → `_predict_scaled` (returns LSTM, [MODEL_CARD.md](../MODEL_CARD.md)). The desk hint, when champion files exist, is LightGBM. The research page still says LSTM. That is accurate for the backtest and is not the Markets column.

## Not taken up here

- Same-calendar `sp500` and `crude` on the LightGBM feature row (US close versus NSE close).
- Per-name calibration. The shown hit rate is the pooled LightGBM figure.
- Paper-book identity, optional desk token, and mark-to-market at fill. [API_SPEC.md](../API_SPEC.md) still describes one shared book.
- LSTM retune, a new model, or an automatic promote. [RETRAIN_POLICY.md](../RETRAIN_POLICY.md) and [CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md) stand.
