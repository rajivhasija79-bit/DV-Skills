"""Pydantic models for task & dashboard descriptors and runs."""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class FormField(BaseModel):
    key: str
    type: Literal[
        "text", "number", "select", "multiselect", "boolean",
        "textarea", "password", "path", "file",
    ]
    label: Optional[str] = None
    options: Optional[list[str]] = None
    required: bool = False
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    placeholder: Optional[str] = None
    help: Optional[str] = None


class FormSection(BaseModel):
    title: str
    fields: list[FormField]


class FormSpec(BaseModel):
    sections: list[FormSection] = Field(default_factory=list)


class ScriptSpec(BaseModel):
    type: Literal["python", "shell"] = "python"
    path: str
    arg_mode: Literal["stdin", "argv", "env"] = "stdin"
    timeout_s: int = 600


class PostRunSpec(BaseModel):
    collect_artifacts: list[str] = Field(default_factory=list)


class TaskDescriptor(BaseModel):
    id: str
    title: str
    group: Literal["rtl", "dv", "pm"]
    icon: Optional[str] = None
    description: Optional[str] = None
    schedulable: bool = True
    script: Optional[ScriptSpec] = None        # tasks (rtl/dv) have scripts
    form: FormSpec = Field(default_factory=FormSpec)
    post_run: PostRunSpec = Field(default_factory=PostRunSpec)
    # Dashboard-only fields:
    adapter: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    layout: list[dict[str, Any]] = Field(default_factory=list)
    refresh_s: int = 300

    @property
    def is_dashboard(self) -> bool:
        return self.group == "pm"


class ScheduleWhen(BaseModel):
    kind: Literal["once", "cron"]
    at: Optional[str] = None       # ISO 8601 with offset, when kind=once
    cron: Optional[str] = None     # 5-field cron, when kind=cron
    tz: Optional[str] = None


class ScheduleCreate(BaseModel):
    config: dict[str, Any]
    when: ScheduleWhen


class ValidateResult(BaseModel):
    ok: bool
    missing: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PromptSpec(BaseModel):
    """Mid-run prompt emitted by a script via ##HDS-PROMPT##."""
    id: str
    label: str
    type: Literal["text", "password", "select", "boolean", "number"] = "text"
    options: Optional[list[str]] = None
    required: bool = True


class PromptResponse(BaseModel):
    prompt_id: str
    value: Any
