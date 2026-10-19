#!/usr/bin/env python3
"""Walk-forward *retrain*: fit on history truncated at an as-of date (manual / heavy).

Uses the same architecture as ``train_lstm.py`` but writes to a separate artifact folder
so the production ``artifacts/`` bundle is untouched unless ``--in-place`` is set.

Environment:

    WF_AS_OF_DATE=2024-06-01 python backend/scripts/walk_forward_retrain.py
    WF_AS_OF_DATE=2024-06-01 WF_OUTPUT=backend/artifacts/wf_2024-06-01 python ...

Requires network for Yahoo unless frames are cached.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from market_data import yfinance_fetcher  # noqa: E402
from train_lstm import train_and_save  # noqa: E402
from universe import NIFTY_50  # noqa: E402


def truncate_frames(frames: dict, as_of: str) -> dict:
    trimmed = {}
    for symbol, frame in frames.items():
        piece = frame[frame["Date"].astype(str) <= as_of]
        if len(piece) >= 140:
            trimmed[symbol] = piece
    return trimmed


def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward retrain with truncated history")
    parser.add_argument(
        "--as-of",
        default=os.environ.get("WF_AS_OF_DATE"),
        help="Inclusive last calendar date in training history (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("WF_OUTPUT"),
        help="Artifact directory (default: backend/artifacts/wf_<date>)",
    )
    parser.add_argument("--in-place", action="store_true", help="Overwrite backend/artifacts")
    parser.add_argument("--period", default="5y", help="Yahoo download period")
    args = parser.parse_args()

    if not args.as_of:
        print("Set --as-of or WF_AS_OF_DATE.", file=sys.stderr)
        return 1

    symbols = [item.symbol for item in NIFTY_50]
    frames = yfinance_fetcher(symbols, args.period)
    frames = truncate_frames(frames, args.as_of)
    if len(frames) < 10:
        print(f"Too few symbols after truncation at {args.as_of}.", file=sys.stderr)
        return 1

    if args.in_place:
        out_dir = BACKEND / "artifacts"
    else:
        out_dir = Path(args.output or BACKEND / "artifacts" / f"wf_{args.as_of}")
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = train_and_save(frames, artifact_dir=out_dir)
    print(f"Wrote {out_dir} — directional accuracy {metrics['directional_accuracy']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
