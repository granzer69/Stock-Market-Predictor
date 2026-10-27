"""Desk forecast provenance. No network and no Keras."""

from __future__ import annotations

import numpy as np
import pandas as pd

import inference
from backtest.signals import predicted_returns_from_windows
from desk_predictor import DeskPredictor


def _live_frame() -> pd.DataFrame:
    return pd.DataFrame({"Date": ["2026-10-27"], "Close": [2500.0]})


class _RaisingLstm:
    ready = True

    def _predict_scaled(self, windows):
        count = len(windows) if hasattr(windows, "__len__") else 1
        return np.zeros(count, dtype=np.float64)

    def summaries(self, frames):
        raise AssertionError("LSTM summaries must not fill a champion miss")

    def detail(self, symbol, frame):
        raise AssertionError("LSTM detail must not replace a champion forecast")

    def summary(self):
        return {"directional_accuracy": 0.4870381534751529}


def _stub_predict(monkeypatch, calls: dict, research: dict):
    def predict_symbol(symbol):
        calls["predict_symbol"] += 1
        if research["on"]:
            raise AssertionError("research path called predict_symbol")
        return {
            "predicted_return": 2410.0 / 2400.0 - 1.0,
            "predicted_price": 2410.0,
            "direction": "up",
            "quantiles": {},
            "confidence": 0.4707,
            "confidence_source": "evaluation_report.pooled_model_comparison.lightgbm.directional_accuracy",
            "as_of": "2026-10-16",
            "last_close": 2400.0,
            "model": "lightgbm",
        }

    monkeypatch.setattr(inference, "predict_symbol", predict_symbol)
    monkeypatch.setattr(inference, "champion_available", lambda: True)


def test_detail_keeps_forecast_as_of_and_base_close(monkeypatch):
    calls = {"predict_symbol": 0, "scaled": 0}
    research = {"on": False}
    _stub_predict(monkeypatch, calls, research)

    class Lstm(_RaisingLstm):
        def _predict_scaled(self, windows):
            calls["scaled"] += 1
            return super()._predict_scaled(windows)

    desk = DeskPredictor(Lstm())
    body = desk.detail("RELIANCE.NS", _live_frame())
    assert body is not None
    assert body["as_of"] == "2026-10-16"
    assert body["last_close"] == 2400
    assert body["predicted_close"] == 2410
    assert body["as_of"] != "2026-10-27"
    assert body["last_close"] != 2500
    assert body["model"] == "lightgbm"
    assert body["model"] != "lstm"

    summaries = desk.summaries({"RELIANCE.NS": _live_frame()})
    row = summaries["RELIANCE.NS"]
    assert row["as_of"] == "2026-10-16"
    assert row["last_close"] == 2400
    assert row["predicted_close"] == 2410
    assert row["model"] == "lightgbm"

    research["on"] = True
    closes = np.linspace(100.0, 180.0, 80)
    before = calls["predict_symbol"]
    signals, _preds = predicted_returns_from_windows(desk, closes)
    assert calls["scaled"] == 1
    assert calls["predict_symbol"] == before
    assert len(signals) == len(closes)
    assert signals[0] == "HOLD"


def test_champion_miss_does_not_mix_lstm(monkeypatch):
    def predict_symbol(symbol):
        raise ValueError("symbol not in panel")

    monkeypatch.setattr(inference, "predict_symbol", predict_symbol)
    monkeypatch.setattr(inference, "champion_available", lambda: True)
    desk = DeskPredictor(_RaisingLstm())
    frame = _live_frame()
    assert desk.summaries({"RELIANCE.NS": frame}) == {}
    assert desk.detail("RELIANCE.NS", frame) is None


def test_research_signals_use_scaled_lstm_only():
    calls = {"scaled": 0}

    class Fake:
        ready = True

        def _predict_scaled(self, windows):
            calls["scaled"] += 1
            return np.zeros(len(windows), dtype=np.float64)

        def predict_symbol(self, symbol):
            raise AssertionError("predict_symbol must not run")

    closes = np.linspace(100.0, 180.0, 80)
    signals, preds = predicted_returns_from_windows(Fake(), closes)
    assert calls["scaled"] == 1
    assert len(signals) == len(closes)
    assert np.isfinite(preds[60:]).all()
