"""JIRA adapter — mock impl reads mock_data/jira_bugs.json. Live impl lands in phase 2."""
from __future__ import annotations
import json
from typing import Any
from ..config import DATA_MODE, MOCK_DATA_DIR


def get_data(params: dict[str, Any]) -> dict:
    if DATA_MODE == "mock":
        path = MOCK_DATA_DIR / "jira_bugs.json"
        if path.exists():
            return json.loads(path.read_text())
    return _empty()


def _empty() -> dict:
    return {
        "kpis": {
            "open_count": 0, "open_delta": 0,
            "created_week": 0, "created_delta": 0,
            "resolved_week": 0, "resolved_delta": 0,
            "blockers": 0, "blockers_delta": 0,
            "sla_breaches": 0, "sla_delta": 0,
            "mttr_days": 0, "mttr_delta": 0,
        },
        "trend": [],
        "severity": [],
        "stale": [],
    }
