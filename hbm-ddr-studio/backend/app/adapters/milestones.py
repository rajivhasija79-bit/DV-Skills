"""Live milestones adapter — placeholder stub.

REPLACE: placeholder. Plug in your real schedule/milestone query (MS Project,
Smartsheet, internal scheduler, ...). The returned dict must match
backend/mock_data/milestones.json. On error, return _fallback().
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
from typing import Any

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "milestones.json"
    return json.loads(p.read_text()) if p.exists() else {}


def get_data(_params: dict[str, Any]) -> dict:
    # TODO: replace with real schedule query.
    fb = _fallback()
    fb["_source"] = "mock-fallback (milestones adapter not implemented)"
    return fb
