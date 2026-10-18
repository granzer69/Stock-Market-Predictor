from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

MODEL_PATH = BASE_DIR / "models" / "nifty_lstm.keras"
SCALERS_PATH = BASE_DIR / "models" / "scalers.joblib"
METRICS_PATH = BASE_DIR / "models" / "metrics.json"
DATA_CSV = BASE_DIR / "data" / "nifty50_closes.csv"
OHLCV_CSV = BASE_DIR / "data" / "ohlcv_panel.csv"
SYMBOLS_CSV = ROOT_DIR / "data" / "nifty50_symbols.csv"
EVAL_REPORT = BASE_DIR / "models" / "evaluation_report.json"

WINDOW = 60

app = FastAPI(title="Indian Stock Market Predictor API")

default_origins = ["http://localhost:3000"]
allowed = os.environ.get("ALLOWED_ORIGINS", ",".join(default_origins))
origins = [o.strip() for o in allowed.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _inference_module():
    import importlib

    try:
        return importlib.import_module("inference")
    except ModuleNotFoundError:
        return importlib.import_module("backend.inference")


DISCLAIMER = (
    "Paper-trading research demo only. Not investment advice. "
    "No broker connectivity or live orders."
)


def _build_symbol_index() -> dict[str, dict]:
    if not SYMBOLS_CSV.exists():
        return {}
    sym_df = pd.read_csv(SYMBOLS_CSV)
    index: dict[str, dict] = {}
    for _, row in sym_df.iterrows():
        nse = str(row["nse_symbol"]).upper()
        yahoo = str(row["yahoo_symbol"])
        entry = {
            "symbol": nse,
            "yahoo_symbol": yahoo,
            "name": row["name"],
            "sector": row["sector"],
        }
        index[nse] = entry
        index[yahoo.upper()] = entry
        index[yahoo.split(".")[0].upper()] = entry
    return index


def canonicalize(symbol: str) -> tuple[str, dict]:
    key = symbol.strip().upper().replace(".NS", "")
    if key in symbol_index:
        entry = symbol_index[key]
        return entry["yahoo_symbol"], entry
    yahoo = symbol.strip().upper()
    if not yahoo.endswith(".NS"):
        yahoo = f"{yahoo}.NS"
    if yahoo in symbol_index:
        return yahoo, symbol_index[yahoo]
    raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")


def _load_artifacts() -> None:
    global model, scalers, metrics, df, symbol_index, use_champion
    symbol_index = _build_symbol_index()
    use_champion = False

    if OHLCV_CSV.exists():
        panel = pd.read_csv(OHLCV_CSV)
        df = panel.rename(columns={"Close": "Close"})
    elif DATA_CSV.exists():
        df = pd.read_csv(DATA_CSV)
    else:
        raise RuntimeError("Missing data CSV. Run fetch scripts.")

    try:
        use_champion = _inference_module().champion_available()
    except Exception:  # noqa: BLE001
        use_champion = False

    model = None
    scalers = {}
    metrics = {}
    if MODEL_PATH.exists() and SCALERS_PATH.exists():
        from tensorflow.keras.models import load_model

        model = load_model(MODEL_PATH)
        scalers = joblib.load(SCALERS_PATH)
        if METRICS_PATH.exists():
            metrics = json.loads(METRICS_PATH.read_text())


def confidence_for(yahoo_symbol: str) -> float:
    if EVAL_REPORT.exists():
        report = json.loads(EVAL_REPORT.read_text())
        champ = report.get("champion_model", "lightgbm")
        pooled = report.get("pooled_model_comparison", {}).get(champ, {})
        if pooled.get("directional_accuracy"):
            return float(pooled["directional_accuracy"])
    sym_metrics = metrics.get("symbols", {}).get(yahoo_symbol, {})
    return float(sym_metrics.get("confidence", 0.5))


model = None
scalers = None
metrics = None
df = None
symbol_index: dict[str, dict] = {}
use_champion = False


@app.on_event("startup")
def startup() -> None:
    _load_artifacts()


@app.get("/health")
def health():
    return {"status": "ok", "disclaimer": DISCLAIMER, "champion_model": use_champion}


@app.get("/symbols")
def list_symbols():
    if not SYMBOLS_CSV.exists():
        raise HTTPException(status_code=503, detail="Symbol list not configured.")
    sym_df = pd.read_csv(SYMBOLS_CSV)
    symbols = [
        {
            "symbol": row["nse_symbol"],
            "yahoo_symbol": row["yahoo_symbol"],
            "name": row["name"],
            "sector": row["sector"],
        }
        for _, row in sym_df.iterrows()
    ]
    return {"symbols": symbols, "disclaimer": DISCLAIMER}


@app.get("/evaluation")
def evaluation():
    data = _inference_module().get_evaluation()
    data["disclaimer"] = DISCLAIMER
    return data


@app.get("/backtest")
def backtest(symbol: str = Query(..., description="NSE symbol e.g. RELIANCE")):
    yahoo_symbol, meta = canonicalize(symbol)
    if not EVAL_REPORT.exists():
        raise HTTPException(status_code=503, detail="Evaluation not available.")
    report = json.loads(EVAL_REPORT.read_text())
    bt = report.get("per_symbol_backtests", {}).get(yahoo_symbol)
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found for symbol.")
    return {
        "symbol": meta["symbol"],
        "yahoo_symbol": yahoo_symbol,
        "strategy": "long_flat_lightgbm_signal",
        "costs_bps": {"commission": 10, "slippage": 5},
        "paper_trading_only": True,
        "disclaimer": DISCLAIMER,
        "metrics": bt,
        "nifty_buy_hold_benchmark": report.get("nifty_buy_hold_benchmark"),
    }


@app.get("/ohlcv")
def ohlcv(
    symbol: str = Query(..., description="NSE symbol"),
    tail: int = Query(120, ge=30, le=500),
):
    inf = _inference_module()
    yahoo_symbol, meta = canonicalize(symbol)
    if not inf.champion_available() and not OHLCV_CSV.exists():
        raise HTTPException(status_code=503, detail="OHLCV panel missing.")
    try:
        bars = inf.ohlcv_with_indicators(yahoo_symbol, tail=tail)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"symbol": meta["symbol"], "yahoo_symbol": yahoo_symbol, "bars": bars}


@app.get("/predict")
def predict_price(symbol: str = Query(..., description="NSE symbol e.g. RELIANCE")):
    yahoo_symbol, meta = canonicalize(symbol)

    if use_champion:
        try:
            out = _inference_module().predict_symbol(yahoo_symbol)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        q = out.get("quantiles", {})
        return {
            "symbol": meta["symbol"],
            "yahoo_symbol": yahoo_symbol,
            "predicted_price": float(out["predicted_price"]),
            "predicted_return": float(out["predicted_return"]),
            "direction": out["direction"],
            "currency": "INR",
            "as_of": out["as_of"],
            "confidence": float(out["confidence"]),
            "interval": {
                "p10": q.get("0.1", {}).get("price"),
                "p50": q.get("0.5", {}).get("price"),
                "p90": q.get("0.9", {}).get("price"),
            },
            "model": out["model"],
            "disclaimer": DISCLAIMER,
        }

    stock_data = df[df["Symbol"] == yahoo_symbol].sort_values("Date")
    if len(stock_data) < WINDOW:
        raise HTTPException(status_code=422, detail="Not enough data for prediction.")
    if yahoo_symbol not in scalers or model is None:
        raise HTTPException(status_code=503, detail="Legacy model unavailable.")

    scaler = scalers[yahoo_symbol]
    close_prices = stock_data["Close"].values[-WINDOW:].reshape(-1, 1)
    close_prices_scaled = scaler.transform(close_prices)
    x_test = np.array([close_prices_scaled])
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
    predicted_scaled_price = model.predict(x_test, verbose=0)
    predicted_price = scaler.inverse_transform(predicted_scaled_price)
    last_date = stock_data.iloc[-1]["Date"]

    return {
        "symbol": meta["symbol"],
        "yahoo_symbol": yahoo_symbol,
        "predicted_price": float(predicted_price[0][0]),
        "currency": "INR",
        "as_of": str(last_date),
        "confidence": confidence_for(yahoo_symbol),
        "model": "legacy_lstm",
        "disclaimer": DISCLAIMER,
    }


@app.get("/chart")
def get_chart_data(symbol: str = Query(..., description="NSE symbol e.g. RELIANCE")):
    yahoo_symbol, meta = canonicalize(symbol)
    stock_data = df[df["Symbol"] == yahoo_symbol].sort_values("Date")

    if len(stock_data) < WINDOW:
        raise HTTPException(status_code=422, detail="Not enough data for chart.")

    stock_data = stock_data.tail(WINDOW)
    chart_data = [
        {"date": row["Date"], "price": float(row["Close"])} for _, row in stock_data.iterrows()
    ]

    return {"symbol": meta["symbol"], "yahoo_symbol": yahoo_symbol, "chart_data": chart_data}


@app.get("/realtime")
def get_realtime_data(symbol: str = Query(..., description="NSE symbol e.g. RELIANCE")):
    yahoo_symbol, meta = canonicalize(symbol)
    stock_data = df[df["Symbol"] == yahoo_symbol].sort_values("Date")

    if len(stock_data) < 2:
        raise HTTPException(status_code=422, detail="Not enough data for quote.")

    latest_row = stock_data.iloc[-1]
    previous_row = stock_data.iloc[-2]

    price = float(latest_row["Close"])
    previous_close = float(previous_row["Close"])
    change = round(price - previous_close, 2)
    change_percent = round((change / previous_close) * 100, 2) if previous_close else 0.0

    return {
        "symbol": meta["symbol"],
        "yahoo_symbol": yahoo_symbol,
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "previous_close": previous_close,
        "currency": "INR",
        "as_of": str(latest_row["Date"]),
        "disclaimer": DISCLAIMER,
    }
