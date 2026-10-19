# Walk-forward methodology — Bharat Desk

This document describes how we evaluate the LSTM **without** shuffling time, and how to run a multi-fold **evaluation** (not retrain) on the committed model.

## Current training holdout (Phase 2)

[`build_samples`](backend/train_lstm.py) builds sliding windows per symbol, then:

1. **Per symbol:** last `holdout_fraction` (20%) of windows are held out for metrics in `metrics.json`.
2. **Pooled fit:** remaining windows from all symbols are concatenated; `model.fit(..., shuffle=False, validation_split=0.1)` uses the last 10% of that pool as Keras validation.

Holdout per symbol is temporal; the pooled train/val split is **global** after concatenation (see [MODEL_CARD.md](MODEL_CARD.md)).

Helpers: [`holdout_cut`](backend/walk_forward.py) mirrors the per-symbol cut index.

## Expanding walk-forward evaluation

For research, we tile the **tail** of each symbol’s window series into `n_folds` contiguous test blocks. Training context for fold *k* is all windows **before** that block (expanding). The committed model is scored on each test block—**no retrain per fold** in the default script.

```
|-- min_train --|-- fold0 --|-- fold1 --| ... |-- foldN-1 --|
^ train [0, t0)  ^ test      ^ train grows each fold
```

Implementation: [`expanding_walk_forward_splits`](backend/walk_forward.py).

### Run report

```bash
pip install -r backend/requirements.txt
python backend/scripts/walk_forward_report.py
```

Environment:

| Variable | Default | Meaning |
|----------|---------|---------|
| `WF_FOLDS` | `5` | Number of test blocks per symbol |
| `WF_MIN_TRAIN` | `120` | Minimum training windows before first test block |

Output is JSON on stdout (pooled MAE / directional accuracy across all fold slices). Requires Yahoo history (or cache) and trained artifacts.

## Future work (not implemented)

- **Rolling retrain:** refit scaler + LSTM at each fold boundary (expensive; needs job orchestration).
- **Purged/embargo gaps** for overlapping labels (not needed for single-day horizon with non-overlapping targets).
- Wire walk-forward metrics into CI only on a schedule (full eval is slow and network-dependent).
