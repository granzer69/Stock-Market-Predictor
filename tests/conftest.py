"""Pytest fixtures: mock Keras/joblib/LightGBM and seed minimal backend artifacts."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.preprocessing import MinMaxScaler

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SYMBOLS_CSV = ROOT / "data" / "nifty50_symbols.csv"

WINDOW = 60
RELIANCE_CONFIDENCE = 0.8721


def _write_closes_csv(path: Path) -> None:
    start = date(2024, 1, 1)
    rows: list[dict[str, object]] = []
    for i in range(WINDOW + 5):
        d = start + timedelta(days=i)
        rows.append(
            {
                "Date": d.isoformat(),
                "Symbol": "RELIANCE.NS",
                "Close": 2500.0 + i,
                "Open": 2490.0 + i,
                "High": 2510.0 + i,
                "Low": 2480.0 + i,
                "Volume": 1_000_000 + i,
            }
        )
    for i in range(10):
        d = start + timedelta(days=i)
        rows.append(
            {
                "Date": d.isoformat(),
                "Symbol": "WIPRO.NS",
                "Close": 400.0 + i,
                "Open": 399.0 + i,
                "High": 401.0 + i,
                "Low": 398.0 + i,
                "Volume": 500_000,
            }
        )
    import pandas as pd

    pd.DataFrame(rows).to_csv(path, index=False)


def _write_macro(path: Path) -> None:
    import pandas as pd

    pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=80, freq="D"),
            "nifty": np.linspace(22000, 23000, 80),
            "india_vix": np.linspace(12, 14, 80),
            "usd_inr": np.linspace(83, 84, 80),
            "crude": np.linspace(70, 72, 80),
            "sp500": np.linspace(5000, 5100, 80),
        }
    ).assign(Date=lambda x: x["Date"].dt.strftime("%Y-%m-%d")).to_csv(path, index=False)


def _make_scaler() -> MinMaxScaler:
    scaler = MinMaxScaler(feature_range=(0, 1))
    values = np.arange(WINDOW).reshape(-1, 1) * 10.0 + 2400.0
    scaler.fit(values)
    return scaler


@pytest.fixture(scope="module")
def client() -> TestClient:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        models = tmp_path / "models"
        data = tmp_path / "data"
        models.mkdir()
        data.mkdir()

        data_csv = data / "ohlcv_panel.csv"
        _write_closes_csv(data_csv)
        macro_csv = data / "macro_series.csv"
        _write_macro(macro_csv)

        metrics = {
            "window_days": WINDOW,
            "symbols": {
                "RELIANCE.NS": {"confidence": RELIANCE_CONFIDENCE, "mape_pct": 12.79},
            },
        }
        (models / "metrics.json").write_text(json.dumps(metrics))
        (models / "nifty_lstm.keras").write_bytes(b"stub")
        (models / "scalers.joblib").write_bytes(b"stub")
        (models / "evaluation_report.json").write_text(
            json.dumps(
                {
                    "champion_model": "lightgbm",
                    "pooled_model_comparison": {
                        "persistence": {"directional_accuracy": 0.51, "mape_pct": 1.5, "rmse": 10, "n_symbols": 1},
                        "lightgbm": {"directional_accuracy": RELIANCE_CONFIDENCE, "mape_pct": 1.2, "rmse": 8, "n_symbols": 1},
                    },
                    "per_symbol_backtests": {
                        "RELIANCE.NS": {
                            "cagr": 0.05,
                            "buy_hold_cagr": 0.08,
                            "sharpe": 0.4,
                            "max_drawdown": -0.12,
                            "win_rate": 0.52,
                        }
                    },
                    "methodology": {"honest_note": "test fixture"},
                }
            )
        )

        scalers = {"RELIANCE.NS": _make_scaler()}
        mock_model = MagicMock()
        mock_model.predict = lambda x, verbose=0: np.array([[0.5]])

        mock_booster = MagicMock()
        mock_booster.predict = lambda x: np.array([0.001])

        patches = (
            patch("tensorflow.keras.models.load_model", return_value=mock_model),
            patch("joblib.load", return_value=scalers),
        )

        for p in patches:
            p.start()

        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(BACKEND))
        for name in list(sys.modules):
            if name in ("main", "inference") or name.endswith(".main"):
                del sys.modules[name]

        import inference as inf  # noqa: WPS433
        import main as api_main  # noqa: WPS433

        inf.REPORT_PATH = models / "evaluation_report.json"
        inf.CHAMPION_LGBM = models / "missing_champion.txt"
        inf.ARTIFACTS = models / "missing_champion.joblib"
        inf.PANEL_CSV = data_csv
        inf.MACRO_CSV = macro_csv

        api_main.OHLCV_CSV = data_csv
        api_main.DATA_CSV = data_csv
        api_main.MODEL_PATH = models / "nifty_lstm.keras"
        api_main.SCALERS_PATH = models / "scalers.joblib"
        api_main.METRICS_PATH = models / "metrics.json"
        api_main.EVAL_REPORT = models / "evaluation_report.json"
        api_main._load_artifacts()
        api_main.use_champion = False

        with TestClient(api_main.app) as test_client:
            yield test_client

        for p in patches:
            p.stop()

        for p in (str(ROOT), str(BACKEND)):
            if p in sys.path:
                sys.path.remove(p)
