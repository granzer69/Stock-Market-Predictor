#!/usr/bin/env python3
"""Download OHLCV for Nifty 50 + macro series; write panel CSV."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS_CSV = ROOT / "data" / "nifty50_symbols.csv"
OUT_DIR = ROOT / "backend" / "data"
PANEL_CSV = OUT_DIR / "ohlcv_panel.csv"
MACRO_CSV = OUT_DIR / "macro_series.csv"
REPORT_JSON = OUT_DIR / "ohlcv_fetch_report.json"

from ml.features import MACRO_TICKERS  # noqa: E402


def fetch_macro() -> pd.DataFrame:
    frames = []
    for name, ticker in MACRO_TICKERS.items():
        raw = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
        if raw is None or raw.empty:
            continue
        if isinstance(raw.columns, pd.MultiIndex):
            raw = raw.droplevel(1, axis=1)
        df = raw.reset_index()
        df = df.rename(columns={"Date": "Date", "Close": name})
        frames.append(df[["Date", name]])
        time.sleep(0.2)
    macro = frames[0]
    for f in frames[1:]:
        macro = macro.merge(f, on="Date", how="outer")
    macro["Date"] = pd.to_datetime(macro["Date"]).dt.strftime("%Y-%m-%d")
    return macro.sort_values("Date")


def fetch_symbol(ticker: str, retries: int = 2) -> pd.DataFrame:
    for attempt in range(retries + 1):
        raw = yf.download(
            ticker, period="5y", interval="1d", auto_adjust=True, progress=False
        )
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw = raw.droplevel(1, axis=1)
            df = raw.reset_index()
            df["Symbol"] = ticker
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
            return df
        time.sleep(2**attempt)
    return pd.DataFrame()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sym_df = pd.read_csv(SYMBOLS_CSV)
    tickers = sym_df["yahoo_symbol"].tolist()

    macro = fetch_macro()
    macro.to_csv(MACRO_CSV, index=False)

    parts: list[pd.DataFrame] = []
    dropped = []
    for i, t in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {t}")
        df = fetch_symbol(t)
        if len(df) < 200:
            dropped.append({"symbol": t, "rows": len(df)})
            continue
        parts.append(df)
        time.sleep(0.25)

    panel = pd.concat(parts, ignore_index=True)
    panel.to_csv(PANEL_CSV, index=False)

    report = {
        "symbols_kept": len(parts),
        "symbols_dropped": dropped,
        "panel_rows": len(panel),
        "macro_columns": list(macro.columns),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2))
    print(f"Wrote {PANEL_CSV} ({len(panel)} rows)")


if __name__ == "__main__":
    main()
