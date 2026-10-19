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
