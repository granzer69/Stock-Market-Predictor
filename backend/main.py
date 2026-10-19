"""Indian market data, LSTM forecasts, and a paper trading book."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from data_providers import provider_fetcher
from market_data import HISTORY_PERIODS, PriceCache, bars_from_frame, sma_series
from research import backtest_from_frame
from portfolio import PaperBook
from predictor import Predictor
from universe import GLOBALS, NIFTY_50, resolve

ROOT = Path(__file__).resolve().parent

market: PriceCache
book: PaperBook
predictor: Predictor


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global market, book, predictor
    market = PriceCache(ROOT / "cache", fetcher=provider_fetcher())
    book = PaperBook(ROOT / "paper_trading.db")
    predictor = Predictor(ROOT / "artifacts")
    predictor.load()
    yield


app = FastAPI(title="Bharat Desk", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


@app.get("/api/health")
def health():
    return {"ok": True, "model": predictor.ready}


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
    return {"stocks": stocks, "model": predictor.summary()}


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
    from market_data import quote_from_frame

    return {
        **series.as_dict(),
        "period": period,
        "quote": quote_from_frame(frame),
        "bars": bars_from_frame(frame),
        "sma20": sma_series(frame, 20),
        "sma50": sma_series(frame, 50),
    }


@app.get("/api/research/backtest/{symbol}")
def research_backtest(symbol: str, period: str = Query(default="2y")):
    if period not in HISTORY_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {', '.join(HISTORY_PERIODS)}")
    series = resolve(symbol)
    if series is None or series.kind != "equity":
        raise HTTPException(status_code=404, detail="Unknown Nifty 50 symbol")
    if not predictor.ready:
        raise HTTPException(status_code=503, detail="Model is not trained yet")
    frame = market.get_history(series.symbol, period)
    if frame is None or frame.empty:
        raise HTTPException(status_code=404, detail="No history for symbol")
    try:
        payload = backtest_from_frame(series.symbol, frame, predictor, period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload.update({"ticker": series.ticker, "name": series.name})
    return payload


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
