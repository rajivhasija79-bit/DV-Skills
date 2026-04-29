"""Live Jenkins adapter — phase 2 stub.

Reads:
  HDS_JENKINS_URL   e.g. "https://ci.example.com"
  HDS_JENKINS_USER
  HDS_JENKINS_TOKEN
  HDS_JENKINS_JOB   default job name (e.g. "ddrss-nightly")

Returns regression-trend-style payload. Falls back to mock data on error.
"""
from __future__ import annotations
import base64
import json
import os
from typing import Any
from urllib import request as _req

from ..config import MOCK_DATA_DIR


def _fallback() -> dict:
    p = MOCK_DATA_DIR / "regression_trends.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _auth_header(user: str, token: str) -> str:
    raw = f"{user}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def get_data(params: dict[str, Any]) -> dict:
    base = os.environ.get("HDS_JENKINS_URL")
    user = os.environ.get("HDS_JENKINS_USER")
    token = os.environ.get("HDS_JENKINS_TOKEN")
    job = os.environ.get("HDS_JENKINS_JOB") or params.get("job")
    if not (base and user and token and job):
        return {**_fallback(), "_source": "mock-fallback (env not set)"}

    try:
        url = f"{base}/job/{job}/api/json?tree=builds[number,result,duration,timestamp]"
        r = _req.Request(url, headers={"Authorization": _auth_header(user, token)})
        with _req.urlopen(r, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        builds = data.get("builds", []) or []
        passed = sum(1 for b in builds if b.get("result") == "SUCCESS")
        failed = sum(1 for b in builds if b.get("result") == "FAILURE")
        skipped = sum(1 for b in builds if b.get("result") in ("ABORTED", "UNSTABLE"))
        total = max(1, passed + failed + skipped)
        # Phase-2 stub: only fill the KPIs from live data; weekly/heatmap/etc. mock.
        mock = _fallback()
        mock["_source"] = "live"
        mock.setdefault("kpis", {}).update({
            "pass_rate": int(round(100 * passed / total)),
            "runs_week": total,
        })
        return mock
    except Exception as exc:  # noqa: BLE001
        fb = _fallback()
        fb["_source"] = f"mock-fallback (jenkins error: {exc})"
        return fb
