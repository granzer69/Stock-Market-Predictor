"""Shared research helpers (API + CLI)."""

from __future__ import annotations

import pandas as pd

from app_config import RESEARCH_PORTFOLIO_MAX_SYMBOLS
from backtest.engine import BacktestConfig, run_long_only_backtest
from backtest.portfolio_engine import run_portfolio_backtest
from backtest.report import buy_and_hold_benchmark, equal_weight_buy_hold, max_drawdown, summarize_result
from backtest.signals import frame_to_closes, predicted_returns_from_windows
from predictor import Predictor

MAX_CURVE_POINTS = 400


def downsample_curve(curve: list[dict], max_points: int = MAX_CURVE_POINTS) -> list[dict]:
    if len(curve) <= max_points:
        return curve
    step = max(1, len(curve) // max_points)
    sampled = [curve[index] for index in range(0, len(curve), step)]
    if sampled[-1] != curve[-1]:
        sampled.append(curve[-1])
    return sampled


def _curve_payload(curve: list[dict]) -> list[dict]:
    return [{"time": point["time"], "equity": point["equity"]} for point in downsample_curve(curve)]


def backtest_from_frame(
    symbol: str,
    frame: pd.DataFrame,
    predictor: Predictor,
    period: str,
    config: BacktestConfig | None = None,
) -> dict:
    dates, closes = frame_to_closes(frame)
    if len(dates) < 65:
        raise ValueError("not enough history for backtest")
    signals, _ = predicted_returns_from_windows(predictor, closes)
    result = run_long_only_backtest(dates, closes, signals, config or BacktestConfig())
    strategy = summarize_result(result)
    bench_curve = buy_and_hold_benchmark(dates, closes, result.starting_cash)
    bench_end = bench_curve[-1]["equity"] if bench_curve else result.starting_cash
    return {
        "symbol": symbol,
        "period": period,
        "strategy": strategy,
        "equity_curve": _curve_payload(result.equity_curve),
        "benchmark": {
            "kind": "buy_and_hold",
            "ending_equity": bench_end,
            "total_return": (bench_end - result.starting_cash) / result.starting_cash,
            "max_drawdown": max_drawdown(bench_curve),
            "equity_curve": _curve_payload(bench_curve),
        },
        "disclaimer": "Offline simulation with India delivery costs; not investment advice.",
    }


def _align_frames(frames: dict[str, pd.DataFrame]) -> tuple[list[str], dict[str, pd.DataFrame]]:
    if not frames:
        raise ValueError("no frames")
    panel = None
    for symbol, frame in frames.items():
        piece = frame[["Date", "Close"]].copy()
        piece["Date"] = piece["Date"].astype(str)
        piece = piece.rename(columns={"Close": symbol})
        panel = piece if panel is None else panel.merge(piece, on="Date", how="inner")
    panel = panel.sort_values("Date")
    if panel is None or panel.empty:
        raise ValueError("no overlapping dates across symbols")
    dates = panel["Date"].tolist()
    aligned = {}
    for symbol in frames:
        if symbol not in panel.columns:
            continue
        aligned[symbol] = pd.DataFrame({"Date": dates, "Close": panel[symbol].astype(float)})
    return dates, aligned


def portfolio_backtest(
    frames: dict[str, pd.DataFrame],
    predictor: Predictor,
    period: str,
    symbols: list[str],
    config: BacktestConfig | None = None,
) -> dict:
    if len(symbols) > RESEARCH_PORTFOLIO_MAX_SYMBOLS:
        raise ValueError(f"at most {RESEARCH_PORTFOLIO_MAX_SYMBOLS} symbols")
    subset = {key: frames[key] for key in symbols if key in frames}
    if len(subset) < 2:
        raise ValueError("need at least two symbols with history")
    timeline, aligned = _align_frames(subset)
    if len(timeline) < 65:
        raise ValueError("not enough history for backtest")

    prices: dict[str, dict[str, float]] = {}
    signal_map: dict[str, dict[str, str]] = {}
    for symbol, frame in aligned.items():
        dates, closes = frame_to_closes(frame)
        signals, _ = predicted_returns_from_windows(predictor, closes)
        prices[symbol] = dict(zip(dates, closes.tolist()))
        signal_map[symbol] = dict(zip(dates, signals))

    cfg = config or BacktestConfig()
    result = run_portfolio_backtest(timeline, prices, signal_map, cfg)
    strategy = summarize_result(result)
    bench_dates, bench_curve = equal_weight_buy_hold(aligned, cfg.starting_cash)
    bench_end = bench_curve[-1]["equity"] if bench_curve else cfg.starting_cash
    return {
        "kind": "portfolio",
        "symbols": list(aligned.keys()),
        "period": period,
        "strategy": strategy,
        "equity_curve": _curve_payload(result.equity_curve),
        "benchmark": {
            "kind": "equal_weight_buy_hold",
            "ending_equity": bench_end,
            "total_return": (bench_end - cfg.starting_cash) / cfg.starting_cash,
            "max_drawdown": max_drawdown(bench_curve),
            "equity_curve": _curve_payload(bench_curve),
        },
        "disclaimer": "Shared-cash multi-name simulation; not investment advice.",
    }
