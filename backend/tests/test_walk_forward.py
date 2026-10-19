"""Walk-forward split helpers."""

from walk_forward import expanding_walk_forward_splits, holdout_cut


def test_holdout_cut_matches_train_lstm_style():
    n = 89
    cut = holdout_cut(n, 0.2)
    assert cut == 71
    assert n - cut == 18


def test_expanding_splits_cover_tail_without_gaps():
    n = 200
    min_train = 50
    n_folds = 5
    splits = expanding_walk_forward_splits(n, n_folds=n_folds, min_train=min_train)
    assert len(splits) == n_folds
    assert splits[0].test_start == min_train
    assert splits[-1].test_end == n
    for left, right in zip(splits, splits[1:]):
        assert left.test_end == right.test_start
