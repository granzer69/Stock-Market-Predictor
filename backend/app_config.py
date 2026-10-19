"""Runtime flags (env-driven, safe to expose on /api/config)."""

from __future__ import annotations

import os
from pathlib import Path

VALID_MARKET_PROVIDERS = frozenset({"yahoo", "nse_csv", "licensed", "csv"})
RESEARCH_PORTFOLIO_MAX_SYMBOLS = 10
DEFAULT_CORS = ("http://localhost:3000", "http://127.0.0.1:3000")
RESEARCH_MAX_CONCURRENT = 2


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def market_data_provider() -> str:
    raw = os.environ.get("MARKET_DATA_PROVIDER", "yahoo").strip().lower()
    if raw in {"licensed", "csv"}:
        return "nse_csv"
    if raw in VALID_MARKET_PROVIDERS:
        return raw if raw != "csv" else "nse_csv"
    return "yahoo"


def market_data_failover_enabled() -> bool:
    return _truthy("MARKET_DATA_FAILOVER", default=True)


def nse_csv_dir() -> str:
    return os.environ.get("NSE_CSV_DIR", "")


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_CORS)
    return [part.strip() for part in raw.split(",") if part.strip()]


def paper_apply_india_costs() -> bool:
    return _truthy("PAPER_APPLY_INDIA_COSTS", default=False)


def default_backtest_fill() -> str:
    """``close`` (same bar) or ``next_close`` (next session close)."""
    raw = os.environ.get("BACKTEST_FILL", "close").strip().lower()
    return raw if raw in {"close", "next_close"} else "close"


def paper_db_path(base_dir: Path) -> Path:
    raw = os.environ.get("PAPER_DB_PATH", "").strip()
    if raw:
        return Path(raw)
    return base_dir / "paper_trading.db"


def research_max_concurrent() -> int:
    try:
        return max(1, int(os.environ.get("RESEARCH_MAX_CONCURRENT", str(RESEARCH_MAX_CONCURRENT))))
    except ValueError:
        return RESEARCH_MAX_CONCURRENT


def public_config() -> dict:
    provider = market_data_provider()
    return {
        "market_data_provider": provider,
        "market_data_label": "NSE CSV bundle" if provider == "nse_csv" else "Yahoo Finance",
        "market_data_failover": market_data_failover_enabled(),
        "research_portfolio_max_symbols": RESEARCH_PORTFOLIO_MAX_SYMBOLS,
        "paper_apply_india_costs": paper_apply_india_costs(),
        "backtest_default_fill": default_backtest_fill(),
        "model_card_url": "/MODEL_CARD.md",
    }
