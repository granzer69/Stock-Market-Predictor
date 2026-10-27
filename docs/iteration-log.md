# Iteration log

## Iteration 1 — forecast identity and the momentum label

**Status:** accepted

### Problem

Markets showed a LightGBM panel forecast as if it were the LSTM next close of the candle on screen. `DeskPredictor.detail` replaced the forecast `as_of` and base close with the live bar. `predict_symbol` dropped the last panel row because `target_return` is null, and it labeled the payload with `champion_model` (`arima_111`) and that row's directional accuracy (0.5066). The momentum baseline in `scripts/run_evaluation.py` was the sign of the return being graded, which is why the committed report shows directional accuracy 1.0.

### Why

A reader could compare three different objects — live quote, panel LightGBM, research LSTM — under one LSTM label. The 1.0 momentum row made every other directional score look worse than a useless baseline. Fixing the label does not require a new fit. The returns LSTM holdout is already recorded against predicting zero in [MODEL_CARD.md](../MODEL_CARD.md).

### Baseline

Committed numbers, unchanged by this iteration:

- Returns LSTM (`backend/artifacts/metrics.json`, 2026-10-19T06:34:07.092506+00:00): directional accuracy 0.4870381534751529, MAE 0.012051809898621074, naive MAE 0.011987893123182505, `train_rows` 46636.
- [CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md) earlier read: about 0.482, `train_rows` 46635. Left as history.
- Evaluation report (2026-10-18T19:29:57.174939+00:00): lightgbm directional accuracy 0.4707, MAPE 1.4153; arima_111 0.5066 and MAPE 11.8258; momentum 1.0. The file still says 1.0.

### Summary

- Forecast `as_of`, `last_close`, and `model` come from `predict_symbol`. The live quote is not copied onto them. A champion miss stays empty.
- The last feature row is scored without a non-null `target_return`. `model` is `lightgbm`. `confidence` is the LightGBM pooled hit rate and `confidence_source` names that field.
- Momentum in `scripts/run_evaluation.py` uses the previous return. The rest of the script, the report JSON, LSTM weights, the 0.003 threshold, the backtest engine, and the paper book are unchanged.
- The Markets column and the symbol page use the payload model id. Research copy still says LSTM, because research calls `_predict_scaled`.
- [API_SPEC.md](../API_SPEC.md) documents the fields `main.py` returns. [RETRAIN_POLICY.md](../RETRAIN_POLICY.md) is unchanged.

### Tests

- `backend/tests/test_forecast_provenance.py` — stub `predict_symbol` returns as-of 2026-10-16, base close 2400, predicted close 2410, model `lightgbm`, against a live bar 2026-10-27 / 2500. Research signals call `_predict_scaled` and do not call `predict_symbol`. A champion miss does not call the LSTM.
- `backend/tests/test_evaluation_labels.py` — alternating closes `100, 110, 100, 110, 100, 110` score momentum directional accuracy 0. A second toy series scores 0.5, so a constant 0 would fail. `predict_symbol` on an in-memory panel uses the last date, `model` `lightgbm`, and the report's LightGBM hit rate rather than 1.0 or 0.5066. No assertion that a model beats 0.5.
- `frontend/e2e/smoke.spec.ts` — overview row `prediction.model` `lightgbm` must not use the header `LSTM next`. Symbol page must not use `one-step LSTM close`.

### Measurements

No new holdout metric. The tests lock labels, not skill. Commands from this iteration, on the iteration branch:

- `python3 -m pytest -q` → **52 passed**, 1 warning (StarletteDeprecationWarning from `fastapi.testclient`), 4.24s.
- `cd frontend && pnpm test:e2e` → **5 passed** (10.3s on a cold dev server; 2.8s when re-run after the symbol-page sentence tweak). Both runs include the Markets header `lightgbm next` and the symbol heading `Next-session lightgbm forecast`.
- `python3 backend/scripts/export_openapi.py` runs inside `backend/tests/test_openapi_export.py` as part of the pytest command. It added the existing `GET /` route to `openapi.json`. Response bodies stay untyped. The new forecast fields are listed in [API_SPEC.md](../API_SPEC.md).

### Reviewer

Pending QA. Independent review verdict: revise. The revise below is in this same iteration. Re-review accepted the revise: [hint-provenance-rereview.md](/cursor/stores/bc-255b3324-964c-4a90-bd85-a3cd276fdc5f/internal/hint-provenance-rereview.md).

### Revise

- Momentum scoring lives in `ml/metrics.py`. The unit test imports that module and does not import `scripts/run_evaluation.py`, so CI can run pytest without `statsmodels`.
- Copy for 0.4707 says it is the evaluation report's pooled directional accuracy across per-symbol LightGBM fits. It is not this saved booster's holdout and not a per-name rate.
- A universe name with no panel forecast returns 404 `No champion forecast for this symbol`. A single miss stays empty and is not labeled `lstm`. If the champion stack cannot load, hints use the LSTM and `model` is `lstm`.
- `GET /evaluation` fails on bare `NaN` in `evaluation_report.json`. It does not serve the momentum 1.0 row. That route is still not fixed.
- An empty champion hint table uses the column header `Model next`, not `LSTM next`.

Commands for this revise, on the same branch, not pushed:

- `python3 -m pytest -q` → **54 passed**, 1 warning (`StarletteDeprecationWarning` from `fastapi.testclient`), 5.17s.
- Fresh interpreter with `sys.modules["statsmodels"]`, `statsmodels.tsa`, `statsmodels.tsa.arima`, and `statsmodels.tsa.arima.model` set to `None`, then `pytest.main(["-q"])` → **54 passed**, 1 warning, 4.24s. The suite does not import `scripts/run_evaluation.py`. `statsmodels` was not added to `backend/requirements.txt`.

### Risks

The hint is still the panel bar (last date in this checkout 2026-10-16), not the live close. The 0.4707 figure is the report's pooled per-symbol LightGBM directional accuracy, not a probability for that name and not a score of `champion_lgbm.txt`. The stored evaluation file still contains momentum 1.0 and bare `NaN`; `GET /evaluation` errors on that `NaN` and does not return the row. Empty hints remain for symbols missing from the panel, with an explicit no-forecast error.

### Decision

Accept. The re-review at [hint-provenance-rereview.md](/cursor/stores/bc-255b3324-964c-4a90-bd85-a3cd276fdc5f/internal/hint-provenance-rereview.md) accepted the revise. Do not treat this as a model promotion. See [decision-log.md](decision-log.md).

### Next

Iteration 2: split the `/evaluation` and `/backtest` documents from the FastAPI routes, without changing this forecast contract. See [engineering-roadmap.md](engineering-roadmap.md) and [known-issues.md](known-issues.md).

## Iteration 2 — Evaluation and Backtest documents

**Status:** in review

### Problem

`/evaluation` and `/backtest` were both Next pages and FastAPI routes. With `API_ORIGIN` set, middleware rewrote the documents to the API. Without it, the pages fetched those same paths and received HTML. `GET /evaluation` also failed strict JSON because `evaluation_report.json` contains bare `NaN`.

### Why

The header links are the screen that shows the stored baselines, including the momentum row iteration 1 left at 1.0. A reader could not open that screen under the documented deploy, and a strict client could not parse the report.

### Baseline

Unchanged files and figures from iteration 1. The evaluation file still has momentum directional accuracy 1.0, `NaN` MAPE and RMSE, and `champion_model` arima_111. Model weights, inference labels, the paper book, and `momentum_directional_accuracy` are not part of this change.

### Summary

- Middleware matches `/api/:path*` only. `/evaluation` and `/backtest` stay on Next when `API_ORIGIN` is set.
- The Evaluation page fetches `GET /api/evaluation`. The Backtest page fetches `GET /api/legacy/backtest`. FastAPI `GET /evaluation` and `GET /backtest` remain and return the same bodies.
- The HTTP payloads replace non-finite floats with JSON `null`. The file on disk is not regenerated. Momentum directional accuracy stays 1.0. The page says that row is the pre-fix same-return score, not a lagged baseline and not a champion. `champion_model` stays arima_111.

### Tests

- `backend/tests/test_evaluation_json.py` — `/evaluation` and `/api/evaluation` are equal, contain no `NaN`, keep momentum directional accuracy 1.0 with null MAPE and RMSE, and keep `champion_model` arima_111. The file on disk still contains `NaN`. `/backtest` and `/api/legacy/backtest` match for RELIANCE.
- `frontend/e2e/smoke.spec.ts` — mocks `GET /api/evaluation` and asserts the heading `Model evaluation`, the momentum annotation, and that the request path is `/api/evaluation`. Existing smoke tests stay.

### Measurements

No new holdout metric. The file on disk was not rewritten. Commands on this branch, not pushed:

- `python3 -m pytest -q` → **56 passed**, 1 warning (`StarletteDeprecationWarning` from `fastapi.testclient`), 4.47s. That run includes `backend/tests/test_evaluation_json.py` and `backend/scripts/export_openapi.py`, which added `GET /api/evaluation` and `GET /api/legacy/backtest` to `openapi.json`.
- `cd frontend && pnpm test:e2e` → **6 passed** (4.7s). The new case asserts the heading `Model evaluation` and a request to `/api/evaluation`. The five earlier smoke tests passed in the same run.
- With `API_ORIGIN=http://127.0.0.1:9`, `GET /evaluation` and `GET /backtest` on the Next server returned `text/html` containing `Model evaluation` and `Paper backtest`. `GET /api/market/overview` on that server returned 500, so `/api/*` was still proxied.

### Risks

The disk file still has bare `NaN`. A reader of the raw JSON, outside these routes, still sees it. The 1.0 row is still in the table, with the annotation beside it. The Backtest page still says "10bps cost · 5bps slippage" from the page copy, not from the payload.

### Decision

In review.

### Next

Not scheduled in this iteration. See [engineering-roadmap.md](engineering-roadmap.md).
