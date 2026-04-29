"""WebSocket: streams log + status + prompt events for a run."""
from __future__ import annotations
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core import runner, run_store

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    status = run_store.read_status(run_id)
    if status:
        await websocket.send_json({"event": "status", "state": status.get("state")})
        for line in run_store.tail_log(run_id, "stdout", 200):
            await websocket.send_json({"event": "log", "stream": "stdout", "line": line})
        for p in run_store.open_prompts(run_id):
            await websocket.send_json({"event": "prompt", "prompt": p})

    q, _loop = runner.subscribe(run_id)
    try:
        while True:
            event = await q.get()
            await websocket.send_json(event)
            if event.get("event") == "status" and event.get("state") in (
                "success", "failed", "cancelled", "interrupted",
            ):
                # let client read final state then close
                await asyncio.sleep(0.1)
                break
    except WebSocketDisconnect:
        pass
    finally:
        runner.unsubscribe(run_id, q)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
