"""Shared-cash portfolio backtest across multiple symbols."""

from __future__ import annotations

from backtest.engine import BacktestConfig, BacktestResult, _max_buy_qty
from india_costs import delivery_turnover_cost_inr


def run_portfolio_backtest(
    timeline: list[str],
    prices: dict[str, dict[str, float]],
    signals: dict[str, dict[str, str]],
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """One cash pool; per day process symbols alphabetically (long-only, whole shares)."""
    cfg = config or BacktestConfig()
    params = cfg.cost_params
    symbols = sorted(signals.keys())
    cash = float(cfg.starting_cash)
    positions: dict[str, int] = {}
    total_costs = 0.0
    trades = 0
    wins = 0
    curve: list[dict] = []

    for day in timeline:
        for symbol in symbols:
            price = prices.get(symbol, {}).get(day)
            if price is None or price <= 0:
                continue
            side = signals[symbol].get(day, "HOLD").upper()
            qty = positions.get(symbol, 0)
            if side == "BUY" and qty == 0:
                buy_qty = _max_buy_qty(cash, price, params)
                if buy_qty > 0:
                    notional = buy_qty * price
                    friction = delivery_turnover_cost_inr("BUY", notional, params)
                    cash -= notional + friction
                    total_costs += friction
                    positions[symbol] = buy_qty
                    trades += 1
            elif side == "SELL" and qty > 0:
                notional = qty * price
                friction = delivery_turnover_cost_inr("SELL", notional, params)
                cash += notional - friction
                total_costs += friction
                trades += 1
                positions[symbol] = 0

        equity = cash
        for symbol, qty in positions.items():
            if qty <= 0:
                continue
            mark = prices.get(symbol, {}).get(day)
            if mark is not None:
                equity += qty * mark
        curve.append({"time": day, "equity": round(equity, 2), "cash": round(cash, 2)})

    ending = curve[-1]["equity"] if curve else cfg.starting_cash
    return BacktestResult(
        starting_cash=cfg.starting_cash,
        ending_equity=ending,
        total_costs_inr=round(total_costs, 2),
        trade_count=trades,
        win_count=wins,
        equity_curve=curve,
        dates=list(timeline),
    )
