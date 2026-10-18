from __future__ import annotations

import numpy as np
import pandas as pd


def run_long_flat_backtest(
    dates: pd.Series,
    closes: np.ndarray,
    predicted_returns: np.ndarray,
    *,
    cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> dict:
    """
    Long when predicted next-day return > 0, else flat.
    Positions apply to next-day realized return (aligned with predictions).
    """
    n = len(closes)
    if n < 3 or len(predicted_returns) != n - 1:
        return {"error": "insufficient aligned data"}

    rets = np.diff(closes) / closes[:-1]
    pred = predicted_returns[: len(rets)]
    position = (pred > 0).astype(float)

    round_trip_cost = (cost_bps + slippage_bps) * 2 / 10_000
    turnover = np.abs(np.diff(np.r_[0, position]))
    strat_rets = position * rets - turnover * round_trip_cost / 2

    bh_rets = rets
    equity = np.cumprod(1 + strat_rets)
    bh_equity = np.cumprod(1 + bh_rets)

    ann_factor = 252
    years = max(len(strat_rets) / ann_factor, 1e-6)
    cagr = float(equity[-1] ** (1 / years) - 1) if len(equity) else 0.0
    bh_cagr = float(bh_equity[-1] ** (1 / years) - 1) if len(bh_equity) else 0.0

    sharpe = _sharpe(strat_rets)
    bh_sharpe = _sharpe(bh_rets)
    max_dd = _max_drawdown(equity)
    bh_max_dd = _max_drawdown(bh_equity)
    wins = float(np.mean(strat_rets > 0)) if len(strat_rets) else 0.0

    return {
        "cagr": round(cagr, 4),
        "buy_hold_cagr": round(bh_cagr, 4),
        "sharpe": round(sharpe, 4),
        "buy_hold_sharpe": round(bh_sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "buy_hold_max_drawdown": round(bh_max_dd, 4),
        "win_rate": round(wins, 4),
        "n_days": int(len(strat_rets)),
        "start_date": str(dates.iloc[1])[:10],
        "end_date": str(dates.iloc[-1])[:10],
        "equity_curve": [
            {"date": str(dates.iloc[i + 1])[:10], "strategy": float(equity[i]), "buy_hold": float(bh_equity[i])}
            for i in range(len(equity))
        ],
    }


def _sharpe(rets: np.ndarray) -> float:
    if len(rets) < 2 or np.std(rets) == 0:
        return 0.0
    return float(np.sqrt(252) * np.mean(rets) / np.std(rets))


def _max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(np.min(dd))
