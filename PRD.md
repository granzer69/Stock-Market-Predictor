# PRD — Bharat Desk (research desk)

## Problem

Retail and student investors in India want a **fast** view of Nifty 50 action, a **transparent** machine-learning hint for the next session, and a **safe** place to practice orders—in rupees—without broker risk.

## Users

- Self-directed learners and hobbyist quant researchers
- Not registered investment advisers or institutional traders

## Goals

| Goal | Measure |
|------|---------|
| See Nifty 50 + macro context | Overview loads with tape and table |
| Understand model limits | Holdout metrics visible; disclaimer persistent |
| Practice execution | Paper book with INR cash and whole shares |
| Reproduce research | Docs, OpenAPI, offline backtest CLI |

## Non-goals

- Live order routing, KYC, or SEBI registration
- Intraday or derivatives automation
- Guaranteed or marketed alpha

## Core journeys

1. **Scan** — Open Markets, search a name, sort by change or model move.
2. **Drill down** — Symbol page: chart, prediction, optional paper ticket.
3. **Portfolio** — View cash, positions, equity curve; refresh marks.
4. **Research (CLI)** — `run_backtest.py`, `walk_forward_report.py`, optional `walk_forward_retrain.py`.

## Compliance copy (product)

- “Paper trading only” and “not investment advice” on every session (header).
- Model output is **not** a recommendation; confidence is holdout hit rate, not probability.
- Data from unofficial Yahoo feeds—may be delayed or wrong.

## Success (Phase 4+)

- Backtest engine matches [BACKTEST_SPEC.md](BACKTEST_SPEC.md)
- CI green: pytest + Playwright + OpenAPI export
- Optional Docker Compose for local demos

## Out of scope (future vendors)

Licensed NSE/BSE tick data ([`LicensedIndiaDailyProvider`](backend/data_providers.py)), production HA, mobile apps.
