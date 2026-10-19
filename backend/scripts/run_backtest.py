#!/usr/bin/env python3
"""Run a long-only signal backtest + equal-weight benchmark (stdout JSON).

Example:

    python backend/scripts/run_backtest.py --symbol RELIANCE.NS
    python backend/scripts/run_backtest.py --all  # one backtest per symbol (slow)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from backtest.engine import BacktestConfig, run_long_only_backtest  # noqa: E402
from backtest.report import equal_weight_buy_hold, max_drawdown, summarize_result  # noqa: E402
from backtest.signals import frame_to_closes, predicted_returns_from_windows  # noqa: E402
from data_providers import YahooHistoryProvider  # noqa: E402
from predictor import Predictor  # noqa: E402
from universe import NIFTY_50  # noqa: E402

ARTIFACTS = BACKEND / "artifacts"


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline LSTM signal backtest")
    parser.add_argument("--symbol", help="Single NSE symbol, e.g. RELIANCE.NS")
    parser.add_argument("--all", action="store_true", help="Run every Nifty 50 symbol (separate ledgers)")
    parser.add_argument("--period", default="5y", help="Yahoo history period")
    args = parser.parse_args()

    symbols = [item.symbol for item in NIFTY_50]
    if args.symbol:
        symbols = [args.symbol]
    elif not args.all:
        symbols = [symbols[0]]

    provider = YahooHistoryProvider()
    frames = provider.fetch(symbols, args.period)
    if not frames:
        print("No history returned.", file=sys.stderr)
        return 1

    predictor = Predictor(ARTIFACTS)
    predictor.load()
    if not predictor.ready:
        print("Train model first (backend/train_lstm.py).", file=sys.stderr)
        return 1

    config = BacktestConfig()
    per_symbol = {}
    for symbol, frame in sorted(frames.items()):
        dates, closes = frame_to_closes(frame)
        signals, _ = predicted_returns_from_windows(predictor, closes)
        result = run_long_only_backtest(dates, closes, signals, config)
        per_symbol[symbol] = summarize_result(result)

    bench_dates, bench_curve = equal_weight_buy_hold(frames, config.starting_cash)
    benchmark = {
        "dates": len(bench_dates),
        "ending_equity": bench_curve[-1]["equity"] if bench_curve else config.starting_cash,
        "max_drawdown": max_drawdown(bench_curve),
    }

    print(json.dumps({"symbols": per_symbol, "benchmark_equal_weight": benchmark}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
