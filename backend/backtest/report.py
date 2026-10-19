"""Backtest metrics and benchmarks."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from backtest.engine import BacktestResult


def _equity_returns(curve: list[dict]) -> np.ndarray:
    values = np.asarray([point["equity"] for point in curve], dtype=np.float64)
    if len(values) < 2:
        return np.array([], dtype=np.float64)
    return np.diff(values) / values[:-1]


def max_drawdown(curve: list[dict]) -> float:
    if not curve:
        return 0.0
    peak = curve[0]["equity"]
    worst = 0.0
    for point in curve:
        equity = float(point["equity"])
        peak = max(peak, equity)
        if peak > 0:
            worst = min(worst, (equity - peak) / peak)
    return float(worst)


def cagr(result: BacktestResult, trading_days_per_year: float = 252.0) -> float:
    if not result.equity_curve:
        return 0.0
    start = result.starting_cash
    end = result.ending_equity
    if start <= 0 or end <= 0:
        return 0.0
    years = max(len(result.equity_curve) / trading_days_per_year, 1 / trading_days_per_year)
    return float((end / start) ** (1.0 / years) - 1.0)


def sharpe_ratio(curve: list[dict], trading_days_per_year: float = 252.0) -> float:
    rets = _equity_returns(curve)
    if len(rets) < 2:
        return 0.0
    std = float(np.std(rets))
    if std == 0:
        return 0.0
    return float(np.mean(rets) / std * math.sqrt(trading_days_per_year))


def hit_rate(result: BacktestResult) -> float:
    closed = result.trade_count // 2 if result.trade_count else 0
    if closed == 0:
        return 0.0
    return float(result.win_count / closed)


def turnover_ratio(result: BacktestResult) -> float:
    if not result.equity_curve:
        return 0.0
    avg_equity = float(np.mean([p["equity"] for p in result.equity_curve]))
    if avg_equity <= 0:
        return 0.0
    # Approximate: each trade leg moves ~one lot; use cost proxy from ending stats.
    return float(result.trade_count * result.starting_cash * 0.1 / avg_equity)


def summarize_result(result: BacktestResult) -> dict[str, Any]:
    return {
        "starting_cash": result.starting_cash,
        "ending_equity": result.ending_equity,
        "total_return": (result.ending_equity - result.starting_cash) / result.starting_cash,
        "cagr": cagr(result),
        "max_drawdown": max_drawdown(result.equity_curve),
        "sharpe": sharpe_ratio(result.equity_curve),
        "hit_rate": hit_rate(result),
        "trade_count": result.trade_count,
        "total_costs_inr": result.total_costs_inr,
        "turnover_ratio": turnover_ratio(result),
    }


def buy_and_hold_benchmark(
    dates: list[str],
    closes: np.ndarray,
    starting_cash: float,
) -> list[dict]:
    """Single-symbol buy at first close, hold through series."""
    if not dates:
        return []
    price0 = float(closes[0])
    if price0 <= 0:
        return []
    qty = int(starting_cash // price0)
    cash = starting_cash - qty * price0
    curve: list[dict] = []
    for day, price in zip(dates, closes):
        equity = cash + qty * float(price)
        curve.append({"time": day, "equity": round(equity, 2)})
    return curve


def equal_weight_buy_hold(
    frames: dict[str, pd.DataFrame],
    starting_cash: float,
) -> tuple[list[str], list[dict]]:
    """Buy equal-notional whole shares on the first common session; hold through last."""
    if not frames:
        return [], []

    aligned: list[pd.DataFrame] = []
    for symbol, frame in frames.items():
        piece = frame[["Date", "Close"]].copy()
        piece["Date"] = piece["Date"].astype(str)
        piece = piece.rename(columns={"Close": symbol})
        aligned.append(piece)

    panel = aligned[0]
    for piece in aligned[1:]:
        panel = panel.merge(piece, on="Date", how="inner")
    panel = panel.sort_values("Date")
    if panel.empty:
        return [], []

    dates = panel["Date"].tolist()
    symbols = [column for column in panel.columns if column != "Date"]
    first = panel.iloc[0]
    per_symbol_cash = starting_cash / len(symbols)
    holdings = {}
    cash = starting_cash
    for symbol in symbols:
        price = float(first[symbol])
        qty = int(per_symbol_cash // price)
        if qty <= 0:
            continue
        notional = qty * price
        cash -= notional
        holdings[symbol] = qty

    curve = []
    for _, row in panel.iterrows():
        equity = cash
        for symbol, qty in holdings.items():
            equity += qty * float(row[symbol])
        curve.append({"time": str(row["Date"]), "equity": round(equity, 2)})
    return dates, curve
