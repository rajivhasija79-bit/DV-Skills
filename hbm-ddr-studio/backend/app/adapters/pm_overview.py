"""Live PM-overview adapter — placeholder stub.

REPLACE: placeholder. Plug in your real PM-rollup query here. The returned
dict must match the shape of backend/mock_data/pm_overview.json (KPIs, RAG,
trends, blockers table, ...). On any error, return _fallback() so the
dashboard degrades to mock data instead of breaking.
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
from typing import Any

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "pm_overview.json"
    return json.loads(p.read_text()) if p.exists() else {}


def get_data(_params: dict[str, Any]) -> dict:
    # TODO: replace with real rollup query (Jira + regression DB + schedule).
    # For now: just return mock so the dashboard renders.
    fb = _fallback()
    fb["_source"] = "mock-fallback (pm_overview adapter not implemented)"
    return fb
