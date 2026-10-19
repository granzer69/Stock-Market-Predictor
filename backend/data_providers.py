"""Market history providers (Yahoo today; licensed feeds later)."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from market_data import yfinance_fetcher


class HistoryProvider(Protocol):
    def fetch(self, symbols: list[str], period: str) -> dict[str, pd.DataFrame]: ...


class YahooHistoryProvider:
    """Default unofficial daily bars via ``yfinance`` (see ``market_data`` cache)."""

    def fetch(self, symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
        return yfinance_fetcher(symbols, period)


class LicensedIndiaDailyProvider:
    """Placeholder for NSE/BSE licensed CSV or API — not implemented."""

    def fetch(self, symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
        raise NotImplementedError(
            "Licensed India daily data is not configured. "
            "Implement fetch() with your vendor SDK or drop CSVs into a local loader."
        )
