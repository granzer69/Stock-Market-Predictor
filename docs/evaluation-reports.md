# Evaluation reports — committed numbers

Figures below are copied from committed files. This iteration did not refit a model and did not rewrite `backend/models/evaluation_report.json` or `backend/artifacts/metrics.json`. None of these figures is a claim that a model beats a coin flip.

## Returns LSTM — [MODEL_CARD.md](../MODEL_CARD.md)

Source: `backend/artifacts/metrics.json`, trained `2026-10-19T06:34:07.092506+00:00`. Research backtests use this bundle via `_predict_scaled`.

| Field | Committed value | Card rounding |
| --- | --- | --- |
| `directional_accuracy` | 0.4870381534751529 | 0.4870 |
| `mae_log_return` | 0.012051809898621074 | 0.012052 |
| `naive_mae_log_return` | 0.011987893123182505 | 0.011988 |
| `train_rows` | 46636 | |
| `symbols` | 50 | |

The card states the holdout MAE is not better than predicting zero, and directional accuracy is below one half.

[CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md) (2026-10-19) recorded an earlier read of about 0.482 directional accuracy, MAE about 0.01203, naive MAE about 0.01200, and `train_rows` 46635. That note stays as the audit's reading. The card matches the file that is in the tree now.

## Close-model report — `backend/models/evaluation_report.json`

Generated `2026-10-18T19:29:57.174939+00:00`. `production_model` is `lightgbm`. `champion_model` is `arima_111`. Those two fields were not rewritten.

Pooled block, as stored:

| Name | Directional accuracy | MAPE % | What the number is |
| --- | --- | --- | --- |
| lightgbm | 0.4707 | 1.4153 | Per-symbol one-step fits in that script, not a fresh score of `champion_lgbm.txt` |
| persistence | 0.0 | 1.225 | Level MAPE versus the last close. Direction was forced to 0 in the script |
| ma20 | 0.5061 | 3.5496 | Prior 20 closes versus the next close |
| arima_111 | 0.5066 | 11.8258 | One multi-step forecast from a single origin, then scored day by day |
| momentum | 1.0 | NaN | Same-bar sign. Invalid as a baseline. See below |
| legacy_lstm_trained | | 1.3925 (`pooled_test_mape_pct`) | Close LSTM in `backend/models/metrics.json` |

`gru_reliance_sample` in the same file: MAPE 1018.7255, RMSE 0.0531, directional accuracy 0.5251, `n_samples` 221. The MAPE is on raw returns.

Nifty buy-and-hold block in that file: CAGR -0.0876, Sharpe -0.6008, max drawdown -0.1556. That block is the last 20% of the macro `nifty` column inside the evaluation script, cost-free.

## Momentum label

`momentum_directional_accuracy` in `ml/metrics.py` (called from `scripts/run_evaluation.py`) scores momentum as the sign of the **previous** return. On an alternating close series that lagged sign does not match the next return (directional accuracy 0). The committed report still says pooled momentum directional accuracy **1.0**, because this iteration does not re-run the script or replace the JSON. A later run would write a different momentum row. `GET /evaluation` does not serve that 1.0 row today: bare `NaN` in the same file makes the handler fail with `ValueError: Out of range float values are not JSON compliant: nan`. This iteration does not fix that route.

## What a desk hint copies

`inference.predict_symbol` sets `confidence` from the report's lightgbm row (0.4707 in this file). That figure is the evaluation report's pooled directional accuracy across per-symbol LightGBM fits. It is not the saved `champion_lgbm.txt` booster's own holdout and not a per-name rate. `confidence_source` is `evaluation_report.pooled_model_comparison.lightgbm.directional_accuracy`. The payload does not copy 1.0 or 0.5066. `model` on that payload is `lightgbm`.

Retrain and promotion rules for the LSTM bundle are [RETRAIN_POLICY.md](../RETRAIN_POLICY.md). Response fields are [API_SPEC.md](../API_SPEC.md).
