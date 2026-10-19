import numpy as np
import pandas as pd

from backtest.portfolio_engine import run_portfolio_backtest
from research import portfolio_backtest
from tests.conftest import FakePredictor, _ohlc_frame


def test_shared_cash_portfolio_runs():
    dates = [f"2024-01-{i:02d}" for i in range(1, 11)]
    prices = {
        "A.NS": {day: 100.0 for day in dates},
        "B.NS": {day: 200.0 for day in dates},
    }
    signals = {
        "A.NS": {day: "BUY" if day == dates[0] else "HOLD" for day in dates},
        "B.NS": {day: "HOLD" for day in dates},
    }
    result = run_portfolio_backtest(dates, prices, signals)
    assert result.ending_equity > 0
    assert len(result.equity_curve) == len(dates)


def test_portfolio_backtest_helper_two_symbols():
    frame_a = _ohlc_frame(90, 100.0)
    frame_b = _ohlc_frame(90, 200.0)
    payload = portfolio_backtest(
        {"A.NS": frame_a, "B.NS": frame_b},
        FakePredictor(),
        "1y",
        ["A.NS", "B.NS"],
    )
    assert payload["kind"] == "portfolio"
    assert len(payload["equity_curve"]) > 0
    assert len(payload["benchmark"]["equity_curve"]) > 0
