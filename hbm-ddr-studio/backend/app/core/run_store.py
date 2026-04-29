"""Filesystem-backed run state. Source of truth for runs/<id>/."""
from __future__ import annotations
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import RUNS_DIR


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id(task_id: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return f"{task_id}_{ts}_{uuid.uuid4().hex[:6]}"


def run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def init_run(task_id: str, config: dict, source: str = "manual",
             schedule_id: Optional[str] = None) -> str:
    run_id = new_run_id(task_id)
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps(config, indent=2))
    (d / "stdout.log").touch()
    (d / "stderr.log").touch()
    (d / "prompts.json").write_text("[]")
    write_status(run_id, {
        "run_id": run_id,
        "task_id": task_id,
        "state": "queued",
        "started_at": _now_iso(),
        "ended_at": None,
        "exit_code": None,
        "source": source,
        "schedule_id": schedule_id,
        "pending_prompt_ids": [],
    })
    return run_id


def write_status(run_id: str, status: dict) -> None:
    (run_dir(run_id) / "status.json").write_text(json.dumps(status, indent=2))


def read_status(run_id: str) -> dict | None:
    p = run_dir(run_id) / "status.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def update_status(run_id: str, **fields: Any) -> dict:
    status = read_status(run_id) or {}
    status.update(fields)
    write_status(run_id, status)
    return status


def append_log(run_id: str, stream: str, line: str) -> None:
    fname = "stdout.log" if stream == "stdout" else "stderr.log"
    with (run_dir(run_id) / fname).open("a") as f:
        f.write(line if line.endswith("\n") else line + "\n")


def tail_log(run_id: str, stream: str = "stdout", n: int = 200) -> list[str]:
    fname = "stdout.log" if stream == "stdout" else "stderr.log"
    p = run_dir(run_id) / fname
    if not p.exists():
        return []
    lines = p.read_text().splitlines()
    return lines[-n:]


def list_runs(task_id: Optional[str] = None, status_filter: Optional[str] = None,
              limit: int = 200) -> list[dict]:
    out = []
    if not RUNS_DIR.exists():
        return out
    dirs = sorted(RUNS_DIR.iterdir(), key=lambda d: d.name, reverse=True)
    for d in dirs:
        if not d.is_dir():
            continue
        s = read_status(d.name)
        if not s:
            continue
        if task_id and s.get("task_id") != task_id:
            continue
        if status_filter and s.get("state") != status_filter:
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def reconcile_orphans() -> None:
    """Mark any run still 'running' on boot as 'interrupted'."""
    for d in RUNS_DIR.iterdir() if RUNS_DIR.exists() else []:
        if not d.is_dir():
            continue
        s = read_status(d.name)
        if s and s.get("state") in ("queued", "running", "paused-needs-input"):
            s["state"] = "interrupted"
            s["ended_at"] = _now_iso()
            write_status(d.name, s)


def append_prompt(run_id: str, prompt: dict) -> None:
    p = run_dir(run_id) / "prompts.json"
    arr = json.loads(p.read_text() or "[]")
    arr.append({"prompt": prompt, "answered_at": None, "response": None})
    p.write_text(json.dumps(arr, indent=2))


def answer_prompt(run_id: str, prompt_id: str, value: Any) -> bool:
    p = run_dir(run_id) / "prompts.json"
    arr = json.loads(p.read_text() or "[]")
    for entry in arr:
        if entry["prompt"]["id"] == prompt_id and entry["answered_at"] is None:
            entry["answered_at"] = _now_iso()
            entry["response"] = value
            p.write_text(json.dumps(arr, indent=2))
            return True
    return False


def open_prompts(run_id: str) -> list[dict]:
    p = run_dir(run_id) / "prompts.json"
    if not p.exists():
        return []
    arr = json.loads(p.read_text() or "[]")
    return [e["prompt"] for e in arr if e["answered_at"] is None]
