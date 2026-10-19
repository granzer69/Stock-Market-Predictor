# Progress log

## 2026-10-19 — Phase 2 complete

**Branch:** `cursor/india-lstm-desk-1e7e`  
**Scope:** Temporal training fix, OpenAPI export, tests + CI.

### Delivered

- `backend/train_lstm.py` — `shuffle=False`; metrics document shuffle and validation split
- Retrained `backend/artifacts/` (holdout directional accuracy ~**48.7%**; still ~coin-flip vs naive MAE)
- `backend/scripts/export_openapi.py`, committed `openapi.json` (7 paths)
- `backend/tests/test_train_samples.py`, `backend/tests/test_openapi_export.py`
- CI runs OpenAPI export after pytest; [MODEL_CARD.md](MODEL_CARD.md) and [API_SPEC.md](API_SPEC.md) updated

### Verification

- `python3 -m pytest -q` → **22 passed**

### Next

Phase 3 backlog: walk-forward methodology, Playwright e2e, Indian cost backtest (see [TASKS.md](TASKS.md)).

---

## 2026-10-19 — Phase 1 complete

**Branch:** `cursor/india-lstm-desk-1e7e`  
**Scope:** Tests, API spec, model card, CI. **No changes** to production API behavior or LSTM training.

### Delivered

- `backend/tests/conftest.py` — `FakeMarket`, `FakePredictor`, `TestClient` without Keras load or Yahoo
- `backend/tests/test_api.py` — 13 API smoke tests (health, overview, globals, history, predict, portfolio, orders)
- [API_SPEC.md](API_SPEC.md), [MODEL_CARD.md](MODEL_CARD.md)
- `.github/workflows/ci.yml` — Python 3.12, `pip install -r backend/requirements.txt`, `pytest -q`

### Verification

- `python3 -m pytest -q` → **20 passed** (7 unit + 13 API)

### Next

Phase 2 complete; Phase 3 backlog in [TASKS.md](TASKS.md).

---

## 2026-10-19 — Phase 0 audit complete

- Published audit architecture docs; **7** pytest tests at phase start.
- Prerequisite charter files (`AGENTS.md`, etc.) still absent from repo.
