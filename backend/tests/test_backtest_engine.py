"""Backtest engine (synthetic bars, no Yahoo)."""

import numpy as np

from backtest.engine import BacktestConfig, run_long_only_backtest
from backtest.report import equal_weight_buy_hold, max_drawdown, summarize_result
from backtest.signals import signals_from_predicted_returns
import pandas as pd


def test_long_only_round_trip_with_costs():
    dates = [f"2024-01-{i:02d}" for i in range(1, 8)]
    closes = np.array([100.0, 101, 102, 103, 104, 103, 102])
    signals = ["HOLD", "BUY", "HOLD", "HOLD", "SELL", "HOLD", "HOLD"]
    result = run_long_only_backtest(dates, closes, signals, BacktestConfig(starting_cash=10_000))
    assert result.trade_count == 2
    assert result.total_costs_inr > 0
    assert result.ending_equity != 10_000


def test_signals_follow_threshold():
    preds = np.array([0.01, -0.01, 0.0])
    signals = signals_from_predicted_returns(preds, threshold=0.003)
    assert signals == ["BUY", "SELL", "HOLD"]


def test_equal_weight_benchmark_rises_with_flat_prices():
    frame_a = pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"], "Close": [100.0, 100.0]})
    frame_b = pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"], "Close": [200.0, 200.0]})
    _, curve = equal_weight_buy_hold({"A": frame_a, "B": frame_b}, starting_cash=10_000)
    assert curve[-1]["equity"] == 10_000
    assert max_drawdown(curve) == 0.0


def test_summarize_result_keys():
    dates = ["2024-01-01", "2024-01-02"]
    closes = np.array([100.0, 101.0])
    result = run_long_only_backtest(dates, closes, ["HOLD", "HOLD"])
    summary = summarize_result(result)
    assert "cagr" in summary and "max_drawdown" in summary
