"""Task catalog, validate, run, schedule endpoints."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.registry import registry
from ..core.schema import ScheduleCreate
from ..core import runner, scheduler

router = APIRouter(prefix="/api", tags=["tasks"])


class RunBody(BaseModel):
    config: dict[str, Any]


@router.get("/tasks")
def list_tasks() -> list[dict]:
    return [d.model_dump() for d in registry.list()]


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    desc = registry.get(task_id)
    if not desc:
        raise HTTPException(404, f"unknown task: {task_id}")
    return desc.model_dump()


@router.post("/tasks/{task_id}/validate")
def validate_task(task_id: str, body: RunBody) -> dict:
    res = registry.validate(task_id, body.config)
    return res.model_dump()


@router.post("/tasks/{task_id}/run")
def run_task(task_id: str, body: RunBody) -> dict:
    desc = registry.get(task_id)
    if not desc:
        raise HTTPException(404, f"unknown task: {task_id}")
    if desc.is_dashboard:
        raise HTTPException(400, f"{task_id} is a dashboard, not runnable")
    res = registry.validate(task_id, body.config)
    if not res.ok:
        raise HTTPException(422, detail={"missing": res.missing, "errors": res.errors})
    run_id = runner.submit_run(task_id, body.config)
    return {"run_id": run_id}


@router.post("/tasks/{task_id}/schedule")
def schedule_task(task_id: str, body: ScheduleCreate) -> dict:
    desc = registry.get(task_id)
    if not desc:
        raise HTTPException(404, f"unknown task: {task_id}")
    if not desc.schedulable:
        raise HTTPException(400, f"{task_id} is not schedulable")
    res = registry.validate(task_id, body.config)
    if not res.ok:
        raise HTTPException(422, detail={"missing": res.missing, "errors": res.errors})
    try:
        sid = scheduler.add(task_id, body.config, body.when.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"schedule failed: {exc}") from exc
    return scheduler.get(sid) or {"id": sid}


@router.post("/registry/reload")
def reload_registry() -> dict:
    registry.reload()
    return {"count": len(registry.list())}
