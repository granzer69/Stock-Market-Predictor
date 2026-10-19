# Architecture delta (Phases 8–12)

Supplements [ARCHITECTURE.md](ARCHITECTURE.md) and [CODEBASE_AUDIT.md](CODEBASE_AUDIT.md) for routes and ops added after Phase 7.

## API surface (desk)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/config` | Runtime flags: data provider, failover, portfolio cap, paper costs, default backtest fill, model card URL |
| GET | `/api/universe/nifty50` | Static Nifty 50 metadata for UI pickers |
| GET | `/api/research/backtest/portfolio` | Shared-cash portfolio backtest (register **before** `{symbol}` route) |
| GET | `/api/research/backtest/{symbol}` | Single-name long-only backtest with India costs |
| GET | `/api/health` | Liveness + `model` ready flag |

Query params on research routes: `period`, optional `fill` (`close` \| `next_close`), portfolio `symbols` (comma-separated).

Legacy evaluation routes (`/evaluation`, `/backtest`, `/predict` without `/api`) remain for the bundled LightGBM evaluation stack when CSV artifacts are present.

## Configuration (`app_config.py`)

| Env | Role |
|-----|------|
| `CORS_ORIGINS` | Comma-separated browser origins for CORSMiddleware |
| `MARKET_DATA_PROVIDER` | `yahoo` (default) or `nse_csv` |
| `MARKET_DATA_FAILOVER` | Yahoo ↔ CSV fallback for missing symbols |
| `NSE_CSV_DIR` | Licensed/curated daily CSV root |
| `PAPER_APPLY_INDIA_COSTS` | Apply delivery cost model to paper fills |
| `PAPER_DB_PATH` | SQLite paper book location |
| `BACKTEST_FILL` | Default `fill` when query param omitted |
| `RESEARCH_MAX_CONCURRENT` | In-process cap on concurrent research backtests |

## Middleware (`http_middleware.py`)

- **RequestContextMiddleware** — structured access log + `X-Request-Id`
- **ResearchRateLimitMiddleware** — 429 when concurrent backtests exceed limit

## Data plane

- `data_quality.validate_ohlcv_frame` — pre-backtest sanity checks
- `data_providers.failover_fetch` — primary provider with optional secondary
- Governance docs: [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md), [CORPORATE_ACTIONS.md](CORPORATE_ACTIONS.md), [UNIVERSE_MAINTENANCE.md](UNIVERSE_MAINTENANCE.md)

## ML / ops

- [RETRAIN_METRICS_DIFF.md](RETRAIN_METRICS_DIFF.md) — human promotion checklist
- `.github/workflows/drift-check.yml` — scheduled walk-forward report artifact
- `DeskPredictor` — LightGBM champion for live quotes when available; LSTM drives research backtests

## Frontend

- `/research` — single + portfolio backtests, export, fill mode, model card link via `/api/config`
