#!/usr/bin/env python3
"""Validate OHLCV for symbols (stdout JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from data_providers import failover_fetch
from data_quality import validate_ohlcv_frame


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", action="append", required=True)
    parser.add_argument("--period", default="2y")
    args = parser.parse_args()
    frames = failover_fetch(args.symbol, args.period)
    report = {}
    for symbol in args.symbol:
        frame = frames.get(symbol)
        report[symbol] = validate_ohlcv_frame(frame, symbol) if frame is not None else ["missing history"]
    print(json.dumps(report, indent=2))
    bad = any(report[s] for s in report)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
