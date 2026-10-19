"""Signal series for backtests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from features import SIGNAL_THRESHOLD, WINDOW, log_returns, signal_from_move


def signals_from_predicted_returns(
    predicted_returns: np.ndarray,
    threshold: float = SIGNAL_THRESHOLD,
) -> list[str]:
    return [signal_from_move(float(move), threshold) for move in predicted_returns]


def hold_signals(length: int) -> list[str]:
    return ["HOLD"] * length


def align_signal_series(dates: list[str], signals: list[str]) -> list[str]:
    if len(dates) != len(signals):
        raise ValueError("dates and signals must have the same length")
    return list(signals)


def predicted_returns_from_windows(
    predictor,
    closes: np.ndarray,
    threshold: float = SIGNAL_THRESHOLD,
) -> tuple[list[str], np.ndarray]:
    """One predicted next-day log return per close bar (HOLD before ``WINDOW``)."""
    n = len(closes)
    out = np.full(n, np.nan, dtype=np.float64)
    if not predictor.ready or n < WINDOW + 2:
        return hold_signals(n), out

    returns = log_returns(closes)
    signals: list[str] = []
    for index in range(n):
        if index < WINDOW:
            signals.append("HOLD")
            continue
        window = returns[index - WINDOW : index]
        pred = float(predictor._predict_scaled(window.reshape(1, WINDOW))[0])
        out[index] = pred
        signals.append(signal_from_move(pred, threshold))
    return signals, out


def frame_to_closes(frame: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    ordered = frame.sort_values("Date")
    dates = [str(value) for value in ordered["Date"].tolist()]
    closes = ordered["Close"].to_numpy(dtype=np.float64)
    return dates, closes
