"""Log-return windows shared by training and inference."""

from __future__ import annotations

import numpy as np

WINDOW = 60
COMPARE_POINTS = 30
SIGNAL_THRESHOLD = 0.003
# A single bad print (around -50%) otherwise dominates min-max scaling.
RETURN_CLIP = 0.2


def log_returns(closes: np.ndarray) -> np.ndarray:
    prices = np.asarray(closes, dtype=np.float64)
    if np.any(prices <= 0):
        raise ValueError("closes must be positive")
    returns = np.diff(np.log(prices))
    return np.clip(returns, -RETURN_CLIP, RETURN_CLIP)


def next_return_window(closes: np.ndarray, window: int = WINDOW) -> np.ndarray:
    returns = log_returns(closes)
    if len(returns) < window:
        raise ValueError(f"need at least {window + 1} closes")
    return returns[-window:]


def build_inference_batch(
    closes: np.ndarray,
    window: int = WINDOW,
    compare: int = COMPARE_POINTS,
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Stack historical windows plus the next-day window.

    Each historical target index ``t`` predicts ``log(close[t+1] / close[t])``
    from the preceding ``window`` returns. The final row predicts the return
    after the last close and has no alignment entry.
    """
    returns = log_returns(closes)
    if len(returns) < window:
        raise ValueError(f"need at least {window + 1} closes")

    t_start = max(window, len(returns) - compare)
    targets = list(range(t_start, len(returns)))
    windows = [returns[t - window : t] for t in targets]
    windows.append(returns[-window:])
    align = [(t, t + 1) for t in targets]
    return np.stack(windows).astype(np.float64), align


def scale_windows(windows: np.ndarray, scaler) -> np.ndarray:
    """Scale return windows to ``(samples, window, 1)``."""
    if windows.ndim == 1:
        windows = windows.reshape(1, -1)
    scaled = scaler.transform(windows.reshape(-1, 1)).reshape(windows.shape[0], windows.shape[1], 1)
    return scaled.astype(np.float32)


def price_from_log_return(last_close: float, log_return: float) -> float:
    return float(last_close * np.exp(log_return))


def signal_from_move(move: float, threshold: float = SIGNAL_THRESHOLD) -> str:
    if move > threshold:
        return "BUY"
    if move < -threshold:
        return "SELL"
    return "HOLD"
