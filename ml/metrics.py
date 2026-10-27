from __future__ import annotations

import numpy as np


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    mask = np.abs(actual) > 1e-9
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100)


def rmse(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def directional_accuracy(actual: np.ndarray, pred: np.ndarray) -> float:
    """Fraction of times sign(predicted value) matches sign(actual value)."""
    if len(actual) == 0:
        return float("nan")
    act_dir = np.sign(actual)
    pred_dir = np.sign(pred)
    mask = act_dir != 0
    if not np.any(mask):
        return float("nan")
    return float(np.mean(act_dir[mask] == pred_dir[mask]))


def directional_accuracy_from_closes(
    actual_next: np.ndarray, pred_next: np.ndarray, prev_close: np.ndarray
) -> float:
    act_ret = (actual_next - prev_close) / np.where(prev_close == 0, np.nan, prev_close)
    pred_ret = (pred_next - prev_close) / np.where(prev_close == 0, np.nan, prev_close)
    mask = np.isfinite(act_ret) & np.isfinite(pred_ret) & (act_ret != 0)
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.sign(act_ret[mask]) == np.sign(pred_ret[mask])))


def momentum_directional_accuracy(closes: np.ndarray, split: int) -> dict:
    """Directional accuracy of the sign of the previous return.

    The return being graded runs from ``closes[split - 1 + j]`` to
    ``closes[split + j]``. Momentum is the sign of the return that ended on
    the prior bar, not the sign of that same move.
    """
    closes = np.asarray(closes, dtype=np.float64)
    actual_next = closes[split:]
    prev_close = closes[split - 1 : -1]
    actual_ret = (actual_next - prev_close) / np.where(prev_close == 0, np.nan, prev_close)
    mom = np.diff(closes)[split - 2 : split - 2 + len(actual_ret)]
    mask = np.isfinite(mom) & (actual_ret != 0)
    if np.any(mask):
        accuracy = float(np.mean(np.sign(mom[mask]) == np.sign(actual_ret[mask])))
    else:
        accuracy = 0.5
    return {
        "directional_accuracy": round(accuracy, 4),
        "n_samples": int(len(actual_ret)),
    }


def naive_mae(actual: np.ndarray) -> float:
    """MAE of predicting zero.

    This is the same quantity ``train_lstm`` stores as ``naive_mae_log_return``:
    the mean absolute value of the holdout log returns.
    """
    actual = np.asarray(actual, dtype=np.float64)
    if actual.size == 0:
        return float("nan")
    return float(np.mean(np.abs(actual)))


def summarize(
    actual: np.ndarray,
    pred: np.ndarray,
    *,
    prev_close: np.ndarray | None = None,
) -> dict[str, float]:
    if prev_close is not None and len(prev_close) == len(actual):
        dir_acc = directional_accuracy_from_closes(actual, pred, prev_close)
    else:
        dir_acc = directional_accuracy(actual, pred)
    return {
        "mape_pct": round(mape(actual, pred), 4),
        "rmse": round(rmse(actual, pred), 4),
        "directional_accuracy": round(dir_acc, 4),
        "n_samples": int(len(actual)),
    }
