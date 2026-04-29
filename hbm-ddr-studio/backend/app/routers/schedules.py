"""Schedule list/edit/delete."""
from __future__ import annotations
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import scheduler

router = APIRouter(prefix="/api", tags=["schedules"])


class PatchBody(BaseModel):
    enabled: Optional[bool] = None


@router.get("/schedules")
def list_(task_id: Optional[str] = None) -> list[dict]:
    return scheduler.list_schedules(task_id=task_id)


@router.get("/schedules/{sid}")
def get_(sid: str) -> dict:
    s = scheduler.get(sid)
    if not s:
        raise HTTPException(404, "schedule not found")
    return s


@router.patch("/schedules/{sid}")
def patch_(sid: str, body: PatchBody) -> dict:
    if body.enabled is not None:
        if not scheduler.set_enabled(sid, body.enabled):
            raise HTTPException(404, "schedule not found")
    return scheduler.get(sid) or {"id": sid}


@router.delete("/schedules/{sid}")
def delete_(sid: str) -> dict:
    if not scheduler.remove(sid):
        raise HTTPException(404, "schedule not found")
    return {"ok": True}
