"""Market history providers (Yahoo default; NSE CSV bundle optional)."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from market_data import _normalize_ohlcv, yfinance_fetcher

ROOT = Path(__file__).resolve().parent

PERIOD_TO_DAYS = {
    "5d": 7,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
    "5y": 1260,
}


class HistoryProvider:
    def fetch(self, symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
        raise NotImplementedError


class YahooHistoryProvider:
    """Default unofficial daily bars via ``yfinance`` (see ``market_data`` cache)."""

    def fetch(self, symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
        return yfinance_fetcher(symbols, period)


class LicensedIndiaDailyProvider:
    """Load vendor/NSE-style daily CSVs from ``NSE_CSV_DIR``.

    Expected layout (one file per symbol):

        {NSE_CSV_DIR}/RELIANCE.NS.csv
        {NSE_CSV_DIR}/HDFCBANK.NS.csv

    Columns: ``Date``, ``Open``, ``High``, ``Low``, ``Close``, ``Volume`` (case-insensitive).
    """

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root or os.environ.get("NSE_CSV_DIR", ROOT / "data" / "nse_daily"))

    def _csv_path(self, symbol: str) -> Path:
        safe = symbol.upper()
        for name in (f"{safe}.csv", f"{safe.replace('.NS', '')}.csv"):
            path = self.root / name
            if path.exists():
                return path
        return self.root / f"{safe}.csv"

    def fetch(self, symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
        if not self.root.is_dir():
            raise FileNotFoundError(
                f"NSE CSV directory not found: {self.root}. "
                "Set NSE_CSV_DIR or add files under backend/data/nse_daily/."
            )
        tail = PERIOD_TO_DAYS.get(period, PERIOD_TO_DAYS["2y"])
        out: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            path = self._csv_path(symbol)
            if not path.is_file():
                continue
            raw = pd.read_csv(path)
            raw.columns = [str(column).strip() for column in raw.columns]
            frame = _normalize_ohlcv(raw)
            if frame is None or frame.empty:
                continue
            out[symbol] = frame.tail(tail).reset_index(drop=True)
        return out


def get_history_provider() -> HistoryProvider:
    from app_config import market_data_provider

    if market_data_provider() == "nse_csv":
        return LicensedIndiaDailyProvider()
    return YahooHistoryProvider()


def provider_fetcher():
    """Callable matching ``PriceCache`` fetcher signature."""

    def _fetch(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
        return get_history_provider().fetch(symbols, period)

    return _fetch
