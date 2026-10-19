# Tasks — Bharat Desk program

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Repository audit

- [x] Inspect frontend, backend, ML, tests, deployment
- [x] Publish [CODEBASE_AUDIT.md](CODEBASE_AUDIT.md), [ARCHITECTURE.md](ARCHITECTURE.md)
- [x] User approval to proceed

---

## Phase 1 — Hardening (smallest safe slice)

- [x] **P1-1** FastAPI smoke tests with mocked market + predictor (`backend/tests/test_api.py`, `conftest.py`) — **20** total pytest tests, no live Yahoo in API tests
- [x] **P1-2** [API_SPEC.md](API_SPEC.md) from `backend/main.py`
- [x] **P1-3** [MODEL_CARD.md](MODEL_CARD.md) from `metrics.json` + training code
- [x] **P1-4** GitHub Actions [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — `pytest` on push/PR

**Out of scope (unchanged):** LSTM retrain, new features, broker integration.

---

## Phase 2 — Training integrity + OpenAPI

- [x] **P2-1** `shuffle=False` in `model.fit`; record `training_shuffle` / `fit_validation_split` in `metrics.json`; retrain artifacts
- [x] **P2-2** `backend/scripts/export_openapi.py` → repo-root `openapi.json`; CI export step; tests (`test_train_samples.py`, `test_openapi_export.py`) — **22** pytest tests

**Out of scope (unchanged):** walk-forward backtest module, Playwright, licensed data, Docker.

---

## Phase 3 — Evaluation + UI smoke + research foundations

- [x] **P3-1** [WALK_FORWARD.md](WALK_FORWARD.md), [`walk_forward.py`](backend/walk_forward.py), [`walk_forward_report.py`](backend/scripts/walk_forward_report.py); tests
- [x] **P3-2** Playwright smoke tests (`frontend/e2e/`) with mocked `/api/*`; CI job `frontend-e2e`
- [x] **P3-3** [BACKTEST_SPEC.md](BACKTEST_SPEC.md) + [`india_costs.py`](backend/india_costs.py) (not wired to paper book)
- [x] **P3-4** [AGENTS.md](AGENTS.md), [VISION.md](VISION.md)

**Out of scope (unchanged):** licensed NSE feed, Docker manifests, full backtest engine, `PRD.md`.

---

## Phase 4 — Backtest, retrain CLI, deploy sketch

- [x] **P4-1** `backend/backtest/` engine + `run_backtest.py`; tests; spec updated
- [x] **P4-2** `train_and_save()` + `walk_forward_retrain.py` (truncated history, separate artifact dir)
- [x] **P4-3** `data_providers.py` (`YahooHistoryProvider`, `LicensedIndiaDailyProvider` stub)
- [x] **P4-4** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` (standalone Next)
- [x] **P4-5** [PRD.md](PRD.md)

**Out of scope (unchanged):** real licensed NSE integration, scheduled cloud retrain, production TLS/HA.

---

## Phase 5 — Data adapter, research UI, retrain ops, deploy docs

- [x] **P5-1** `LicensedIndiaDailyProvider` (CSV bundle + `NSE_CSV_DIR` / `MARKET_DATA_PROVIDER=nse_csv`)
- [x] **P5-2** `GET /api/research/backtest/{symbol}` + `/research` UI panel
- [x] **P5-3** [RETRAIN_POLICY.md](RETRAIN_POLICY.md) + [`.github/workflows/model-retrain.yml`](.github/workflows/model-retrain.yml) (artifact upload, no auto-promote)
- [x] **P5-4** [DEPLOY.md](DEPLOY.md), [vercel.json](vercel.json)

**Out of scope (unchanged):** vendor API SDK, auto-promotion of CI models, managed TLS appliances.

---

## Phase 6+ (backlog)

- [ ] Backtest equity curve chart in UI
- [ ] Multi-symbol portfolio backtest in API
- [ ] Feature flags for `nse_csv` per environment in hosted deploy
