# Decision log

Status of iteration 1: **in review** until QA. Entries here are the choices in that iteration, not a promotion of any model.

## 2026-10-27 — Name the booster that ran

**Decision.** `inference.predict_symbol` sets `model` to `lightgbm`, the booster loaded from `champion_lgbm.txt`. It does not copy `evaluation_report.json` `champion_model` (`arima_111`).

**Why.** The report's champion and the booster that executes were different objects. The desk was showing one name for the other's number.

**Not decided.** Do not switch the desk to ARIMA because 0.5066 is the highest directional accuracy in that table. That fit is a multi-step level forecast with pooled MAPE 11.8258. Do not add another model.

## 2026-10-27 — Hit rate source is the LightGBM row

**Decision.** When the payload includes a hit rate, `confidence` is `pooled_model_comparison.lightgbm.directional_accuracy` (0.4707 in the committed file) and `confidence_source` names that field. Momentum's 1.0 and `arima_111`'s 0.5066 are not used.

**Why.** A perfect momentum score was the sign of the return being graded. Publishing it, or the ARIMA direction score, on a LightGBM forecast misstates the hint.

## 2026-10-27 — Forecast bar stays the panel bar

**Decision.** `as_of` and `last_close` on the forecast are the panel row `predict_symbol` scored. The live quote date and close stay on the quote. Markets and the symbol page show the payload model id. Research copy stays LSTM.

**Why.** Overwriting the forecast as-of with the live bar made a panel forecast look like the next close of the candle on screen. Research still backtests the returns LSTM (`_predict_scaled`), so the research page keeps that name. See [MODEL_CARD.md](../MODEL_CARD.md) and [API_SPEC.md](../API_SPEC.md).

## 2026-10-27 — Momentum baseline is the previous return

**Decision.** `momentum_directional_accuracy` in `scripts/run_evaluation.py` uses the sign of the previous return. The rest of that script is unchanged. The committed report is not regenerated.

**Why.** The stored 1.0 is not a usable ranking. Rewriting the report would be a new measurement. This iteration only stops the next run from grading a return against itself.

## 2026-10-27 — Do not retune

**Decision.** No change to LSTM depth, the 60-day window, the ±0.2 clip, the 0.003 threshold, the loss, artifact weights, the backtest engine, or the paper book. No refit of LightGBM.

**Why.** The committed LSTM holdout is already on the weak side of its naive MAE (0.012051809898621074 versus 0.011987893123182505). [RETRAIN_POLICY.md](../RETRAIN_POLICY.md) still gates promotion of `backend/artifacts`. [CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md) remains the 2026-10-19 record.
