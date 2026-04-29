# HBM-DDR Studio

GUI-based task invoker for the DDR/HBM Subsystem covering RTL, DV, and Program Management workflows.

## Quick start

```bash
# one-time setup
cd backend && python3 -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# run both
./launch.sh
# frontend: http://localhost:5173
# backend:  http://localhost:8000
```

## Adding a new task

Drop a YAML descriptor into `backend/tasks/<rtl|dv|pm>/` and (for runnable tasks) add the script at the path it references. Restart the backend — the task appears in the sidebar with form, run, history, schedules, and status indicators all wired automatically.

```yaml
id: my_new_task
title: My New Task
group: dv                # rtl | dv | pm
icon: zap
description: What it does
script:
  type: python
  path: scripts/dv/my_new_task.py
  arg_mode: stdin        # script reads JSON config from stdin
  timeout_s: 600
schedulable: true
form:
  sections:
    - title: Inputs
      fields:
        - {key: spec_path, type: path, required: true}
        - {key: variant,   type: select, options: [A, B, C], required: true}
```

The script reads JSON config from stdin, prints log lines to stdout, and may emit
`##HDS-PROMPT## {"id":"...","label":"...","type":"text","required":true}` to ask
the user for missing inputs mid-run.

## Layout

- `frontend/` — React + Vite + TypeScript + Tailwind + shadcn/ui
- `backend/` — FastAPI + APScheduler
- `backend/tasks/` — task & dashboard YAML descriptors
- `backend/scripts/` — generator scripts invoked by the runner
- `backend/runs/` — per-run filesystem state (config, logs, status, prompts)

See `/Users/apple/.claude/plans/resilient-humming-moth.md` for the full design.
