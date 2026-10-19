#!/usr/bin/env python3
"""Write FastAPI OpenAPI schema to openapi.json (no server, no Keras load)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
OUTPUT = REPO_ROOT / "openapi.json"


def main() -> int:
    sys.path.insert(0, str(BACKEND))
    from predictor import Predictor

    def _skip_load(self) -> None:
        self.ready = False

    Predictor.load = _skip_load  # type: ignore[method-assign]
    import main as api_main  # noqa: E402

    schema = api_main.app.openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    paths = sorted(schema.get("paths", {}))
    print(f"Wrote {OUTPUT} ({len(paths)} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
