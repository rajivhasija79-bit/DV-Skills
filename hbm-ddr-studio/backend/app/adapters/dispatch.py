"""Adapter dispatch.

Resolves a dashboard descriptor's `adapter` field to a callable that returns
a JSON-serialisable dict. In mock mode (default) we just look up
backend/mock_data/<adapter>.json.

To swap in a real adapter (Jira REST, Jenkins, regression DB, ...) set
HDS_DATA_MODE=live and register the adapter here.
"""
from __future__ import annotations
import json
from typing import Any, Callable

from ..config import DATA_MODE, MOCK_DATA_DIR
from . import (
    jira_rest,
    jenkins,
    regression_db,
    pm_overview,
    ip_owners,
    milestones,
    rtl_completion,
)


def _mock_loader(name: str) -> Callable[[dict[str, Any]], dict]:
    def _read(_params: dict[str, Any]) -> dict:
        path = MOCK_DATA_DIR / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}
    return _read


# Live adapters registered here. They each fall back to mock if env unset
# or if the upstream call fails, so the UI never breaks.
_LIVE: dict[str, Callable[[dict[str, Any]], dict]] = {
    "jira": jira_rest.get_data,
    "regression_trends": regression_db.get_data,
    "jenkins": jenkins.get_data,
    # Placeholder stubs — implement get_data() in each module to go live.
    "pm_overview": pm_overview.get_data,
    "ip_owners": ip_owners.get_data,
    "milestones": milestones.get_data,
    "rtl_completion": rtl_completion.get_data,
}


def get(name: str) -> Callable[[dict[str, Any]], dict] | None:
    if not name:
        return None
    if DATA_MODE == "live" and name in _LIVE:
        return _LIVE[name]
    return _mock_loader(name)
