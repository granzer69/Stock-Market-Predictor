# Retrain metrics diff template

Use when promoting artifacts from `walk_forward_retrain.py` or CI artifact `lstm-wf-retrain-*`.

## Compare

| Metric | Current `artifacts/metrics.json` | Candidate |
|--------|-------------------------------|-----------|
| `directional_accuracy` | | |
| `mae_log_return` | | |
| `naive_mae_log_return` | | |
| `train_rows` | | |
| `trained_at` | | |

## Per-symbol (optional)

List symbols where candidate `directional_accuracy` improves by > 2pp vs current `per_symbol` entry.

## Decision

- [ ] Promote to `backend/artifacts/` (human review per [RETRAIN_POLICY.md](RETRAIN_POLICY.md))
- [ ] Reject — keep current bundle

## Commands

```bash
jq '.directional_accuracy, .mae_log_return' backend/artifacts/metrics.json
jq '.directional_accuracy, .mae_log_return' backend/artifacts/wf_DATE/metrics.json
```
