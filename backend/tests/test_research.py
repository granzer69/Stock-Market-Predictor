import pandas as pd

from research import backtest_from_frame
from conftest import FakePredictor, _ohlc_frame


def test_backtest_from_frame_returns_strategy_and_benchmark():
    frame = _ohlc_frame(90, close=500.0)
    payload = backtest_from_frame("RELIANCE.NS", frame, FakePredictor(), "1y")
    assert payload["symbol"] == "RELIANCE.NS"
    assert "strategy" in payload and "benchmark" in payload
    assert payload["benchmark"]["kind"] == "buy_and_hold"
    assert len(payload["equity_curve"]) > 0
    assert len(payload["benchmark"]["equity_curve"]) > 0
