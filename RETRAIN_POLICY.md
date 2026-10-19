# Model retrain policy

## Production artifacts

Committed defaults live in `backend/artifacts/` (`model.keras`, `scaler.joblib`, `metrics.json`). The running API loads this bundle on startup.

## Walk-forward retrain (manual)

```bash
WF_AS_OF_DATE=2024-06-01 python backend/scripts/walk_forward_retrain.py
```

Writes to `backend/artifacts/wf_<date>/` unless `--in-place` is passed.

**Promotion checklist** (human gate — not automated in CI). Use [RETRAIN_METRICS_DIFF.md](RETRAIN_METRICS_DIFF.md) as the review template.

1. Holdout directional accuracy and MAE documented vs current `metrics.json`
2. `python -m pytest -q` green
3. Spot-check `/api/market/overview` signals on 3 names
4. Replace `backend/artifacts/*` only after review; commit with explicit message

## Scheduled workflow

[`.github/workflows/model-retrain.yml`](.github/workflows/model-retrain.yml) runs on a **monthly schedule** and `workflow_dispatch`. It:

- Trains into a **temporary** directory under `backend/artifacts/ci_retrain_<run_id>/`
- Uploads that folder as a GitHub Actions **artifact** (30-day retention)
- Does **not** push to `main` or overwrite committed artifacts

Download the artifact from the Actions run, evaluate locally, then promote manually if acceptable.

## CI pytest

Pull-request CI does **not** train TensorFlow models (too slow/flaky). API tests use `FakePredictor`.
