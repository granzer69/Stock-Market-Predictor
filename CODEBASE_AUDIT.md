# Codebase audit — Bharat Desk (Phase 0)

**Audit date:** 2026-10-19 (UTC)  
**Branch inspected:** `cursor/india-lstm-desk-1e7e` (commits `916819d`, `29cdc5e` ahead of `main`)  
**Auditor:** Cursor agent (repository inspection + commands below; no application code changes in this phase)

## Prerequisite documents

The workflow requested reading `AGENTS.md`, `VISION.md`, and `CURSOR_WORKFLOW.md` first. **Those files are not present** in this repository on `main` or the current feature branch (verified via `git ls-tree` and workspace search). This audit uses the implemented code, [README.md](README.md), and the user’s Phase 0 scope only.

## Commands run (evidence)

| Command | Result |
|---------|--------|
| `python3 -m pytest -q` (repo root) | **7 passed** in ~0.9s (`backend/tests/`) |
| `python3` read `backend/artifacts/metrics.json` | `directional_accuracy` ≈ **0.482**, `mae_log_return` ≈ **0.01203**, `naive_mae_log_return` ≈ **0.01200**, `symbols`: 50, `train_rows`: 46635 |
| Workspace listing | `backend/artifacts/model.keras` (~134 KB), `scaler.joblib`, `metrics.json` present; `backend/cache/` ~2.5 MB; `backend/paper_trading.db` present locally (gitignored) |

No HTTP integration tests, frontend test runner, or CI workflow files were found in the repo.

## Product surface (as-built)

### Frontend (Next.js 15, React 19)

| Route | Component | API usage |
|-------|-----------|-----------|
| `/` | `components/overview.tsx` | `GET /api/market/overview` |
| `/stock/[symbol]` | `components/stock-desk.tsx` | `GET /api/market/history/{symbol}`, `GET /api/predict/{symbol}` |
| `/portfolio` | `components/portfolio-desk.tsx` | `GET /api/portfolio`, `GET /api/orders`, `POST /api/orders` (via ticket on stock page) |

Shared: `components/site-header.tsx` (disclaimer, IST clock, `GET /api/market/globals` tape), `lib/api.ts` (same-origin `API_URL` default `""`), `next.config.mjs` rewrites `/api/*` → `http://127.0.0.1:8000/api/*`.

Charts: `lightweight-charts` (OHLCV), Recharts (comparison, equity curve).

**No** `frontend` unit/e2e tests located.

### Backend (FastAPI)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/api/health` | `health` | `{ ok, model }` |
| GET | `/api/market/overview` | `overview` | Nifty 50 quotes + batch predictions + model summary |
| GET | `/api/market/globals` | `globals_tape` | Macro/index series |
| GET | `/api/market/history/{symbol}` | `history` | `period` ∈ `6mo,1y,2y,5y`; bars + SMA20/50 |
| GET | `/api/predict/{symbol}` | `predict` | Equity only; 503 if model missing |
| GET | `/api/portfolio` | `portfolio` | Marks positions with latest quotes |
| GET | `/api/orders` | `orders` | Blotter |
| POST | `/api/orders` | `create_order` | Body: `symbol`, `side`, `qty`; fill at quote price |

CORS: `localhost:3000`, `127.0.0.1:3000` only.

**Legacy US demo API** (`/predict`, `/chart`, `/realtime` without `/api` prefix) is **not** in current `backend/main.py`. Legacy artifacts remain on disk (see below).

### ML pipeline

- **Train:** `backend/train_lstm.py` — downloads 5y daily via `yfinance_fetcher`, builds 60-day log-return windows, pooled LSTM (32→16), `StandardScaler`, saves `backend/artifacts/*`.
- **Infer:** `backend/predictor.py` — loads `model.keras`, `scaler.joblib`, `metrics.json`; signals via `features.signal_from_move` (threshold 0.003); “confidence” = per-symbol or global holdout directional accuracy from metrics file.
- **Features:** `backend/features.py` — univariate log returns, clip ±0.2.

### Market data

- **Source:** Yahoo Finance through `yfinance` (`backend/market_data.py`).
- **Env:** `YF_DISABLE_CURL_CFFI=1` set in `market_data.py` (documented reason: TensorFlow + curl_cffi interaction).
- **TTL:** history 12h, quotes 15m; disk under `backend/cache/` (gitignored).
- **Universe:** `backend/universe.py` — 50 Nifty names + 9 macro/index tickers (static list, Oct 2026 composition including `BSE`, `TMPV`).

### Paper trading

- `backend/portfolio.py` — SQLite `paper_trading.db`, ₹10,00,000 starting cash, integer shares, average cost, realized/unrealized in snapshot.

### Legacy / parallel stacks (preserve awareness, not wired to Bharat UI)

| Asset | Location | Status |
|-------|----------|--------|
| Streamlit US upload demo | [main.py](main.py) | Expects `stock_predictor_model.h5`, `scaler.save` in CWD |
| Old Keras + CSV | `backend/stock_predictor_model.h5`, `backend/scaler.save`, `backend/top50_stocks_data.csv`, `backend/sample_stock_data.csv` | Not used by `backend/main.py` |
| Notebook | `Stock_Market_Predictor.ipynb` | Historical training exploration |

## Functionality to preserve (regression-sensitive)

1. Nifty 50 overview with LSTM columns and model summary strip.
2. Macro tape in header (`/api/market/globals`).
3. Symbol history periods and chart + trade ticket + comparison chart.
4. Paper buy/sell validation (cash, share count) and portfolio/equity curve.
5. Same-origin `/api` proxy via Next rewrites for single-port deploy.
6. Offline-ish operation when cache warm (no hard dependency on live Yahoo for every request).
7. Committed model artifacts so API can start without retraining.

## Tests (current)

**`backend/tests/test_market_and_model.py`**

- Disk cache hit for history (injected fetcher).
- Quote cache hit (single network fetch for two symbols).
- MultiIndex Yahoo frame parsing.
- `build_inference_batch` shape + `scale_windows` shape.

**`backend/tests/test_portfolio.py`**

- Buy rejected when cash insufficient.
- Sell rejected when shares insufficient.
- Average cost and unrealized PnL after two buys.

**API tests (Phase 1):** `backend/tests/test_api.py` — 13 smoke tests with `FakeMarket` / `FakePredictor` (no live Yahoo, Keras `load` patched). See [API_SPEC.md](API_SPEC.md).

**Remaining gaps:** No live `yfinance` contract tests, no frontend tests, no training reproducibility test, no OpenAPI export in CI.

## Data leakage and methodology risks (verified from code)

| Issue | Evidence | Severity |
|-------|----------|----------|
| **Training shuffle across time** | `model.fit(..., shuffle=True)` in `train_lstm.py` | Inflates training/val loss; holdout per symbol is last 20% **not** shuffled into train, but scaler is fit on all pre-holdout rows pooled across symbols |
| **Pooled global scaler** | `scaler.fit(x_train.reshape(-1, 1))` on concatenated symbols | Cross-symbol distribution in one scaler; not leakage but homogenizes tickers |
| **Univariate close-only model** | Only `Close` → log returns in train/infer | Macro tape in UI is not model input |
| **Holdout evaluation** | Per-symbol temporal 80/20 in `build_samples` | Reasonable for reported `metrics.json`; not walk-forward |
| **UI “comparison” series** | `predictor.detail` runs model on last ~30 historical windows on **full** cached history | In-sample visualization for UX; not a claim of OOS performance on those points unless user understands overlap with training era |
| **“Confidence”** | Holdout directional hit rate | Not calibrated probability; documented in README |

Reported holdout **does not beat** naive zero-return MAE (~0.01203 vs ~0.01200) and directional accuracy **below 50%** (~48.2%).

## Deployment and operations (observed)

- **Documented run:** `uvicorn` on backend port 8000; `pnpm dev` on 3000; optional `train_lstm.py`.
- **No** `Dockerfile`, `docker-compose`, GitHub Actions, or `environment.json` in repo.
- **Dependencies:** `backend/requirements.txt`; frontend `package.json` (`lightweight-charts` added).
- **Secrets:** None required for Yahoo path; no broker keys.
- **Production gaps:** No health beyond `/api/health`, no structured logging, no rate limits, SQLite single-writer, model path fixed, CORS localhost-only.

## Unknowns / not verified in this audit

- Live Yahoo reliability in target deployment region (only prior agent experience; no fetch run logged in this audit session).
- Whether PR #3 merge state matches local branch.
- Legal/commercial packaging (no `RISK_AND_COMPLIANCE.md` in repo).
- Performance of `/api/market/overview` cold-cache (50 symbols × 2y history + predict batch) — not load-tested.

## Phase 0 conclusion

The repository contains a **coherent Bharat Desk vertical slice** (Indian universe, LSTM artifacts, FastAPI, Next UI, paper book) on the feature branch, with **small but real** unit tests and **honest** holdout metrics that show **weak predictive edge**. Enterprise-style docs (`AGENTS.md`, `API_SPEC.md`, etc.) are **not** in tree; only this audit pack is being introduced for Phase 0 tracking files.

**Application code was not modified during this audit.**
