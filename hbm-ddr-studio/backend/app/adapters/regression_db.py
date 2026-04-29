"""Live regression-DB adapter — phase 2 stub.

Reads HDS_REGRESSION_DB pointing to a JSON file (or sqlite/csv in a real impl)
that holds per-run results. The file format is intentionally identical to
backend/mock_data/regression_trends.json so the same rendering pipeline works.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "regression_trends.json"
    return json.loads(p.read_text()) if p.exists() else {}


def get_data(_params: dict[str, Any]) -> dict:
    src = os.environ.get("HDS_REGRESSION_DB")
    if not src:
        return {**_fallback(), "_source": "mock-fallback (HDS_REGRESSION_DB unset)"}
    p = Path(src)
    if not p.exists():
        return {**_fallback(), "_source": f"mock-fallback (file not found: {src})"}
    try:
        data = json.loads(p.read_text())
        data["_source"] = "live"
        return data
    except Exception as exc:  # noqa: BLE001
        fb = _fallback()
        fb["_source"] = f"mock-fallback (parse error: {exc})"
        return fb
