#!/usr/bin/env python3
"""Download Nifty 50 daily closes from Yahoo Finance (.NS tickers)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS_CSV = ROOT / "data" / "nifty50_symbols.csv"
OUT_CSV = ROOT / "backend" / "data" / "nifty50_closes.csv"
REPORT_JSON = ROOT / "backend" / "data" / "fetch_report.json"
MIN_ROWS = 200
MIN_SYMBOLS = 45
CHUNK_SIZE = 10


def load_symbols() -> pd.DataFrame:
    df = pd.read_csv(SYMBOLS_CSV)
    required = {"nse_symbol", "yahoo_symbol", "name", "sector"}
    if not required.issubset(df.columns):
        raise SystemExit(f"{SYMBOLS_CSV} must contain columns: {sorted(required)}")
    return df


def fetch_chunk(tickers: list[str], retries: int = 2) -> pd.DataFrame | None:
    for attempt in range(retries + 1):
        try:
            raw = yf.download(
                tickers,
                period="5y",
                interval="1d",
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )
            if raw is None or raw.empty:
                continue
            return raw
        except Exception as exc:  # noqa: BLE001
            if attempt >= retries:
                print(f"Chunk failed after retries: {tickers[:3]}... ({exc})")
                return None
            time.sleep(2 ** attempt)
    return None


def extract_closes(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if len(ticker.split(".")) == 1:
        yahoo = f"{ticker}.NS"
    else:
        yahoo = ticker

    if isinstance(raw.columns, pd.MultiIndex):
        if yahoo not in raw.columns.get_level_values(0):
            return pd.DataFrame()
        sub = raw[yahoo]
    else:
        sub = raw

    if "Close" not in sub.columns:
        return pd.DataFrame()

    closes = sub["Close"].dropna()
    if closes.empty:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "Symbol": yahoo,
            "Date": closes.index.strftime("%Y-%m-%d"),
            "Close": closes.values.astype(float),
        }
    )
    return out


def main() -> None:
    symbols_df = load_symbols()
    tickers = symbols_df["yahoo_symbol"].tolist()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    dropped: list[dict] = []
    kept: list[str] = []

    for i in range(0, len(tickers), CHUNK_SIZE):
        chunk = tickers[i : i + CHUNK_SIZE]
        print(f"Fetching {i + 1}-{i + len(chunk)} / {len(tickers)}...")
        raw = fetch_chunk(chunk)
        if raw is None:
            for t in chunk:
                dropped.append({"yahoo_symbol": t, "reason": "download_failed"})
            continue

        for t in chunk:
            part = extract_closes(raw, t)
            if len(part) < MIN_ROWS:
                dropped.append(
                    {
                        "yahoo_symbol": t,
                        "reason": "insufficient_rows",
                        "rows": int(len(part)),
                    }
                )
                continue
            frames.append(part)
            kept.append(t)

        time.sleep(0.5)

    if len(kept) < MIN_SYMBOLS:
        raise SystemExit(
            f"Only {len(kept)} symbols met row threshold (need {MIN_SYMBOLS}). "
            f"See {REPORT_JSON}."
        )

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["Symbol", "Date"])
    combined.to_csv(OUT_CSV, index=False)

    date_min = combined["Date"].min()
    date_max = combined["Date"].max()
    report = {
        "symbols_requested": len(tickers),
        "symbols_kept": len(kept),
        "symbols_dropped": dropped,
        "date_range": {"min": date_min, "max": date_max},
        "output_csv": str(OUT_CSV.relative_to(ROOT)),
        "min_rows_per_symbol": MIN_ROWS,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2))
    print(f"Wrote {OUT_CSV} ({len(combined)} rows, {len(kept)} symbols)")


if __name__ == "__main__":
    main()
