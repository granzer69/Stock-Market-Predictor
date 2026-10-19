# Changelog

## v0.1.0 — 2026-10-19

### Release gate (Phase 8)

- `CORS_ORIGINS` env wired through `app_config` and FastAPI CORS middleware
- [ARCHITECTURE_DELTA.md](ARCHITECTURE_DELTA.md) documents `/api/config`, `/api/universe/nifty50`, and research routes
- README changelog and deployment notes for production origins

### Ops (Phase 9)

- Docker Compose volumes for cache and paper DB path
- [BACKUP.md](BACKUP.md) and `backend/scripts/backup_paper_db.sh`
- Structured logging and `RESEARCH_MAX_CONCURRENT` rate limiting on research endpoints

### Data (Phase 10)

- `validate_ohlcv_frame`, `failover_fetch`, `validate_market_data.py` CLI
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md), [CORPORATE_ACTIONS.md](CORPORATE_ACTIONS.md), [UNIVERSE_MAINTENANCE.md](UNIVERSE_MAINTENANCE.md)

### ML integrity (Phase 11)

- [RETRAIN_METRICS_DIFF.md](RETRAIN_METRICS_DIFF.md) promotion template
- `.github/workflows/drift-check.yml` for scheduled walk-forward reports
- Product direction: LSTM desk (#3) remains primary for research backtests; LightGBM evaluation stack optional when artifacts exist

### Product (Phase 12)

- `fill` query param (`close` | `next_close`) on research backtests
- `PAPER_APPLY_INDIA_COSTS` for paper book
- Research UI fill selector and MODEL_CARD link via `/api/config`
