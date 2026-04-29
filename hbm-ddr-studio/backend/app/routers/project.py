"""Project-level config: paths, git, env vars, tools, documents.

Persists to backend/project_config.json. Used by every task script via the
`project_config` field that's automatically merged into the run config.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter

from ..config import BACKEND_DIR

router = APIRouter(prefix="/api", tags=["project"])

PROJECT_FILE = BACKEND_DIR / "project_config.json"

DEFAULT: dict[str, Any] = {
    "name": "",
    "subsystem": "DDR5",
    "paths": {
        "rtl": "",
        "dv": "",
        "docs": "",
        "scripts": "",
        "output": "",
    },
    "git": {
        "url": "",
        "branch": "main",
        "commit": "",
    },
    "env_vars": [],          # [{key, value}]
    "tools": [],             # [{name, path, version}]
    "documents": [],         # [{label, path}]
}


def _read() -> dict:
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text())
        except Exception:
            pass
    return DEFAULT.copy()


@router.get("/project-config")
def get_project_config() -> dict:
    return _read()


@router.put("/project-config")
def put_project_config(body: dict) -> dict:
    # No schema enforcement here — we accept whatever fields the UI sends so
    # the descriptor stays flexible (UI is the source of truth for shape).
    PROJECT_FILE.write_text(json.dumps(body, indent=2))
    return {"ok": True, "saved": body}
