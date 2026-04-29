"""APScheduler with SQLite jobstore. Fires runs via runner.submit_run."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from ..config import SCHEDULER_DIR
from . import runner


_jobstore_url = f"sqlite:///{SCHEDULER_DIR / 'jobs.sqlite'}"
_scheduler = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=_jobstore_url)})


def start() -> None:
    if not _scheduler.running:
        _scheduler.start()


def stop() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def _fire(task_id: str, config_json: str, schedule_id: str) -> None:
    config = json.loads(config_json)
    runner.submit_run(task_id, config, source="schedule", schedule_id=schedule_id)


def add(task_id: str, config: dict, when: dict) -> str:
    schedule_id = f"sch_{uuid.uuid4().hex[:8]}"
    kind = when.get("kind")
    tz = when.get("tz")
    if kind == "once":
        trigger = DateTrigger(run_date=when["at"], timezone=tz)
    elif kind == "cron":
        trigger = CronTrigger.from_crontab(when["cron"], timezone=tz)
    else:
        raise ValueError(f"unknown when.kind: {kind}")
    _scheduler.add_job(
        _fire,
        trigger=trigger,
        args=[task_id, json.dumps(config), schedule_id],
        id=schedule_id,
        name=f"{task_id}:{kind}",
        replace_existing=True,
        misfire_grace_time=300,
    )
    return schedule_id


def list_schedules(task_id: Optional[str] = None) -> list[dict]:
    out = []
    for job in _scheduler.get_jobs():
        meta = _job_meta(job)
        if task_id and meta["task_id"] != task_id:
            continue
        out.append(meta)
    return out


def get(schedule_id: str) -> Optional[dict]:
    job = _scheduler.get_job(schedule_id)
    return _job_meta(job) if job else None


def remove(schedule_id: str) -> bool:
    try:
        _scheduler.remove_job(schedule_id)
        return True
    except Exception:  # noqa: BLE001
        return False


def set_enabled(schedule_id: str, enabled: bool) -> bool:
    job = _scheduler.get_job(schedule_id)
    if not job:
        return False
    if enabled:
        job.resume()
    else:
        job.pause()
    return True


def _job_meta(job: Any) -> dict:
    args = job.args or []
    task_id = args[0] if len(args) > 0 else "?"
    config = json.loads(args[1]) if len(args) > 1 else {}
    next_run = job.next_run_time.isoformat() if job.next_run_time else None
    trigger = job.trigger
    when: dict[str, Any] = {}
    if isinstance(trigger, DateTrigger):
        when = {"kind": "once", "at": trigger.run_date.isoformat()}
    elif isinstance(trigger, CronTrigger):
        when = {"kind": "cron", "cron": str(trigger)}
    return {
        "id": job.id,
        "task_id": task_id,
        "config": config,
        "when": when,
        "next_run_at": next_run,
        "enabled": job.next_run_time is not None,
        "name": job.name,
    }
