"""Pytest fixtures: mock Keras/joblib and seed minimal backend artifacts for API tests."""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.preprocessing import MinMaxScaler

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODELS = BACKEND / "models"
DATA = BACKEND / "data"

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
    MODELS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    data_csv = DATA / "nifty50_closes.csv"
    _write_closes_csv(data_csv)

    metrics = {
        "window_days": WINDOW,
        "symbols": {
            "RELIANCE.NS": {"confidence": RELIANCE_CONFIDENCE, "mape_pct": 12.79},
        },
    }
    (MODELS / "metrics.json").write_text(json.dumps(metrics))
    (MODELS / "nifty_lstm.keras").write_bytes(b"stub")
    (MODELS / "scalers.joblib").write_bytes(b"stub")

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

    api_main._load_artifacts()

    with TestClient(api_main.app) as test_client:
        yield test_client

    for p in patches:
        p.stop()

    if str(BACKEND) in sys.path:
        sys.path.remove(str(BACKEND))
