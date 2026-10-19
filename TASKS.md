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

## Phase 3+ (backlog)

- [ ] Walk-forward / rolling retrain methodology (document + optional script)
- [ ] Frontend smoke test (Playwright) with mocked API
- [ ] Indian cost model + backtest module
- [ ] Licensed India daily data feed
- [ ] Docker / production deploy manifests
- [ ] Program docs: `AGENTS.md`, `VISION.md`, `PRD.md`, etc.
