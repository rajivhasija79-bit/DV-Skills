"""Live RTL-completion adapter — placeholder stub.

REPLACE: placeholder. Plug in your real RTL-feature-tracking query (e.g. PRD
checklist DB, Jira epics, custom tracker). The returned dict must match
backend/mock_data/rtl_completion.json. On error, return _fallback().
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
from typing import Any

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "rtl_completion.json"
    return json.loads(p.read_text()) if p.exists() else {}


def get_data(_params: dict[str, Any]) -> dict:
    # TODO: replace with real RTL-completion query.
    fb = _fallback()
    fb["_source"] = "mock-fallback (rtl_completion adapter not implemented)"
    return fb
