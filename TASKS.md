# Tasks — Bharat Desk program

**Phase 0:** Audit only (no application code changes). **Status:** complete — see [PROGRESS.md](PROGRESS.md).

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Repository audit

- [x] Inspect frontend routes, components, API client, Next rewrites
- [x] Inventory FastAPI routes and lifespan dependencies
- [x] Trace LSTM train/infer path and artifact layout
- [x] Document market-data source, cache TTLs, env flags
- [x] Run `pytest`; record pass count
- [x] Read committed `metrics.json` (no invented metrics)
- [x] Note legacy Streamlit/US assets
- [x] Write [CODEBASE_AUDIT.md](CODEBASE_AUDIT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PROGRESS.md](PROGRESS.md)
- [ ] **User approval** before any Phase 1 application code

---

## Phase 1 — Proposed smallest safe slice (awaiting approval)

**Goal:** Harden what exists without changing product behavior or model architecture.

| ID | Task | Acceptance criteria (measurable) |
|----|------|----------------------------------|
| P1-1 | Add FastAPI smoke tests (`httpx`/`TestClient`) with **mocked** `PriceCache` + fixed `Predictor` fixture | `pytest` ≥ **10** tests; `/api/health`, `/api/portfolio`, order rejection paths covered; **no** live Yahoo in CI |
| P1-2 | Document API contract in `API_SPEC.md` generated from `backend/main.py` only | Every route in audit table has request/response fields; no undocumented endpoints |
| P1-3 | Add `MODEL_CARD.md` from `metrics.json` + `train_lstm.py` facts | Holdout accuracy, MAE vs naive, train date, feature list, known limitations copied from audit |
| P1-4 | CI workflow: `pytest` on push | GitHub Action job green on PR |

**Explicitly out of scope for P1:** retrain LSTM, new features, broker integration, shuffle=False retrain, walk-forward backtest.

---

## Phase 2+ (backlog — not scheduled)

- [ ] Walk-forward training protocol; disable `shuffle` for temporal splits
- [ ] `API_SPEC.md` / OpenAPI export alignment with frontend types
- [ ] Frontend smoke test (Playwright) against mocked API
- [ ] Indian cost model + backtest module per future `BACKTESTING_SPEC.md`
- [ ] Replace Yahoo with licensed daily feed (TBD vendor)
- [ ] Deployment: Docker + health/readiness for both processes

---

## Missing program docs (repo gap)

The following were named in the program charter but **are not in the repository** yet: `AGENTS.md`, `VISION.md`, `CURSOR_WORKFLOW.md`, `PRD.md`, `API_SPEC.md`, `BACKTESTING_SPEC.md`, etc. Phase 1 can add them incrementally from verified sources only.
