# Nifty 50 universe maintenance

Constituents live in [`backend/universe.py`](backend/universe.py) (`NIFTY_50` tuple).

## When to update

- NSE publishes a Nifty 50 rebalance (typically semi-annual).
- Ticker renames (e.g. `TMPV`).

## Checklist

1. Update `_equity(...)` entries to match the official NSE list.
2. Run `python3 -m pytest -q` (universe resolve tests via API).
3. Regenerate OpenAPI if routes change: `python backend/scripts/export_openapi.py`.
4. Retrain LSTM if composition shift is material: `python backend/train_lstm.py`.
5. Note the change in [CHANGELOG.md](CHANGELOG.md).

## Verification

```bash
python -c "from universe import NIFTY_50; print(len(NIFTY_50))"
```

Expect **50** equity names.
