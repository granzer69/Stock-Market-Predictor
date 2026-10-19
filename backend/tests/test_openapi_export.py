"""OpenAPI export script smoke test."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_openapi_writes_health_route():
    script = REPO_ROOT / "backend/scripts/export_openapi.py"
    # Run with patched output by invoking module logic inline is heavier; run script to repo file then check
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    schema = json.loads((REPO_ROOT / "openapi.json").read_text(encoding="utf-8"))
    assert "/api/health" in schema["paths"]
    get_health = schema["paths"]["/api/health"]["get"]
    assert get_health["responses"]["200"]
