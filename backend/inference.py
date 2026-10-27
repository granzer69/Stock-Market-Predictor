from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS, build_symbol_features

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
PANEL_CSV = BASE_DIR / "data" / "ohlcv_panel.csv"
MACRO_CSV = BASE_DIR / "data" / "macro_series.csv"
REPORT_PATH = MODEL_DIR / "evaluation_report.json"
CHAMPION_LGBM = MODEL_DIR / "champion_lgbm.txt"
ARTIFACTS = MODEL_DIR / "champion_artifacts.joblib"

_lgbm = None
_artifacts = None
_panel = None
_macro = None
_report = None


def _load_lgbm():
    global _lgbm, _artifacts, _report
    if _lgbm is not None:
        return
    import lightgbm as lgb

    _lgbm = lgb.Booster(model_file=str(CHAMPION_LGBM))
    _artifacts = joblib.load(ARTIFACTS)
    if REPORT_PATH.exists():
        _report = json.loads(REPORT_PATH.read_text())


def load_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    global _panel, _macro
    if _panel is None:
        _panel = pd.read_csv(PANEL_CSV)
        _panel["Date"] = pd.to_datetime(_panel["Date"])
    if _macro is None:
        _macro = pd.read_csv(MACRO_CSV)
        _macro["Date"] = pd.to_datetime(_macro["Date"])
    return _panel, _macro


# The booster loaded from champion_lgbm.txt. Not evaluation_report champion_model.
SERVED_MODEL = "lightgbm"
CONFIDENCE_SOURCE = "evaluation_report.pooled_model_comparison.lightgbm.directional_accuracy"


def champion_available() -> bool:
    """True only when the saved booster can load. A missing import is not a per-symbol miss."""
    if not CHAMPION_LGBM.exists() or not ARTIFACTS.exists():
        return False
    try:
        import lightgbm  # noqa: F401
        _load_lgbm()
    except Exception:  # noqa: BLE001 — stack cannot run; caller uses the LSTM
        return False
    return _lgbm is not None


def forecast_feature_row(feat: pd.DataFrame) -> pd.Series:
    """Last bar that has features. The newest close has no realized target_return yet."""
    usable = feat.dropna(subset=list(FEATURE_COLUMNS) + ["Close"])
    if len(usable) < 65:
        raise ValueError("not enough history")
    return usable.iloc[-1]


def _finite_float(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def served_confidence(report: dict | None) -> tuple[float | None, str | None]:
    """Pooled LightGBM directional accuracy. Never the momentum or champion_model row."""
    if not report:
        return None, None
    block = (report.get("pooled_model_comparison") or {}).get(SERVED_MODEL) or {}
    value = _finite_float(block.get("directional_accuracy"))
    if value is None:
        return None, None
    return value, CONFIDENCE_SOURCE


def predict_symbol(yahoo_symbol: str) -> dict:
    _load_lgbm()
    panel, macro = load_panel()
    sym = panel[panel["Symbol"] == yahoo_symbol].copy()
    if sym.empty:
        raise ValueError("symbol not in panel")

    feat = build_symbol_features(sym, macro.copy())
    row = forecast_feature_row(feat)
    close = float(row["Close"])
    X = row[FEATURE_COLUMNS].values.reshape(1, -1)
    scaler = _artifacts["scaler"]
    Xs = scaler.transform(X)

    pred_ret = float(_lgbm.predict(Xs)[0])
    pred_close = close * (1 + pred_ret)

    q_models = _artifacts.get("quantile_models", {})
    quantiles = {}
    if q_models:
        import lightgbm as lgb

        for q, model_str in q_models.items():
            booster = lgb.Booster(model_str=model_str)
            q_ret = float(booster.predict(Xs)[0])
            quantiles[q] = {
                "return": q_ret,
                "price": close * (1 + q_ret),
            }

    conf, confidence_source = served_confidence(_report)

    return {
        "predicted_return": pred_ret,
        "predicted_price": pred_close,
        "direction": "up" if pred_ret > 0 else "down",
        "quantiles": quantiles,
        "confidence": conf,
        "confidence_source": confidence_source,
        "as_of": str(row["Date"])[:10],
        "last_close": close,
        "model": SERVED_MODEL,
    }


def get_evaluation() -> dict:
    if not REPORT_PATH.exists():
        return {"error": "evaluation not run", "hint": "python3 scripts/run_evaluation.py"}
    return json.loads(REPORT_PATH.read_text())


def get_backtest_for_symbol(yahoo_symbol: str) -> dict:
    report = get_evaluation()
    if "error" in report:
        return report
    for entry in report.get("per_symbol_sample", []):
        if entry.get("symbol") == yahoo_symbol:
            return entry.get("backtest_lightgbm", {})
    # compute lightweight from panel if not in sample
    return {
        "note": "Full per-symbol backtest available after evaluation",
        "nifty_benchmark": report.get("nifty_buy_hold_benchmark"),
    }


def ohlcv_with_indicators(yahoo_symbol: str, tail: int = 120) -> list[dict]:
    panel, macro = load_panel()
    sym = panel[panel["Symbol"] == yahoo_symbol].copy()
    feat = build_symbol_features(sym, macro.copy()).tail(tail)
    rows = []
    for _, r in feat.iterrows():
        rows.append(
            {
                "date": str(r["Date"])[:10],
                "open": float(r["Open"]) if "Open" in r and pd.notna(r["Open"]) else float(r["Close"]),
                "high": float(r["High"]) if "High" in r and pd.notna(r["High"]) else float(r["Close"]),
                "low": float(r["Low"]) if "Low" in r and pd.notna(r["Low"]) else float(r["Close"]),
                "close": float(r["Close"]),
                "volume": float(r["Volume"]) if "Volume" in r and pd.notna(r["Volume"]) else 0.0,
                "rsi_14": float(r["rsi_14"]) if pd.notna(r["rsi_14"]) else None,
                "macd": float(r["macd"]) if pd.notna(r["macd"]) else None,
                "bb_up": float(r["bb_up"]) if pd.notna(r.get("bb_up")) else None,
                "bb_low": float(r["bb_low"]) if pd.notna(r.get("bb_low")) else None,
            }
        )
    return rows
