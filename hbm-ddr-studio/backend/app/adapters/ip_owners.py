"""Live IP-owners adapter — placeholder stub.

REPLACE: placeholder. Plug in your real IP-ownership query (e.g. LDAP, Confluence
table, internal tracker). The returned dict must match
backend/mock_data/ip_owners.json. On error, return _fallback().
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
from typing import Any

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "ip_owners.json"
    return json.loads(p.read_text()) if p.exists() else {}


def get_data(_params: dict[str, Any]) -> dict:
    # TODO: replace with real ownership query.
    fb = _fallback()
    fb["_source"] = "mock-fallback (ip_owners adapter not implemented)"
    return fb
