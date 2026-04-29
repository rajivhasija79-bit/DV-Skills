"""Subprocess runner with streaming logs, mid-run prompts, and pub/sub for WebSocket clients."""
from __future__ import annotations
import asyncio
import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import BACKEND_DIR
from . import run_store
from .registry import registry

# In-memory subscriber queues for each run_id.
# Each subscriber gets its own asyncio.Queue and its own event loop reference,
# so the runner thread can safely schedule put_nowait via call_soon_threadsafe.
_subscribers: dict[str, list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}
_subscribers_lock = threading.Lock()
_processes: dict[str, subprocess.Popen] = {}
_processes_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hds-runner")

PROMPT_MARKER = "##HDS-PROMPT##"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def subscribe(run_id: str) -> tuple[asyncio.Queue, asyncio.AbstractEventLoop]:
    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    with _subscribers_lock:
        _subscribers.setdefault(run_id, []).append((loop, q))
    return q, loop


def unsubscribe(run_id: str, q: asyncio.Queue) -> None:
    with _subscribers_lock:
        subs = _subscribers.get(run_id, [])
        _subscribers[run_id] = [(l, qq) for (l, qq) in subs if qq is not q]


def _publish(run_id: str, event: dict) -> None:
    with _subscribers_lock:
        subs = list(_subscribers.get(run_id, []))
    for loop, q in subs:
        try:
            loop.call_soon_threadsafe(q.put_nowait, event)
        except Exception:  # noqa: BLE001
            pass


def _build_command(script_path: Path, script_type: str) -> list[str]:
    if script_type == "python":
        return ["python3", str(script_path)]
    return ["bash", str(script_path)]


def _read_stream(run_id: str, proc: subprocess.Popen, stream_name: str) -> None:
    stream = proc.stdout if stream_name == "stdout" else proc.stderr
    if stream is None:
        return
    for raw in iter(stream.readline, ""):
        line = raw.rstrip("\n")
        # Detect prompt marker (only on stdout)
        if stream_name == "stdout" and PROMPT_MARKER in line:
            try:
                payload = json.loads(line.split(PROMPT_MARKER, 1)[1].strip())
                run_store.append_prompt(run_id, payload)
                status = run_store.read_status(run_id) or {}
                pending = status.get("pending_prompt_ids", [])
                pending.append(payload["id"])
                run_store.update_status(
                    run_id,
                    state="paused-needs-input",
                    pending_prompt_ids=pending,
                )
                _publish(run_id, {"event": "prompt", "prompt": payload})
                _publish(run_id, {"event": "status", "state": "paused-needs-input"})
                continue
            except Exception as exc:  # noqa: BLE001
                line = f"[runner] failed to parse prompt: {exc}; line={line}"
        run_store.append_log(run_id, stream_name, line)
        _publish(run_id, {"event": "log", "stream": stream_name, "line": line})
    stream.close()


def respond_to_prompt(run_id: str, prompt_id: str, value: Any) -> bool:
    with _processes_lock:
        proc = _processes.get(run_id)
    if not proc or proc.stdin is None:
        return False
    if not run_store.answer_prompt(run_id, prompt_id, value):
        return False
    try:
        proc.stdin.write(json.dumps({"prompt_id": prompt_id, "value": value}) + "\n")
        proc.stdin.flush()
    except Exception as exc:  # noqa: BLE001
        run_store.append_log(run_id, "stderr", f"[runner] stdin write failed: {exc}")
        return False
    status = run_store.read_status(run_id) or {}
    pending = [p for p in status.get("pending_prompt_ids", []) if p != prompt_id]
    new_state = "running" if not pending else "paused-needs-input"
    run_store.update_status(run_id, state=new_state, pending_prompt_ids=pending)
    _publish(run_id, {"event": "status", "state": new_state})
    return True


def cancel_run(run_id: str) -> bool:
    with _processes_lock:
        proc = _processes.get(run_id)
    if not proc:
        return False
    try:
        proc.terminate()
    except Exception:  # noqa: BLE001
        return False
    return True


def _run_subprocess(run_id: str, task_id: str, config: dict) -> None:
    desc = registry.get(task_id)
    if not desc or not desc.script:
        run_store.update_status(run_id, state="failed", ended_at=_now_iso(),
                                exit_code=-1)
        _publish(run_id, {"event": "status", "state": "failed"})
        return

    script_path = (BACKEND_DIR / desc.script.path).resolve()
    if not script_path.exists():
        run_store.append_log(run_id, "stderr", f"[runner] script not found: {script_path}")
        run_store.update_status(run_id, state="failed", ended_at=_now_iso(), exit_code=-1)
        _publish(run_id, {"event": "status", "state": "failed"})
        return

    cmd = _build_command(script_path, desc.script.type)
    env_extra = {}
    if desc.script.arg_mode == "env":
        env_extra = {f"HDS_{k.upper()}": str(v) for k, v in config.items()}
    if desc.script.arg_mode == "argv":
        cmd += [json.dumps(config)]

    run_store.update_status(run_id, state="running")
    _publish(run_id, {"event": "status", "state": "running"})

    try:
        import os
        env = os.environ.copy()
        env.update(env_extra)
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(BACKEND_DIR),
            env=env,
        )
    except Exception as exc:  # noqa: BLE001
        run_store.append_log(run_id, "stderr", f"[runner] launch failed: {exc}")
        run_store.update_status(run_id, state="failed", ended_at=_now_iso(), exit_code=-1)
        _publish(run_id, {"event": "status", "state": "failed"})
        return

    with _processes_lock:
        _processes[run_id] = proc

    if desc.script.arg_mode == "stdin" and proc.stdin is not None:
        try:
            proc.stdin.write(json.dumps(config) + "\n")
            proc.stdin.flush()
        except Exception:  # noqa: BLE001
            pass

    t_out = threading.Thread(target=_read_stream, args=(run_id, proc, "stdout"), daemon=True)
    t_err = threading.Thread(target=_read_stream, args=(run_id, proc, "stderr"), daemon=True)
    t_out.start()
    t_err.start()

    try:
        exit_code = proc.wait(timeout=desc.script.timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        exit_code = proc.wait()
        run_store.append_log(run_id, "stderr", "[runner] killed: timeout")

    t_out.join(timeout=5)
    t_err.join(timeout=5)

    state = "success" if exit_code == 0 else "failed"
    cur = run_store.read_status(run_id) or {}
    if cur.get("state") == "cancelled":
        state = "cancelled"
    run_store.update_status(run_id, state=state, ended_at=_now_iso(), exit_code=exit_code)
    _publish(run_id, {"event": "status", "state": state, "exit_code": exit_code})

    with _processes_lock:
        _processes.pop(run_id, None)


def submit_run(task_id: str, config: dict, source: str = "manual",
               schedule_id: Optional[str] = None) -> str:
    run_id = run_store.init_run(task_id, config, source=source, schedule_id=schedule_id)
    _executor.submit(_run_subprocess, run_id, task_id, config)
    return run_id
