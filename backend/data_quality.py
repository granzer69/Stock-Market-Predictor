"""OHLCV sanity checks before training or backtest."""

from __future__ import annotations

import pandas as pd


def validate_ohlcv_frame(frame: pd.DataFrame, symbol: str = "") -> list[str]:
    issues: list[str] = []
    prefix = f"{symbol}: " if symbol else ""
    if frame is None or frame.empty:
        issues.append(f"{prefix}empty frame")
        return issues
    required = {"Date", "Close"}
    missing = required - set(frame.columns)
    if missing:
        issues.append(f"{prefix}missing columns {sorted(missing)}")
        return issues
    if frame["Close"].le(0).any():
        issues.append(f"{prefix}non-positive close prices")
    dates = pd.to_datetime(frame["Date"], errors="coerce")
    if dates.isna().any():
        issues.append(f"{prefix}unparseable dates")
    if dates.duplicated().any():
        issues.append(f"{prefix}duplicate dates")
    ordered = frame.sort_values("Date")
    if not ordered["Date"].equals(frame["Date"]):
        issues.append(f"{prefix}dates not sorted")
    gaps = dates.sort_values().diff().dt.days.dropna()
    if len(gaps) > 0 and (gaps > 10).sum() > len(gaps) * 0.05:
        issues.append(f"{prefix}frequent calendar gaps (>10d)")
    return issues
