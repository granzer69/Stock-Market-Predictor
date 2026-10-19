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

## Phase 2+ (backlog)

- [ ] Walk-forward training; `shuffle=False` for temporal integrity
- [ ] OpenAPI export aligned with `API_SPEC.md` and frontend types
- [ ] Frontend smoke test (Playwright) with mocked API
- [ ] Indian cost model + backtest module
- [ ] Licensed India daily data feed
- [ ] Docker / production deploy manifests
- [ ] Program docs: `AGENTS.md`, `VISION.md`, `PRD.md`, etc.
