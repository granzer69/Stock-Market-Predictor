"""Shared API test fixtures (no live Yahoo, no Keras load)."""

from __future__ import annotations

from contextlib import contextmanager

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main as api_main
from portfolio import PaperBook, STARTING_CASH
from predictor import Predictor


def _ohlc_frame(rows: int = 80, close: float = 1000.0) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "Date": [d.strftime("%Y-%m-%d") for d in dates],
            "Open": close,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": 1_000_000,
        }
    )


class FakePredictor:
    ready = True

    def summary(self):
        return {
            "directional_accuracy": 0.482,
            "mae_log_return": 0.01203,
            "naive_mae_log_return": 0.01200,
            "trained_at": "2026-10-18T19:18:36.779819+00:00",
            "symbols": 50,
            "window": 60,
            "signal_threshold": 0.003,
        }

    def summaries(self, frames: dict) -> dict:
        out = {}
        for symbol, frame in frames.items():
            if frame is None or frame.empty:
                continue
            last = float(frame["Close"].iloc[-1])
            out[symbol] = {
                "predicted_close": last * 1.001,
                "predicted_return": 0.001,
                "direction": "up",
                "signal": "HOLD",
                "confidence": 0.5,
            }
        return out

    def detail(self, symbol: str, frame: pd.DataFrame) -> dict | None:
        if frame is None or len(frame) < 61:
            return None
        last = float(frame["Close"].iloc[-1])
        return {
            "symbol": symbol,
            "as_of": str(frame["Date"].iloc[-1]),
            "last_close": last,
            "predicted_close": last * 1.001,
            "predicted_return": 0.001,
            "direction": "up",
            "signal": "HOLD",
            "confidence": 0.5,
            "signal_threshold": 0.003,
            "comparison": [],
            "model": self.summary(),
        }


class FakeMarket:
    def __init__(self, close: float = 1000.0):
        self.close = close
        self._frame = _ohlc_frame(80, close)

    def get_quotes(self, symbols: list[str]) -> dict[str, dict]:
        return {
            symbol: {
                "price": self.close,
                "previous_close": self.close - 1,
                "change": 1.0,
                "change_percent": 0.1,
                "open": self.close,
                "high": self.close + 1,
                "low": self.close - 1,
                "volume": 1_000_000.0,
                "as_of": "2026-10-16",
            }
            for symbol in symbols
        }

    def get_histories(self, symbols: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
        return {symbol: self._frame.copy() for symbol in symbols}

    def get_history(self, symbol: str, period: str = "2y") -> pd.DataFrame | None:
        return self._frame.copy()


def _noop_predictor_load(self) -> None:
    self.ready = False
    self.metrics = {}


@contextmanager
def api_client(tmp_path, close: float = 1000.0):
    pytest.importorskip("fastapi")
    original_load = Predictor.load
    Predictor.load = _noop_predictor_load
    try:
        with TestClient(api_main.app) as client:
            api_main.market = FakeMarket(close=close)
            api_main.book = PaperBook(tmp_path / "api_test.db")
            api_main.predictor = FakePredictor()
            yield client
    finally:
        Predictor.load = original_load


@pytest.fixture
def client(tmp_path):
    with api_client(tmp_path) as test_client:
        yield test_client
