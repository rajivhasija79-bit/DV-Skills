"""Dashboard catalog + data."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException

from ..adapters import dispatch as adapters
from ..core.registry import registry

router = APIRouter(prefix="/api", tags=["dashboards"])


@router.get("/dashboards")
def list_() -> list[dict]:
    return [d.model_dump() for d in registry.list() if d.is_dashboard]


@router.get("/dashboards/{dash_id}")
def get_(dash_id: str) -> dict:
    desc = registry.get(dash_id)
    if not desc or not desc.is_dashboard:
        raise HTTPException(404, "dashboard not found")
    fn = adapters.get(desc.adapter or "")
    if fn is None:
        return {"descriptor": desc.model_dump(), "data": {}}
    return {"descriptor": desc.model_dump(), "data": fn(desc.params)}
