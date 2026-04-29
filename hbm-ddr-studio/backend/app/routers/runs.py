"""Run inspection, prompt response, cancel, delete."""
from __future__ import annotations
import shutil
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import run_store, runner

router = APIRouter(prefix="/api", tags=["runs"])


class RespondBody(BaseModel):
    prompt_id: str
    value: Any


@router.get("/runs")
def list_runs(task_id: Optional[str] = None, status: Optional[str] = None,
              limit: int = 200) -> list[dict]:
    return run_store.list_runs(task_id=task_id, status_filter=status, limit=limit)


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    s = run_store.read_status(run_id)
    if not s:
        raise HTTPException(404, "run not found")
    return {
        **s,
        "stdout_tail": run_store.tail_log(run_id, "stdout", 200),
        "stderr_tail": run_store.tail_log(run_id, "stderr", 50),
        "open_prompts": run_store.open_prompts(run_id),
    }


@router.post("/runs/{run_id}/respond")
def respond(run_id: str, body: RespondBody) -> dict:
    ok = runner.respond_to_prompt(run_id, body.prompt_id, body.value)
    if not ok:
        raise HTTPException(400, "no matching open prompt or process gone")
    return {"ok": True}


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: str) -> dict:
    if not runner.cancel_run(run_id):
        raise HTTPException(404, "no live process for run")
    run_store.update_status(run_id, state="cancelled")
    return {"ok": True}


@router.delete("/runs/{run_id}")
def delete_run(run_id: str) -> dict:
    d = run_store.run_dir(run_id)
    if not d.exists():
        raise HTTPException(404, "run not found")
    shutil.rmtree(d)
    return {"ok": True}
