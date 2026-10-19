"""Long-only, whole-share backtest at the daily close."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from features import SIGNAL_THRESHOLD
from india_costs import IndiaEquityCostParams, delivery_turnover_cost_inr


@dataclass
class BacktestConfig:
    starting_cash: float = 1_000_000.0
    signal_threshold: float = SIGNAL_THRESHOLD
    cost_params: IndiaEquityCostParams | None = None


@dataclass
class BacktestResult:
    starting_cash: float
    ending_equity: float
    total_costs_inr: float
    trade_count: int
    win_count: int
    equity_curve: list[dict] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)


def _max_buy_qty(cash: float, price: float, params: IndiaEquityCostParams | None) -> int:
    if cash <= 0 or price <= 0:
        return 0
    qty = int(cash // price)
    while qty > 0:
        notional = qty * price
        friction = delivery_turnover_cost_inr("BUY", notional, params)
        if notional + friction <= cash:
            return qty
        qty -= 1
    return 0


def run_long_only_backtest(
    dates: list[str],
    closes: np.ndarray,
    signals: list[str],
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Act on each day's signal at that day's close (long-only, flat or one open lot)."""
    if len(dates) != len(closes) or len(closes) != len(signals):
        raise ValueError("dates, closes, and signals must align")
    cfg = config or BacktestConfig()
    params = cfg.cost_params

    cash = float(cfg.starting_cash)
    qty = 0
    avg_cost = 0.0
    total_costs = 0.0
    trades = 0
    wins = 0
    curve: list[dict] = []

    for day, price, signal in zip(dates, closes, signals):
        price = float(price)
        if price <= 0:
            raise ValueError("closes must be positive")

        side = signal.upper()
        if side == "BUY" and qty == 0:
            buy_qty = _max_buy_qty(cash, price, params)
            if buy_qty > 0:
                notional = buy_qty * price
                friction = delivery_turnover_cost_inr("BUY", notional, params)
                cash -= notional + friction
                total_costs += friction
                qty = buy_qty
                avg_cost = price
                trades += 1
        elif side == "SELL" and qty > 0:
            notional = qty * price
            friction = delivery_turnover_cost_inr("SELL", notional, params)
            cash += notional - friction
            total_costs += friction
            pnl = (price - avg_cost) * qty - friction
            if pnl > 0:
                wins += 1
            qty = 0
            avg_cost = 0.0
            trades += 1

        equity = cash + qty * price
        curve.append({"time": day, "equity": round(equity, 2), "cash": round(cash, 2), "qty": qty})

    ending = curve[-1]["equity"] if curve else cfg.starting_cash
    return BacktestResult(
        starting_cash=cfg.starting_cash,
        ending_equity=ending,
        total_costs_inr=round(total_costs, 2),
        trade_count=trades,
        win_count=wins,
        equity_curve=curve,
        dates=list(dates),
    )


def merge_portfolio_equity(curves: list[list[dict]], dates: list[str]) -> list[dict]:
    """Sum per-symbol equity curves that each started with full ``starting_cash`` (research aggregate)."""
    if not curves:
        return []
    by_day: dict[str, float] = {day: 0.0 for day in dates}
    for curve in curves:
        for point in curve:
            by_day[point["time"]] = by_day.get(point["time"], 0.0) + float(point["equity"])
    return [{"time": day, "equity": round(by_day[day], 2)} for day in dates if day in by_day]
