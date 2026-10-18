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


def champion_available() -> bool:
    return CHAMPION_LGBM.exists() and ARTIFACTS.exists()


def predict_symbol(yahoo_symbol: str) -> dict:
    _load_lgbm()
    panel, macro = load_panel()
    sym = panel[panel["Symbol"] == yahoo_symbol].copy()
    if sym.empty:
        raise ValueError("symbol not in panel")

    feat = build_symbol_features(sym, macro.copy())
    feat = feat.dropna(subset=FEATURE_COLUMNS + ["Close", "target_return"])
    if len(feat) < 65:
        raise ValueError("not enough history")

    row = feat.iloc[-1]
    close = float(row["Close"])
    X = row[FEATURE_COLUMNS].values.reshape(1, -1)
    scaler = _artifacts["scaler"]
    Xs = scaler.transform(X)

    pred_ret = float(_lgbm.predict(Xs)[0])
    pred_close = close * (1 + pred_ret)

    q_models = _artifacts.get("quantile_models", {})
    import lightgbm as lgb

    quantiles = {}
    for q, model_str in q_models.items():
        booster = lgb.Booster(model_str=model_str)
        q_ret = float(booster.predict(Xs)[0])
        quantiles[q] = {
            "return": q_ret,
            "price": close * (1 + q_ret),
        }

    conf = 0.5
    if _report and "pooled_model_comparison" in _report:
        champ = _report.get("champion_model", "lightgbm")
        comp = _report["pooled_model_comparison"].get(champ, {})
        conf = float(comp.get("directional_accuracy", 0.5))

    return {
        "predicted_return": pred_ret,
        "predicted_price": pred_close,
        "direction": "up" if pred_ret > 0 else "down",
        "quantiles": quantiles,
        "confidence": conf,
        "as_of": str(row["Date"])[:10],
        "last_close": close,
        "model": _report.get("champion_model", "lightgbm") if _report else "lightgbm",
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
