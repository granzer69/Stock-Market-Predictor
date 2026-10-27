"""Strict JSON for the stored evaluation report. The file on disk is not rewritten."""

from __future__ import annotations

import math
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "models" / "evaluation_report.json"


def _assert_json_numbers(value) -> None:
    if isinstance(value, float):
        assert math.isfinite(value)
    elif isinstance(value, dict):
        for item in value.values():
            _assert_json_numbers(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_numbers(item)


def test_evaluation_aliases_are_strict_json(client):
    raw = REPORT.read_text(encoding="utf-8")
    assert "NaN" in raw

    legacy = client.get("/evaluation")
    alias = client.get("/api/evaluation")
    assert legacy.status_code == 200
    assert alias.status_code == 200
    assert "NaN" not in legacy.text
    assert "NaN" not in alias.text
    body = legacy.json()
    assert body == alias.json()
    _assert_json_numbers(body)
    momentum = body["pooled_model_comparison"]["momentum"]
    assert momentum["directional_accuracy"] == 1.0
    assert momentum["mape_pct"] is None
    assert momentum["rmse"] is None
    assert body["champion_model"] == "arima_111"
    assert body["champion_model"] != "momentum"
    assert "pooled_model_comparison" in body
    assert "disclaimer" in body


def test_legacy_backtest_alias_matches(client):
    legacy = client.get("/backtest", params={"symbol": "RELIANCE"})
    alias = client.get("/api/legacy/backtest", params={"symbol": "RELIANCE"})
    assert legacy.status_code == 200
    assert alias.status_code == 200
    assert "NaN" not in legacy.text
    assert legacy.json() == alias.json()
    assert legacy.json()["paper_trading_only"] is True
    _assert_json_numbers(legacy.json())
