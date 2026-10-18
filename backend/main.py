"""Bharat Desk API: Nifty 50, paper book, LightGBM + evaluation endpoints."""

from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from desk_predictor import DeskPredictor
from market_data import HISTORY_PERIODS, PriceCache, bars_from_frame, quote_from_frame, sma_series
from portfolio import PaperBook
from predictor import Predictor
from universe import GLOBALS, NIFTY_50, resolve

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

DISCLAIMER = (
    "Paper-trading research demo only. Not investment advice. "
    "No broker connectivity or live orders."
)

market: PriceCache
book: PaperBook
predictor: DeskPredictor

df: pd.DataFrame | None = None
symbol_index: dict[str, dict] = {}
use_champion = False
legacy_model = None
legacy_scalers = None
legacy_metrics: dict = {}


def _inference_module():
    import importlib

    try:
        return importlib.import_module("inference")
    except ModuleNotFoundError:
        return importlib.import_module("backend.inference")


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


def _load_legacy_stack() -> None:
    global df, symbol_index, use_champion, legacy_model, legacy_scalers, legacy_metrics
    symbol_index = _build_symbol_index()
    use_champion = False
    if OHLCV_CSV.exists():
        df = pd.read_csv(OHLCV_CSV)
    elif DATA_CSV.exists():
        df = pd.read_csv(DATA_CSV)
    else:
        df = pd.DataFrame()
    try:
        use_champion = _inference_module().champion_available()
    except Exception:  # noqa: BLE001
        use_champion = False
    legacy_model = None
    legacy_scalers = {}
    legacy_metrics = {}
    if MODEL_PATH.exists() and SCALERS_PATH.exists():
        from tensorflow.keras.models import load_model

        legacy_model = load_model(MODEL_PATH)
        legacy_scalers = joblib.load(SCALERS_PATH)
        if METRICS_PATH.exists():
            legacy_metrics = json.loads(METRICS_PATH.read_text())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global market, book, predictor
    market = PriceCache(BASE_DIR / "cache")
    book = PaperBook(BASE_DIR / "paper_trading.db")
    lstm = Predictor(BASE_DIR / "artifacts")
    lstm.load()
    predictor = DeskPredictor(lstm)
    _load_legacy_stack()
    yield


app = FastAPI(title="Bharat Desk", lifespan=lifespan)
allowed = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [o.strip() for o in allowed.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrderIn(BaseModel):
    symbol: str
    side: str
    qty: int = Field(..., gt=0)


def _listing_quote(series, quote: dict, prediction: dict | None = None) -> dict:
    payload = {**series.as_dict(), **quote}
    if prediction is not None:
        payload["prediction"] = prediction
    return payload


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


@app.get("/api/health")
def api_health():
    return {"ok": True, "model": predictor.ready, "disclaimer": DISCLAIMER}


@app.get("/api/market/overview")
def overview():
    symbols = [item.symbol for item in NIFTY_50]
    quotes = market.get_quotes(symbols)
    histories = market.get_histories(symbols, "2y")
    predictions = predictor.summaries(histories)
    stocks = []
    for series in NIFTY_50:
        quote = quotes.get(series.symbol)
        if not quote:
            continue
        stocks.append(_listing_quote(series, quote, predictions.get(series.symbol)))
    return {"stocks": stocks, "model": predictor.summary(), "disclaimer": DISCLAIMER}


@app.get("/api/market/globals")
def globals_tape():
    symbols = [item.symbol for item in GLOBALS]
    quotes = market.get_quotes(symbols)
    series = []
    for item in GLOBALS:
        quote = quotes.get(item.symbol)
        if not quote:
            continue
        series.append(_listing_quote(item, quote))
    return {"series": series}


@app.get("/api/market/history/{symbol}")
def history(symbol: str, period: str = Query(default="2y")):
    if period not in HISTORY_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {', '.join(HISTORY_PERIODS)}")
    series = resolve(symbol)
    if series is None:
        raise HTTPException(status_code=404, detail="Unknown symbol")
    frame = market.get_history(series.symbol, period)
    if frame is None or frame.empty:
        raise HTTPException(status_code=404, detail="No history for symbol")
    return {
        **series.as_dict(),
        "period": period,
        "quote": quote_from_frame(frame),
        "bars": bars_from_frame(frame),
        "sma20": sma_series(frame, 20),
        "sma50": sma_series(frame, 50),
    }


@app.get("/api/predict/{symbol}")
def predict(symbol: str):
    series = resolve(symbol)
    if series is None or series.kind != "equity":
        raise HTTPException(status_code=404, detail="Unknown Nifty 50 symbol")
    if not predictor.ready:
        raise HTTPException(status_code=503, detail="Model is not trained yet")
    frame = market.get_history(series.symbol, "2y")
    if frame is None:
        raise HTTPException(status_code=404, detail="No history for symbol")
    detail = predictor.detail(series.symbol, frame)
    if detail is None:
        raise HTTPException(status_code=400, detail="Not enough history to predict")
    detail.update(series.as_dict())
    detail["disclaimer"] = DISCLAIMER
    return detail


def _enrich(row: dict) -> dict:
    series = resolve(row["symbol"])
    if series is None:
        return {**row, "ticker": row["symbol"], "name": row["symbol"]}
    return {**row, "ticker": series.ticker, "name": series.name}


@app.get("/api/portfolio")
def portfolio():
    positions = book.positions()
    quotes = market.get_quotes([row["symbol"] for row in positions]) if positions else {}
    prices = {symbol: quote["price"] for symbol, quote in quotes.items()}
    snapshot = book.snapshot(prices)
    snapshot["positions"] = [_enrich(row) for row in snapshot["positions"]]
    snapshot["disclaimer"] = DISCLAIMER
    return snapshot


@app.get("/api/orders")
def orders():
    return {"orders": [_enrich(row) for row in book.orders()]}


@app.post("/api/orders")
def create_order(body: OrderIn):
    series = resolve(body.symbol)
    if series is None or series.kind != "equity":
        raise HTTPException(status_code=400, detail="Only Nifty 50 stocks can be traded")
    quotes = market.get_quotes([series.symbol])
    quote = quotes.get(series.symbol)
    if not quote:
        raise HTTPException(status_code=503, detail="No price for that symbol")
    try:
        order = book.place_order(series.symbol, body.side, body.qty, quote["price"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _enrich(order)


@app.get("/health")
def health():
    return {"status": "ok", "disclaimer": DISCLAIMER, "champion_model": use_champion}


@app.get("/evaluation")
def evaluation():
    data = _inference_module().get_evaluation()
    data["disclaimer"] = DISCLAIMER
    return data


@app.get("/backtest")
def backtest(symbol: str = Query(...)):
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
        "paper_trading_only": True,
        "disclaimer": DISCLAIMER,
        "metrics": bt,
        "nifty_buy_hold_benchmark": report.get("nifty_buy_hold_benchmark"),
    }


@app.get("/symbols")
def list_symbols():
    if SYMBOLS_CSV.exists():
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
    else:
        symbols = [s.as_dict() for s in NIFTY_50]
    return {"symbols": symbols, "disclaimer": DISCLAIMER}


@app.get("/chart")
def get_chart_data(symbol: str = Query(...)):
    yahoo_symbol, meta = canonicalize(symbol)
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="No data loaded.")
    stock_data = df[df["Symbol"] == yahoo_symbol].sort_values("Date")
    if len(stock_data) < WINDOW:
        raise HTTPException(status_code=422, detail="Not enough data for chart.")
    stock_data = stock_data.tail(WINDOW)
    chart_data = [
        {"date": row["Date"], "price": float(row["Close"])} for _, row in stock_data.iterrows()
    ]
    return {"symbol": meta["symbol"], "yahoo_symbol": yahoo_symbol, "chart_data": chart_data}


@app.get("/predict")
def predict_price(symbol: str = Query(...)):
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
            "model": out.get("model", "lightgbm"),
            "disclaimer": DISCLAIMER,
        }
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="No data loaded.")
    stock_data = df[df["Symbol"] == yahoo_symbol].sort_values("Date")
    if len(stock_data) < WINDOW:
        raise HTTPException(status_code=422, detail="Not enough data for prediction.")
    if yahoo_symbol not in legacy_scalers or legacy_model is None:
        raise HTTPException(status_code=503, detail="Legacy model unavailable.")
    scaler = legacy_scalers[yahoo_symbol]
    close_prices = stock_data["Close"].values[-WINDOW:].reshape(-1, 1)
    close_prices_scaled = scaler.transform(close_prices)
    x_test = np.array([close_prices_scaled]).reshape(1, WINDOW, 1)
    predicted_scaled_price = legacy_model.predict(x_test, verbose=0)
    predicted_price = scaler.inverse_transform(predicted_scaled_price)
    return {
        "symbol": meta["symbol"],
        "yahoo_symbol": yahoo_symbol,
        "predicted_price": float(predicted_price[0][0]),
        "currency": "INR",
        "as_of": str(stock_data.iloc[-1]["Date"]),
        "confidence": float(
            legacy_metrics.get("symbols", {}).get(yahoo_symbol, {}).get("confidence", 0.5)
        ),
        "model": "legacy_lstm",
        "disclaimer": DISCLAIMER,
    }


@app.get("/realtime")
def get_realtime_data(symbol: str = Query(...)):
    yahoo_symbol, meta = canonicalize(symbol)
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="No data loaded.")
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
