#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${ROOT}/backend/paper_trading.db"
DEST_DIR="${ROOT}/backups"
STAMP="$(date -u +%Y%m%d_%H%M%S)"

if [[ ! -f "$SRC" ]]; then
  echo "No paper DB at $SRC" >&2
  exit 1
fi
mkdir -p "$DEST_DIR"
cp "$SRC" "${DEST_DIR}/paper_trading_${STAMP}.db"
echo "Wrote ${DEST_DIR}/paper_trading_${STAMP}.db"
