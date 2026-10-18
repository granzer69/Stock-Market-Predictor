"""Daily OHLCV with a disk cache and a short-lived quote cache."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pandas as pd

# TensorFlow's SSL stack breaks curl_cffi impersonation in the same process.
# Yahoo still answers the plain requests client, which is what the API uses
# after the model has been loaded.
os.environ.setdefault("YF_DISABLE_CURL_CFFI", "1")

HISTORY_TTL_SECONDS = 12 * 60 * 60
QUOTE_TTL_SECONDS = 15 * 60
HISTORY_PERIODS = ("6mo", "1y", "2y", "5y")


def _safe_name(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol)


def _normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame | None:
    df = frame.copy()
    if "Date" not in df.columns:
        df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else ("Datetime" if "Datetime" in df.columns else df.columns[0])
    if "Close" not in df.columns:
        return None
    df = df.rename(columns={date_col: "Date"})
    for col in ("Open", "High", "Low"):
        if col not in df.columns:
            df[col] = df["Close"]
    if "Volume" not in df.columns:
        df["Volume"] = 0
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Date", "Close"])
    df = df[df["Close"] > 0]
    if df.empty:
        return None
    df["Open"] = df["Open"].fillna(df["Close"])
    df["High"] = df["High"].fillna(df["Close"])
    df["Low"] = df["Low"].fillna(df["Close"])
    df["Volume"] = df["Volume"].fillna(0)
    df["High"] = df[["Open", "High", "Low", "Close"]].max(axis=1)
    df["Low"] = df[["Open", "High", "Low", "Close"]].min(axis=1)
    df = df.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]].reset_index(drop=True)


def frames_from_download(raw: pd.DataFrame | None, symbols: list[str]) -> dict[str, pd.DataFrame]:
    if raw is None or raw.empty:
        return {}
    out: dict[str, pd.DataFrame] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        tickers = set(raw.columns.get_level_values(-1))
        for symbol in symbols:
            if symbol not in tickers:
                continue
            sub = raw.xs(symbol, axis=1, level=-1)
            frame = _normalize_ohlcv(sub)
            if frame is not None:
                out[symbol] = frame
        return out
    if len(symbols) != 1:
        return {}
    frame = _normalize_ohlcv(raw)
    if frame is not None:
        out[symbols[0]] = frame
    return out


def quote_from_frame(frame: pd.DataFrame) -> dict:
    last = frame.iloc[-1]
    prev = frame.iloc[-2] if len(frame) > 1 else last
    price = float(last["Close"])
    previous = float(prev["Close"])
    change = price - previous
    percent = (change / previous * 100.0) if previous else 0.0
    return {
        "price": price,
        "previous_close": previous,
        "change": change,
        "change_percent": percent,
        "open": float(last["Open"]),
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "volume": float(last["Volume"]),
        "as_of": str(last["Date"]),
    }


def bars_from_frame(frame: pd.DataFrame) -> list[dict]:
    bars = []
    for row in frame.itertuples(index=False):
        bars.append(
            {
                "time": str(row.Date),
                "open": float(row.Open),
                "high": float(row.High),
                "low": float(row.Low),
                "close": float(row.Close),
                "volume": float(row.Volume),
            }
        )
    return bars


def sma_series(frame: pd.DataFrame, window: int) -> list[dict]:
    rolled = frame["Close"].rolling(window).mean()
    points = []
    for date, value in zip(frame["Date"], rolled):
        if pd.notna(value):
            points.append({"time": str(date), "value": float(value)})
    return points


def _download_chunk(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    try:
        raw = yf.download(
            tickers=symbols if len(symbols) > 1 else symbols[0],
            period=period,
            auto_adjust=False,
            progress=False,
            threads=False,
            group_by="column",
        )
    except Exception:
        return {}
    return frames_from_download(raw, symbols)


def yfinance_fetcher(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    if not symbols:
        return {}
    found: dict[str, pd.DataFrame] = {}
    for start in range(0, len(symbols), 15):
        found.update(_download_chunk(symbols[start : start + 15], period))
    for symbol in symbols:
        if symbol not in found:
            found.update(_download_chunk([symbol], period))
    return found


class PriceCache:
    def __init__(
        self,
        root: Path,
        history_ttl: float = HISTORY_TTL_SECONDS,
        quote_ttl: float = QUOTE_TTL_SECONDS,
        fetcher=None,
        now=None,
    ):
        self.root = Path(root)
        self.history_ttl = history_ttl
        self.quote_ttl = quote_ttl
        self.fetcher = fetcher or yfinance_fetcher
        self.now = now or time.time
        self.history_fetches = 0
        self.quote_fetches = 0
        self._history_mem: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
        self._quote_mem: dict[str, tuple[float, dict]] = {}
        (self.root / "history").mkdir(parents=True, exist_ok=True)
        (self.root / "quotes").mkdir(parents=True, exist_ok=True)

    def _history_paths(self, symbol: str, period: str) -> tuple[Path, Path]:
        stem = self.root / "history" / f"{_safe_name(symbol)}__{period}"
        return Path(f"{stem}.csv"), Path(f"{stem}.json")

    def _quote_path(self, symbol: str) -> Path:
        return self.root / "quotes" / f"{_safe_name(symbol)}.json"

    def _read_history_disk(self, symbol: str, period: str) -> tuple[float, pd.DataFrame] | None:
        csv_path, meta_path = self._history_paths(symbol, period)
        if not csv_path.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text())
        frame = pd.read_csv(csv_path)
        return float(meta["saved_at"]), frame

    def _write_history_disk(self, symbol: str, period: str, saved_at: float, frame: pd.DataFrame) -> None:
        csv_path, meta_path = self._history_paths(symbol, period)
        frame.to_csv(csv_path, index=False)
        meta_path.write_text(json.dumps({"saved_at": saved_at}))

    def _read_quote_disk(self, symbol: str) -> tuple[float, dict] | None:
        path = self._quote_path(symbol)
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        return float(payload["saved_at"]), payload["quote"]

    def _write_quote_disk(self, symbol: str, saved_at: float, quote: dict) -> None:
        self._quote_path(symbol).write_text(json.dumps({"saved_at": saved_at, "quote": quote}))

    def get_history(self, symbol: str, period: str = "2y") -> pd.DataFrame | None:
        frames = self.get_histories([symbol], period)
        return frames.get(symbol)

    def get_histories(self, symbols: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
        if period not in HISTORY_PERIODS:
            raise ValueError(f"period must be one of {', '.join(HISTORY_PERIODS)}")
        now = float(self.now())
        found: dict[str, pd.DataFrame] = {}
        missing: list[str] = []
        for symbol in symbols:
            key = (symbol, period)
            cached = self._history_mem.get(key)
            if cached and now - cached[0] < self.history_ttl:
                found[symbol] = cached[1].copy()
                continue
            disk = self._read_history_disk(symbol, period)
            if disk and now - disk[0] < self.history_ttl:
                self._history_mem[key] = disk
                found[symbol] = disk[1].copy()
                continue
            missing.append(symbol)
        if not missing:
            return found
        fetched = self.fetcher(missing, period) or {}
        self.history_fetches += 1
        for symbol in missing:
            frame = fetched.get(symbol)
            if frame is None or frame.empty:
                continue
            self._history_mem[(symbol, period)] = (now, frame)
            self._write_history_disk(symbol, period, now, frame)
            found[symbol] = frame.copy()
        return found

    def get_quotes(self, symbols: list[str]) -> dict[str, dict]:
        now = float(self.now())
        found: dict[str, dict] = {}
        missing: list[str] = []
        for symbol in symbols:
            cached = self._quote_mem.get(symbol)
            if cached and now - cached[0] < self.quote_ttl:
                found[symbol] = cached[1]
                continue
            disk = self._read_quote_disk(symbol)
            if disk and now - disk[0] < self.quote_ttl:
                self._quote_mem[symbol] = disk
                found[symbol] = disk[1]
                continue
            missing.append(symbol)
        if not missing:
            return found
        fetched = self.fetcher(missing, "5d") or {}
        self.quote_fetches += 1
        for symbol in missing:
            frame = fetched.get(symbol)
            if frame is None or frame.empty:
                continue
            quote = quote_from_frame(frame)
            self._quote_mem[symbol] = (now, quote)
            self._write_quote_disk(symbol, now, quote)
            found[symbol] = quote
        return found
