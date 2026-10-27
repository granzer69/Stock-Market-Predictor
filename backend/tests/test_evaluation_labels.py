"""Label fixes for the momentum baseline and the served LightGBM payload.

No Yahoo and no Keras. These checks do not claim that any model beats 0.5.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import inference

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = Path(__file__).resolve().parents[1] / "models" / "evaluation_report.json"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from ml.features import FEATURE_COLUMNS  # noqa: E402
from ml.metrics import momentum_directional_accuracy  # noqa: E402

# Same cut evaluate_symbol uses (TRAIN_RATIO in scripts/run_evaluation.py).
_TRAIN_RATIO = 0.8


def test_momentum_baseline_uses_previous_return_sign():
    closes = np.array([100, 110, 100, 110, 100, 110], dtype=np.float64)
    split = int(len(closes) * _TRAIN_RATIO)
    scored = momentum_directional_accuracy(closes, split)
    # Alternating closes: the lagged sign never matches the next return.
    assert scored["directional_accuracy"] == 0
    assert scored["n_samples"] == len(closes) - split

    # A second series where the lagged sign matches once. A constant 0 or the
    # same-bar sign (accuracy 1 on this cut) would not produce 0.5.
    mixed = np.array([100, 110, 100, 110, 120, 110], dtype=np.float64)
    mixed_split = int(len(mixed) * _TRAIN_RATIO)
    mixed_score = momentum_directional_accuracy(mixed, mixed_split)
    assert mixed_score["directional_accuracy"] == 0.5


def test_forecast_row_does_not_require_target_return():
    n = 70
    dates = pd.bdate_range("2024-01-02", periods=n)
    data = {column: np.linspace(0.1, 1.0, n) for column in FEATURE_COLUMNS}
    data["Close"] = np.linspace(100.0, 170.0, n)
    data["Date"] = dates
    target = np.linspace(0.01, 0.02, n)
    target[-1] = np.nan
    data["target_return"] = target
    row = inference.forecast_feature_row(pd.DataFrame(data))
    assert str(row["Date"])[:10] == str(dates[-1])[:10]
    assert pd.isna(row["target_return"])
    assert float(row["Close"]) == data["Close"][-1]


class _IdentityScaler:
    def transform(self, values):
        return values


class _StubBooster:
    def predict(self, values):
        return np.array([0.01], dtype=np.float64)


def test_predict_symbol_scores_last_date_as_lightgbm(monkeypatch):
    report = json.loads(REPORT_PATH.read_text())
    pooled = report["pooled_model_comparison"]
    lightgbm_hit = pooled["lightgbm"]["directional_accuracy"]
    arima_hit = pooled["arima_111"]["directional_accuracy"]
    momentum_hit = pooled["momentum"]["directional_accuracy"]
    assert report["champion_model"] == "arima_111"
    assert lightgbm_hit != arima_hit
    assert lightgbm_hit != momentum_hit

    n = 160
    dates = pd.bdate_range("2024-01-02", periods=n)
    closes = np.where(np.arange(n) % 2 == 0, 100.0, 110.0)
    panel = pd.DataFrame(
        {
            "Date": dates,
            "Close": closes,
            "High": closes + 1.0,
            "Low": closes - 1.0,
            "Open": closes,
            "Volume": 1_000_000 + np.arange(n) * 250,
            "Symbol": "RELIANCE.NS",
        }
    )
    macro = pd.DataFrame(
        {
            "Date": dates,
            "nifty": np.linspace(18000, 20000, n),
            "india_vix": np.linspace(14, 18, n),
            "usd_inr": np.linspace(82, 84, n),
            "crude": np.linspace(70, 85, n),
            "sp500": np.linspace(4200, 5200, n),
        }
    )

    monkeypatch.setattr(inference, "_lgbm", _StubBooster())
    monkeypatch.setattr(inference, "_artifacts", {"scaler": _IdentityScaler(), "quantile_models": {}})
    monkeypatch.setattr(inference, "_report", report)
    monkeypatch.setattr(inference, "load_panel", lambda: (panel, macro))

    out = inference.predict_symbol("RELIANCE.NS")
    last_date = str(dates[-1])[:10]
    previous_date = str(dates[-2])[:10]
    assert out["as_of"] == last_date
    assert out["as_of"] != previous_date
    assert out["last_close"] == closes[-1]
    assert out["model"] == "lightgbm"
    assert out["model"] != report["champion_model"]
    assert out["confidence"] == lightgbm_hit
    assert out["confidence"] != momentum_hit
    assert out["confidence"] != arima_hit
    assert out["confidence_source"] == inference.CONFIDENCE_SOURCE
    assert "lightgbm" in out["confidence_source"]
