from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "nifty_lstm.keras"
SCALERS_PATH = BASE_DIR / "models" / "scalers.joblib"
METRICS_PATH = BASE_DIR / "models" / "metrics.json"
DATA_CSV = BASE_DIR / "data" / "nifty50_closes.csv"
SYMBOLS_CSV = BASE_DIR.parent / "data" / "nifty50_symbols.csv"

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


def _load_artifacts() -> None:
    global model, scalers, metrics, df, symbol_index
    missing = [p for p in (MODEL_PATH, SCALERS_PATH, METRICS_PATH, DATA_CSV) if not p.exists()]
    if missing:
        names = ", ".join(str(p.relative_to(BASE_DIR.parent)) for p in missing)
        raise RuntimeError(
            f"Missing artifact(s): {names}. Run scripts/fetch_nifty.py and scripts/train.py."
        )
    model = load_model(MODEL_PATH)
    scalers = joblib.load(SCALERS_PATH)
    metrics = json.loads(METRICS_PATH.read_text())
    df = pd.read_csv(DATA_CSV)
    symbol_index = _build_symbol_index()


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


def confidence_for(yahoo_symbol: str) -> float:
    sym_metrics = metrics.get("symbols", {}).get(yahoo_symbol, {})
    return float(sym_metrics.get("confidence", 0.5))


model = None
scalers = None
metrics = None
df = None
symbol_index: dict[str, dict] = {}


@app.on_event("startup")
def startup() -> None:
    _load_artifacts()


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
    return {"symbols": symbols}


@app.get("/predict")
def predict_price(symbol: str = Query(..., description="NSE symbol e.g. RELIANCE")):
    yahoo_symbol, meta = canonicalize(symbol)
    stock_data = df[df["Symbol"] == yahoo_symbol].sort_values("Date")

    if len(stock_data) < WINDOW:
        raise HTTPException(status_code=422, detail="Not enough data for prediction.")

    if yahoo_symbol not in scalers:
        raise HTTPException(status_code=422, detail="No scaler for symbol.")

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
    }
