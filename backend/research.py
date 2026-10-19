"""Shared research helpers (API + CLI)."""

from __future__ import annotations

import pandas as pd

from backtest.engine import BacktestConfig, run_long_only_backtest
from backtest.report import buy_and_hold_benchmark, max_drawdown, summarize_result
from backtest.signals import frame_to_closes, predicted_returns_from_windows
from predictor import Predictor


def backtest_from_frame(
    symbol: str,
    frame: pd.DataFrame,
    predictor: Predictor,
    period: str,
    config: BacktestConfig | None = None,
) -> dict:
    dates, closes = frame_to_closes(frame)
    if len(dates) < 65:
        raise ValueError("not enough history for backtest")
    signals, _ = predicted_returns_from_windows(predictor, closes)
    result = run_long_only_backtest(dates, closes, signals, config or BacktestConfig())
    strategy = summarize_result(result)
    bench_curve = buy_and_hold_benchmark(dates, closes, result.starting_cash)
    bench_end = bench_curve[-1]["equity"] if bench_curve else result.starting_cash
    return {
        "symbol": symbol,
        "period": period,
        "strategy": strategy,
        "benchmark": {
            "kind": "buy_and_hold",
            "ending_equity": bench_end,
            "total_return": (bench_end - result.starting_cash) / result.starting_cash,
            "max_drawdown": max_drawdown(bench_curve),
        },
        "disclaimer": "Offline simulation with India delivery costs; not investment advice.",
    }
