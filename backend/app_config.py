"""Runtime flags (env-driven, safe to expose on /api/config)."""

from __future__ import annotations

import os

VALID_MARKET_PROVIDERS = frozenset({"yahoo", "nse_csv", "licensed", "csv"})
RESEARCH_PORTFOLIO_MAX_SYMBOLS = 10


def market_data_provider() -> str:
    raw = os.environ.get("MARKET_DATA_PROVIDER", "yahoo").strip().lower()
    if raw in {"licensed", "csv"}:
        return "nse_csv"
    if raw in VALID_MARKET_PROVIDERS:
        return raw if raw != "csv" else "nse_csv"
    return "yahoo"


def nse_csv_dir() -> str:
    return os.environ.get("NSE_CSV_DIR", "")


def public_config() -> dict:
    provider = market_data_provider()
    return {
        "market_data_provider": provider,
        "market_data_label": "NSE CSV bundle" if provider == "nse_csv" else "Yahoo Finance",
        "research_portfolio_max_symbols": RESEARCH_PORTFOLIO_MAX_SYMBOLS,
    }
