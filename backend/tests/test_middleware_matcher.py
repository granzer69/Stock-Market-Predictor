"""The Next middleware matcher must not rewrite the Evaluation or Backtest documents.

Playwright starts without API_ORIGIN, so a matcher regression would not fail e2e.
"""

from __future__ import annotations

import re
from pathlib import Path

MIDDLEWARE = Path(__file__).resolve().parents[2] / "frontend" / "middleware.ts"


def _matcher_source() -> str:
    text = MIDDLEWARE.read_text(encoding="utf-8")
    without_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    without_comments = re.sub(r"//.*?$", "", without_comments, flags=re.M)
    match = re.search(r"matcher\s*:\s*\[(.*?)\]", without_comments, flags=re.S)
    assert match, "frontend/middleware.ts has no matcher array"
    return match.group(1)


def test_middleware_matcher_leaves_page_documents_on_next():
    body = _matcher_source()
    assert "/api/:path*" in body
    assert "/evaluation" not in body
    assert "/backtest" not in body
