"""Training sample construction (temporal holdout, no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from train_lstm import build_samples


def _frame(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": [f"2024-01-{i:02d}" for i in range(1, len(closes) + 1)],
            "Close": closes,
        }
    )


def test_holdout_is_tail_of_each_symbol():
    n = 150  # build_samples requires window + 80 closes
    closes = np.linspace(100, 200, n)
    frames = {"TEST.NS": _frame(closes.tolist())}
    window = 60
    holdout = 0.2
    x_train, y_train, held = build_samples(frames, window=window, holdout=holdout)
    x_hold, y_hold = held["TEST.NS"]
    total_windows = (n - 1) - window  # one log return per close step
    cut = int(total_windows * (1.0 - holdout))
    assert len(x_train) == cut
    assert len(x_hold) == total_windows - cut
    # Adjacent sliding windows share all but one return step.
    np.testing.assert_allclose(x_train[-1][1:], x_hold[0][:-1])
