"""Temporal split helpers for walk-forward evaluation (no model I/O)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeSplit:
    """One expanding-window fold: train on ``[0, test_start)``, test on ``[test_start, test_end)``."""

    test_start: int
    test_end: int


def holdout_cut(n_samples: int, holdout_fraction: float) -> int:
    """Index where training windows end (exclusive); holdout is ``[cut, n_samples)``."""
    if n_samples < 2:
        raise ValueError("n_samples must be at least 2")
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError("holdout_fraction must be between 0 and 1")
    cut = int(n_samples * (1.0 - holdout_fraction))
    if cut < 1:
        cut = 1
    if cut >= n_samples:
        cut = n_samples - 1
    return cut


def expanding_walk_forward_splits(n_samples: int, n_folds: int, min_train: int) -> list[TimeSplit]:
    """Expanding-window folds over ``n_samples`` ordered windows.

    Fold *k* trains on indices ``[0, test_start)`` and tests on ``[test_start, test_end)``.
    The training set grows after each fold; test blocks tile the tail after ``min_train``.
    """
    if n_folds < 1:
        raise ValueError("n_folds must be at least 1")
    if min_train < 1:
        raise ValueError("min_train must be at least 1")
    if n_samples <= min_train:
        raise ValueError("n_samples must exceed min_train")

    tail = n_samples - min_train
    if tail < n_folds:
        raise ValueError("not enough tail samples for n_folds")

    base = tail // n_folds
    extra = tail % n_folds
    splits: list[TimeSplit] = []
    test_start = min_train
    for fold in range(n_folds):
        block = base + (1 if fold < extra else 0)
        test_end = test_start + block
        if fold == n_folds - 1:
            test_end = n_samples
        if test_end <= test_start:
            raise ValueError("degenerate fold; adjust min_train or n_folds")
        splits.append(TimeSplit(test_start=test_start, test_end=test_end))
        test_start = test_end
    return splits
