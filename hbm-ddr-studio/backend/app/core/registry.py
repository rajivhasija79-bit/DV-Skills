"""Loads task & dashboard YAML descriptors from backend/tasks/."""
from __future__ import annotations
from pathlib import Path
import yaml
from .schema import TaskDescriptor, ValidateResult
from ..config import TASKS_DIR


class Registry:
    def __init__(self) -> None:
        self._items: dict[str, TaskDescriptor] = {}
        self.reload()

    def reload(self) -> None:
        items: dict[str, TaskDescriptor] = {}
        for yml in sorted(TASKS_DIR.rglob("*.yaml")):
            try:
                data = yaml.safe_load(yml.read_text()) or {}
                desc = TaskDescriptor(**data)
                if desc.id in items:
                    raise ValueError(f"duplicate task id: {desc.id} ({yml})")
                items[desc.id] = desc
            except Exception as exc:  # noqa: BLE001
                print(f"[registry] skipping {yml}: {exc}")
        self._items = items

    def list(self) -> list[TaskDescriptor]:
        return list(self._items.values())

    def get(self, task_id: str) -> TaskDescriptor | None:
        return self._items.get(task_id)

    def validate(self, task_id: str, config: dict) -> ValidateResult:
        desc = self.get(task_id)
        if not desc:
            return ValidateResult(ok=False, errors=[f"unknown task: {task_id}"])
        missing: list[str] = []
        errors: list[str] = []
        for section in desc.form.sections:
            for f in section.fields:
                v = config.get(f.key)
                empty = v is None or (isinstance(v, str) and v.strip() == "")
                if f.required and empty:
                    missing.append(f.key)
                if not empty and f.type == "number" and not isinstance(v, (int, float)):
                    errors.append(f"{f.key} must be a number")
                if not empty and f.type == "select" and f.options and v not in f.options:
                    errors.append(f"{f.key} must be one of {f.options}")
        return ValidateResult(ok=not missing and not errors, missing=missing, errors=errors)


registry = Registry()
