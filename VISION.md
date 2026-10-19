# Vision — Bharat Desk

## Goal

A fast, readable **India-first** market desk for learning and experimentation: see Nifty 50 quotes, a transparent next-close **model hint**, world context, and a **paper** portfolio in rupees—without routing orders to an exchange.

## Principles

1. **Honest metrics** — publish holdout stats; distinguish UI confidence from calibrated probability.
2. **Paper only by default** — fills at available closes; costs optional in research backtests.
3. **Daily bar realism** — no pretense of intraday alpha on free delayed data.
4. **Small, inspectable stack** — FastAPI + SQLite book + one global LSTM; docs and OpenAPI stay in sync.

## Near-term roadmap

See [TASKS.md](TASKS.md): walk-forward evaluation, frontend smoke tests, India cost backtest engine, licensed data, Docker deploy, deeper program docs.

## Non-goals

SEBI registration, live brokerage, options automation, or marketing model output as guaranteed returns.
