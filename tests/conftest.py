"""Pytest fixtures: mock TF and isolated CSV artifacts for legacy REST routes."""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import asynccontextmanager
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

        (models / "metrics.json").write_text(
            json.dumps(
                {
                    "symbols": {
                        "RELIANCE.NS": {"confidence": RELIANCE_CONFIDENCE},
                    }
                }
            )
        )
        (models / "nifty_lstm.keras").write_bytes(b"stub")
        (models / "scalers.joblib").write_bytes(b"stub")
        (models / "evaluation_report.json").write_text(
            json.dumps(
                {
                    "champion_model": "arima_111",
                    "champion_directional_accuracy": 0.5066,
                    "pooled_model_comparison": {
                        "lightgbm": {
                            "directional_accuracy": RELIANCE_CONFIDENCE,
                            "mape_pct": 1.42,
                            "rmse": 47,
                            "n_symbols": 50,
                        }
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

        mock_lstm = MagicMock()
        mock_lstm.ready = False
        mock_lstm.load.return_value = None
        mock_desk = MagicMock()
        mock_desk.ready = False
        mock_desk.summary.return_value = None
        mock_desk.summaries.return_value = {}

        @asynccontextmanager
        async def _test_life(_app):
            import main as api_main

            api_main._load_legacy_stack()
            yield

        patches = (
            patch("tensorflow.keras.models.load_model", return_value=mock_model),
            patch("joblib.load", return_value=scalers),
            patch("main.PriceCache", return_value=MagicMock()),
            patch("main.PaperBook", return_value=MagicMock()),
            patch("main.Predictor", return_value=mock_lstm),
            patch("main.DeskPredictor", return_value=mock_desk),
        )

        for p in patches:
            p.start()

        sys.path.insert(0, str(BACKEND))
        for name in list(sys.modules):
            if name == "main" or name.startswith("main."):
                del sys.modules[name]

        import main as api_main  # noqa: WPS433

        inf = api_main._inference_module()
        inf.REPORT_PATH = models / "evaluation_report.json"
        inf.CHAMPION_LGBM = models / "missing.txt"
        inf.ARTIFACTS = models / "missing.joblib"
        inf.PANEL_CSV = data_csv
        inf.MACRO_CSV = data / "macro.csv"

        api_main.OHLCV_CSV = data_csv
        api_main.DATA_CSV = data_csv
        api_main.MODEL_PATH = models / "nifty_lstm.keras"
        api_main.SCALERS_PATH = models / "scalers.joblib"
        api_main.METRICS_PATH = models / "metrics.json"
        api_main.EVAL_REPORT = models / "evaluation_report.json"
        api_main.SYMBOLS_CSV = SYMBOLS_CSV
        api_main.app.router.lifespan_context = _test_life

        with TestClient(api_main.app) as test_client:
            yield test_client

        for p in patches:
            p.stop()
        if str(BACKEND) in sys.path:
            sys.path.remove(str(BACKEND))


def _make_scaler() -> MinMaxScaler:
    scaler = MinMaxScaler(feature_range=(0, 1))
    values = np.arange(WINDOW).reshape(-1, 1) * 10.0 + 2400.0
    scaler.fit(values)
    return scaler
