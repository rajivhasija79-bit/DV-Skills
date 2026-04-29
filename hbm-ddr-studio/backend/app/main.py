"""FastAPI app entrypoint for HBM-DDR Studio."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .core import run_store, scheduler
from .routers import tasks, runs, ws, schedules, dashboards, project


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    run_store.reconcile_orphans()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(title="HBM-DDR Studio", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(runs.router)
app.include_router(schedules.router)
app.include_router(dashboards.router)
app.include_router(project.router)
app.include_router(ws.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
