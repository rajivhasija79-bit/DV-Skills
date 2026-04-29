"""Live JIRA REST adapter — phase 2 stub.

Reads:
  HDS_JIRA_URL    e.g. "https://issues.example.com"
  HDS_JIRA_TOKEN  bearer token
  HDS_JIRA_PROJECT  project key (e.g. "DDRSS")

Returns the same shape as backend/mock_data/jira.json so the frontend doesn't
care which backend is in play. Falls back to mock data on any error so the UI
never sees a hole.
"""
from __future__ import annotations
import json
import os
from typing import Any
from urllib import request as _req
from urllib.parse import urlencode

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "jira.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _get(url: str, token: str) -> dict:
    r = _req.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    with _req.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_data(params: dict[str, Any]) -> dict:
    base = os.environ.get("HDS_JIRA_URL")
    token = os.environ.get("HDS_JIRA_TOKEN")
    project = os.environ.get("HDS_JIRA_PROJECT") or params.get("project")
    if not (base and token and project):
        return {**_fallback(), "_source": "mock-fallback (env not set)"}

    try:
        # Open count
        q_open = urlencode({"jql": f'project={project} AND statusCategory != Done', "maxResults": 0})
        open_count = _get(f"{base}/rest/api/2/search?{q_open}", token).get("total", 0)
        # Created this week
        q_created = urlencode({"jql": f'project={project} AND created >= -7d', "maxResults": 0})
        created_week = _get(f"{base}/rest/api/2/search?{q_created}", token).get("total", 0)
        # Resolved this week
        q_resolved = urlencode({"jql": f'project={project} AND resolved >= -7d', "maxResults": 0})
        resolved_week = _get(f"{base}/rest/api/2/search?{q_resolved}", token).get("total", 0)
        # Blockers
        q_block = urlencode({"jql": f'project={project} AND priority = Blocker AND statusCategory != Done', "maxResults": 0})
        blockers = _get(f"{base}/rest/api/2/search?{q_block}", token).get("total", 0)

        # The historical trend / severity / stale tables would be more queries —
        # phase-2 stub just fills KPIs and falls back to mock for the rest.
        mock = _fallback()
        mock["_source"] = "live"
        mock.setdefault("kpis", {}).update({
            "open_count": open_count, "created_week": created_week,
            "resolved_week": resolved_week, "blockers": blockers,
        })
        return mock
    except Exception as exc:  # noqa: BLE001
        fb = _fallback()
        fb["_source"] = f"mock-fallback (jira error: {exc})"
        return fb
