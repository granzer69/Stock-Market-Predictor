# Engineering roadmap

Iteration 1 is accepted. Iteration 2 is in review. Later items stay out of both.

## Iteration 1 — one named forecast (this change)

- Desk hints keep `as_of`, base close, and model id from `predict_symbol`.
- The served id is `lightgbm`. The hit rate, when present, is the LightGBM pooled figure and the payload names the source.
- The last panel date is scored even though `target_return` is null.
- Momentum in `scripts/run_evaluation.py` is the previous return's sign. The report file is not rewritten.
- Markets and the symbol page show the payload model id. Research copy stays LSTM.
- Tests cover provenance and the label fix. No new holdout metric.

Details: [architecture.md](architecture.md), [decision-log.md](decision-log.md), [iteration-log.md](iteration-log.md).

## Iteration 2 — page versus API for Evaluation and Backtest

In review. FastAPI `GET /evaluation` and `GET /backtest` stay. The Next documents stay on those paths. The pages fetch `GET /api/evaluation` and `GET /api/legacy/backtest`. The evaluation response is strict JSON. See [iteration-log.md](iteration-log.md) and [known-issues.md](known-issues.md).

## Later, not scheduled here

- Score the live bar with one model. Depends on the provenance test already in the tree, and on cache validation, which is separate.
- Lag same-calendar US features, then score the booster that is actually saved. No refit until that is true.
- Optional shared token and fill-time marks for the paper book. Not an account system. [RETRAIN_POLICY.md](../RETRAIN_POLICY.md) does not cover the book.
- Survivorship and corporate actions, after the labels above stay honest. [MODEL_CARD.md](../MODEL_CARD.md) and [CODEBASE_AUDIT.md](../CODEBASE_AUDIT.md) describe the current LSTM holdout; do not replace those numbers to make a new universe look better.

## Out of scope

A third model, per-user KYC, a live tick feed, and another chart library. The contract for fields the API returns is [API_SPEC.md](../API_SPEC.md).
