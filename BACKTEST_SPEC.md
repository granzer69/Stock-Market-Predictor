# Backtest spec (Phase 3 draft)

Paper trading in the app fills at **last close** with **no** statutory costs. This spec defines a future **offline backtest** module for signal research on Nifty 50 daily bars.

## Scope

- **In:** Long-only delivery simulation, whole shares, INR, costs from [`india_costs.py`](backend/india_costs.py).
- **Out:** Intraday, margin, F&O, shorting, borrow, corporate actions, circuit limits, liquidity constraints.

## Inputs

| Input | Source |
|-------|--------|
| OHLCV daily | Yahoo today; licensed NSE/BSE feed later |
| Signals | LSTM `BUY`/`SELL`/`HOLD` from [`features.signal_from_move`](backend/features.py) |
| Starting cash | Default ₹10,00,000 (match paper book) |

## Execution model (proposed)

1. Signal observed at close *t* (model uses history through *t*).
2. Order fills at close *t* (same as paper desk—optimistic; optional open+*t+1* fill flag later).
3. Apply `delivery_turnover_cost_inr(side, qty * price)` on each fill.
4. Position: integer qty, average cost, cash ledger.

## Metrics (proposed)

- CAGR, max drawdown, Sharpe (daily), hit rate, turnover, total costs.
- Benchmark: equal-weight Nifty 50 buy-and-hold on same calendar.

## Module layout (future)

```
backend/backtest/
  engine.py      # event loop over dates
  signals.py     # adapter from predictor or CSV
  report.py      # JSON + optional equity curve
```

## Paper book parity

[`portfolio.py`](backend/portfolio.py) remains the live UI book. Backtest code must not mutate `paper.db` without an explicit flag.
