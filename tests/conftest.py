"""Pytest fixtures: mock Keras/joblib and isolated backend artifacts for API tests."""

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
            }
        )
    for i in range(10):
        d = start + timedelta(days=i)
        rows.append(
            {
                "Date": d.isoformat(),
                "Symbol": "WIPRO.NS",
                "Close": 400.0 + i,
            }
        )
    import pandas as pd

    pd.DataFrame(rows).to_csv(path, index=False)


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

        data_csv = data / "nifty50_closes.csv"
        _write_closes_csv(data_csv)

        metrics = {
            "window_days": WINDOW,
            "symbols": {
                "RELIANCE.NS": {"confidence": RELIANCE_CONFIDENCE, "mape_pct": 12.79},
            },
        }
        (models / "metrics.json").write_text(json.dumps(metrics))
        (models / "nifty_lstm.keras").write_bytes(b"stub")
        (models / "scalers.joblib").write_bytes(b"stub")

        scalers = {
            "RELIANCE.NS": _make_scaler(),
        }

        mock_model = MagicMock()
        mock_model.predict = lambda x, verbose=0: np.array([[0.5]])

        patches = (
            patch("tensorflow.keras.models.load_model", return_value=mock_model),
            patch("joblib.load", return_value=scalers),
        )

        for p in patches:
            p.start()

        sys.path.insert(0, str(BACKEND))
        for name in list(sys.modules):
            if name == "main" or name.endswith(".main"):
                del sys.modules[name]

        import main as api_main  # noqa: WPS433

        api_main.MODEL_PATH = models / "nifty_lstm.keras"
        api_main.SCALERS_PATH = models / "scalers.joblib"
        api_main.METRICS_PATH = models / "metrics.json"
        api_main.DATA_CSV = data_csv
        api_main.SYMBOLS_CSV = SYMBOLS_CSV

        api_main._load_artifacts()

        with TestClient(api_main.app) as test_client:
            yield test_client

        for p in patches:
            p.stop()

        if str(BACKEND) in sys.path:
            sys.path.remove(str(BACKEND))
