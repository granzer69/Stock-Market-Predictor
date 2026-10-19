#!/usr/bin/env python3
"""Walk-forward *evaluation* of the committed LSTM on cached Yahoo history (no retrain).

Run from repo root (needs network if history is not cached):

    python backend/scripts/walk_forward_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from features import WINDOW, log_returns  # noqa: E402
from market_data import yfinance_fetcher  # noqa: E402
from predictor import Predictor  # noqa: E402
from train_lstm import directional_accuracy  # noqa: E402
from universe import NIFTY_50  # noqa: E402
from walk_forward import expanding_walk_forward_splits  # noqa: E402

ARTIFACTS = BACKEND / "artifacts"
DEFAULT_FOLDS = 5
DEFAULT_MIN_TRAIN = 120


def symbol_windows(closes: np.ndarray, window: int = WINDOW) -> tuple[np.ndarray, np.ndarray]:
    returns = log_returns(closes)
    xs, ys = [], []
    for index in range(window, len(returns)):
        xs.append(returns[index - window : index])
        ys.append(returns[index])
    return np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64)


def main() -> int:
    predictor = Predictor(ARTIFACTS)
    predictor.load()
    if not predictor.ready:
        print("Model artifacts not found; train with backend/train_lstm.py first.", file=sys.stderr)
        return 1

    symbols = [item.symbol for item in NIFTY_50]
    frames = yfinance_fetcher(symbols, "5y")
    n_folds = int(__import__("os").environ.get("WF_FOLDS", str(DEFAULT_FOLDS)))
    min_train = int(__import__("os").environ.get("WF_MIN_TRAIN", str(DEFAULT_MIN_TRAIN)))

    fold_stats: list[dict] = []
    all_actual: list[float] = []
    all_pred: list[float] = []

    for symbol, frame in sorted(frames.items()):
        closes = frame["Close"].to_numpy(dtype=np.float64)
        if len(closes) < WINDOW + min_train + n_folds:
            continue
        xs, ys = symbol_windows(closes)
        try:
            splits = expanding_walk_forward_splits(len(xs), n_folds=n_folds, min_train=min_train)
        except ValueError:
            continue
        for fold_index, split in enumerate(splits):
            chunk = xs[split.test_start : split.test_end]
            actual = ys[split.test_start : split.test_end]
            pred = predictor._predict_scaled(chunk)
            mae = float(np.mean(np.abs(actual - pred)))
            dir_acc = directional_accuracy(actual, pred)
            fold_stats.append(
                {
                    "symbol": symbol,
                    "fold": fold_index,
                    "n": len(actual),
                    "mae_log_return": mae,
                    "directional_accuracy": dir_acc,
                }
            )
            all_actual.extend(actual.tolist())
            all_pred.extend(pred.tolist())

    if not fold_stats:
        print("No symbol produced walk-forward folds; check history length.", file=sys.stderr)
        return 1

    actual_arr = np.asarray(all_actual)
    pred_arr = np.asarray(all_pred)
    summary = {
        "n_folds_config": n_folds,
        "min_train_windows": min_train,
        "fold_rows": len(fold_stats),
        "pooled_mae_log_return": float(np.mean(np.abs(actual_arr - pred_arr))),
        "pooled_directional_accuracy": directional_accuracy(actual_arr, pred_arr),
        "per_fold_sample": fold_stats[:12],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
