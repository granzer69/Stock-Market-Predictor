from __future__ import annotations

import numpy as np
import pandas as pd

MACRO_TICKERS = {
    "nifty": "^NSEI",
    "india_vix": "^INDIAVIX",
    "usd_inr": "INR=X",
    "crude": "CL=F",
    "sp500": "^GSPC",
}


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def _bollinger(series: pd.Series, period: int = 20) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    return lower, mid, upper


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def build_symbol_features(df: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """OHLCV frame for one symbol + merged macro; adds indicators and next-day return target."""
    out = df.sort_values("Date").copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out = out.merge(macro, on="Date", how="left")
    out = out.sort_values("Date").reset_index(drop=True)

    close = out["Close"]
    out["return_1d"] = close.pct_change()
    out["log_return_1d"] = np.log(close / close.shift(1))
    out["target_return"] = out["return_1d"].shift(-1)
    out["target_close"] = close.shift(-1)

    out["rsi_14"] = _rsi(close, 14)
    macd, macd_sig, macd_hist = _macd(close)
    out["macd"] = macd
    out["macd_signal"] = macd_sig
    out["macd_hist"] = macd_hist
    bb_low, bb_mid, bb_up = _bollinger(close)
    out["bb_low"] = bb_low
    out["bb_mid"] = bb_mid
    out["bb_up"] = bb_up
    out["bb_pct"] = (close - bb_low) / (bb_up - bb_low).replace(0, np.nan)

    if {"High", "Low"}.issubset(out.columns):
        out["atr_14"] = _atr(out["High"], out["Low"], close, 14)
    else:
        out["atr_14"] = close.rolling(14).std()

    vol = out["Volume"] if "Volume" in out.columns else pd.Series(0, index=out.index)
    vol_ma = vol.rolling(20).mean()
    vol_std = vol.rolling(20).std().replace(0, np.nan)
    out["volume_z"] = (vol - vol_ma) / vol_std

    out["sma_20"] = close.rolling(20).mean()
    out["sma_50"] = close.rolling(50).mean()
    out["ma_ratio"] = out["sma_20"] / out["sma_50"]

    macro_cols = [c for c in macro.columns if c != "Date"]
    for c in macro_cols:
        if c in out.columns:
            out[f"{c}_ret"] = out[c].pct_change()

    feature_cols = [
        "return_1d",
        "log_return_1d",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_pct",
        "atr_14",
        "volume_z",
        "ma_ratio",
    ] + [f"{c}_ret" for c in macro_cols if f"{c}_ret" in out.columns]

    return out


FEATURE_COLUMNS = [
    "return_1d",
    "log_return_1d",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_pct",
    "atr_14",
    "volume_z",
    "ma_ratio",
    "nifty_ret",
    "india_vix_ret",
    "usd_inr_ret",
    "crude_ret",
    "sp500_ret",
]
