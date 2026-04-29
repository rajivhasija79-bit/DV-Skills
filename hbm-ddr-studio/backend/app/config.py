"""Runtime config: paths and mode flags."""
from __future__ import annotations
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = BACKEND_DIR / "tasks"
SCRIPTS_DIR = BACKEND_DIR / "scripts"
RUNS_DIR = BACKEND_DIR / "runs"
SCHEDULER_DIR = BACKEND_DIR / "scheduler"
MOCK_DATA_DIR = BACKEND_DIR / "mock_data"

# mock | live — selects adapter implementations for dashboards
DATA_MODE = os.environ.get("HDS_DATA_MODE", "mock")

# CORS origins for the Vite dev server
CORS_ORIGINS = os.environ.get(
    "HDS_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

RUNS_DIR.mkdir(parents=True, exist_ok=True)
SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)
