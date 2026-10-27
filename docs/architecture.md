# Architecture — forecast provenance (iteration 1)

This note records how a desk hint is produced after iteration 1. The phase-0 map is [ARCHITECTURE.md](../ARCHITECTURE.md). The 2026-10-19 inspection, including its older metric read, stays in [CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md).

## Two forecasts, named apart

```text
GET /api/market/overview and GET /api/predict/{symbol}
  DeskPredictor
    champion files present → inference.predict_symbol
      LightGBM booster (champion_lgbm.txt) on the frozen OHLCV panel
      payload.model = lightgbm
      payload.as_of / last_close = the panel bar that was scored
    champion stack unavailable → Predictor (backend/artifacts LSTM)

GET /api/research/backtest/...
  predicted_returns_from_windows → DeskPredictor._predict_scaled
    returns LSTM only. Does not call predict_symbol.
```

The live quote (`price`, quote `as_of`) stays on the quote object. `DeskPredictor.detail` and `summaries` copy `as_of`, `last_close`, and `model` from `predict_symbol`. They do not stamp the live bar date or the live close onto the forecast.

`predict_symbol` scores the last panel row whose features are present. That row's `target_return` is null, because the next close has not printed. The row is still the one that is scored.

## What the id and the hit rate are

The booster that runs is LightGBM. The payload `model` is `lightgbm`. It is not `evaluation_report.json`'s `champion_model` (`arima_111`).

When a hit rate is attached, `confidence` is `pooled_model_comparison.lightgbm.directional_accuracy` and `confidence_source` names that field. It is not momentum's directional accuracy and not `arima_111`'s. See [evaluation-reports.md](evaluation-reports.md) and [MODEL_CARD.md](../MODEL_CARD.md). The card is the returns LSTM. The desk hint, when champion files exist, is not that model.

Research copy in the UI stays LSTM because that page backtests `_predict_scaled`. Markets and the symbol page show the payload model id.

Field list: [API_SPEC.md](../API_SPEC.md) (`prediction` summary and `GET /api/predict/{symbol}`). Promotion of `backend/artifacts` is unchanged: [RETRAIN_POLICY.md](../RETRAIN_POLICY.md).

## What this split does not do

A champion miss for one symbol leaves that hint empty. It does not fill the miss from the LSTM. Scoring the live Yahoo bar, lagging US macro features, and aliasing `/evaluation` are later work ([known-issues.md](known-issues.md), [engineering-roadmap.md](engineering-roadmap.md)).
