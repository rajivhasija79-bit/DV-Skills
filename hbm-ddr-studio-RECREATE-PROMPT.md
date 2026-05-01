# Recreate HBM-DDR Studio — single-prompt spec

Paste everything below the `---` line into a fresh Claude Code (or Claude
Agent SDK) session inside your organization, pointing the agent at an empty
working directory. It should produce a runnable app equivalent to the public
hbm-ddr-studio in this repo.

The spec is intentionally exhaustive. Trim sections you don't need before
pasting (e.g. drop the PM Central section if you only need RTL/DV).

---

# Build "HBM-DDR Studio" — a memory-subsystem cockpit web app

## Goal

A single web app that lets verification & program-management users kick off
RTL / DV tasks via forms (with live log streaming and scheduling) and view
PM dashboards (mock data by default, swappable to live adapters). Every
"task" is described by a YAML file; the backend runs a script on demand and
streams output to the browser over a WebSocket. Every "dashboard" is also a
YAML file that names an adapter; the adapter returns JSON the frontend
renders into KPI tiles, charts, RAG strips, tables, etc.

The app should run unchanged on macOS and Linux with no sudo, only Python
3.9+ and Node 18+.

## Tech stack (use these versions or newer)

- **Backend**: Python 3.9+, FastAPI ≥ 0.110, uvicorn[standard] ≥ 0.27,
  pydantic ≥ 2.6, pyyaml ≥ 6.0, websockets ≥ 12.0, python-multipart,
  apscheduler ≥ 3.10, sqlalchemy ≥ 2.0
- **Frontend**: Vite 5, React 18, TypeScript 5, Tailwind CSS 3 +
  tailwindcss-animate, Radix UI primitives (accordion / dialog /
  dropdown-menu / popover / progress / scroll-area / select / separator /
  slot / switch / tabs / tooltip / label), lucide-react icons, recharts,
  react-router-dom v6, react-hook-form, zod, reactflow ≥ 11
- **Bash launcher** (`launch.sh`) starts both servers.

## Directory layout (create exactly this)

```
hbm-ddr-studio/
  README.md
  launch.sh
  .gitignore                        # exclude .venv, node_modules, runs/, jobstore, *.pyc, .DS_Store, tsc-emitted .js next to .tsx
  docs/
    INTEGRATION.md                  # see "Integration guide" section below
  backend/
    requirements.txt
    app/
      __init__.py
      main.py                       # FastAPI entrypoint + CORS + lifespan
      config.py                     # paths, DATA_MODE, CORS_ORIGINS from env
      core/
        __init__.py
        registry.py                 # loads YAMLs from tasks/ into pydantic models
        schema.py                   # pydantic models for tasks, forms, dashboards
        runner.py                   # subprocess runner with stdin/argv/env modes,
                                    # stdout/stderr stream → WebSocket, mid-run prompts
        run_store.py                # SQLite (or jsonl) persistence for runs
        scheduler.py                # APScheduler wrapper (cron + interval)
      adapters/
        __init__.py
        dispatch.py                 # mock → backend/mock_data/<name>.json,
                                    # live → registered adapters
        jira_rest.py                # uses HDS_JIRA_BASE/_TOKEN/_PROJECT, fallback to mock
        jenkins.py                  # uses HDS_JENKINS_URL/_USER/_TOKEN/_JOB, fallback to mock
        regression_db.py            # reads HDS_REGRESSION_DB (local file)
        pm_overview.py              # placeholder stub returning _fallback()
        ip_owners.py                # placeholder stub
        milestones.py               # placeholder stub
        rtl_completion.py           # placeholder stub
      routers/
        __init__.py
        tasks.py                    # GET /api/tasks, GET /api/tasks/{id}
        runs.py                     # POST /api/runs, GET /api/runs, GET /api/runs/{id}, etc.
        ws.py                       # WS /ws/runs/{id} — streams status / log / prompt
        schedules.py                # CRUD over scheduler jobs
        dashboards.py               # GET /api/dashboards, GET /api/dashboards/{id}
        project.py                  # project config (TB root path, IP scan, persistence)
    tasks/
      rtl/
        review.yaml
        sdc_gen.yaml
        subsystem_integration.yaml
      dv/
        coverage_model.yaml
        debug.yaml
        ral_gen.yaml
        regression_run.yaml
        test_strategy.yaml
        testbench_create.yaml
        testplan_gen.yaml
        vip_integration.yaml
      pm/
        pm_overview.yaml
        ip_owners.yaml
        jira_trends.yaml
        milestones.yaml
        regression_trends.yaml
        rtl_completion.yaml
    scripts/
      common/
      rtl/
        review.py
        sdc_gen.py
        integrate_subsystem.py
      dv/
        coverage_model.py
        debug.py
        ral_gen.py
        regression_run.py
        test_strategy.py
        testbench_create.py
        testplan_gen.py
        vip_integration.py
    mock_data/
      pm_overview.json
      ip_owners.json
      milestones.json
      jira.json
      jira_bugs.json
      regression_trends.json
      rtl_completion.json
  frontend/
    index.html
    package.json
    vite.config.ts
    tsconfig.json
    tailwind.config.ts
    postcss.config.js
    src/
      main.tsx
      App.tsx
      styles/globals.css
      lib/
        api.ts                      # typed REST client
        ws.ts                       # WebSocket helper for /ws/runs/<id>
        theme.ts
        utils.ts                    # cn(), etc.
      components/
        ui/                         # shadcn-style wrappers around Radix:
                                    # accordion, badge, button, card, dialog,
                                    # dropdown-menu, input, label, progress,
                                    # scroll-area, select, separator, sheet,
                                    # switch, tabs, tooltip
        layout/
          AppShell.tsx              # sidebar + topbar + outlet
          AppSidebar.tsx            # collapsible groups: RTL / DV / PM
          Topbar.tsx                # search, run-history, settings, theme
          ThemeToggle.tsx
          RunHistoryDrawer.tsx
        task/
          TaskPage.tsx              # generic per-task page (form + run pane + history + schedules)
          SchemaForm.tsx            # renders form from YAML schema using react-hook-form + zod
          RunPane.tsx               # live log stream + status + mid-run prompts
          RunHistory.tsx            # past runs list w/ status badges
          ScheduleDialog.tsx
          SchedulesTab.tsx
          StatusBadge.tsx
        diagrams/
          DiagramSubsystem.tsx      # static isometric diagram (theme-token aware)
          DiagramBuilder.tsx        # reactflow canvas: drag palette → boxes → edges → Apply to Form
        charts/
          Sparkline.tsx
      pages/
        Home.tsx                    # landing page with the three track cards
        GroupPage.tsx               # /rtl, /dv, /pm — list of tasks/dashboards in that group
        ProjectConfigPage.tsx       # TB root path, scan IPs, persist to backend/project.json
        SubsystemIntegrationPage.tsx# tabs: Form / Diagram Builder
        DashboardPage.tsx           # generic per-dashboard renderer driven by YAML layout
```

## Backend contracts

### Task YAML (RTL / DV) example shape

```yaml
id: rtl_review
title: RTL Review
group: rtl
icon: book-open                    # lucide-react icon name
description: Compare RTL against PRD/spec checklist
schedulable: false
script:
  type: python                     # or "bash"
  path: scripts/rtl/review.py
  arg_mode: stdin                  # or "argv" | "env"
  timeout_s: 600
form:
  sections:
    - title: Sources
      fields:
        - {key: spec_path, type: path, required: true, placeholder: "./docs/PRD.md"}
        - {key: rtl_path,  type: path, required: true, placeholder: "./rtl"}
    - title: Focus
      fields:
        - {key: focus, type: multiselect,
           options: [Functional, Lint, CDC, Power, Synthesis]}
        - {key: severity_threshold, type: select,
           options: [Info, Warning, Error], default: Warning, required: true}
    - title: Output
      fields:
        - {key: output_dir, type: path, required: true, placeholder: "./review"}
post_run:
  collect_artifacts: ["review_report.md", "issues.json"]
```

Supported `field.type`: `text | number | select | multiselect | boolean | textarea | password | path | file`.

### Script contract

- **stdin**: one JSON line containing all form fields (when `arg_mode: stdin`).
- **stdout**: free-text progress lines; each line is streamed to the UI live.
- **stderr**: ignored in UI but kept in run log on disk.
- **exit**: 0 = success, non-zero = failed.
- **mid-run prompt**: print `##HDS-PROMPT## {"id":"...","label":"...","type":"password|text|bool","required":true}` and read the next stdin line as JSON answer.

The runner builds the command as a `list` and calls `subprocess.Popen` **without `shell=True`**. Form input must never be spliced into a shell line.

### Dashboard YAML (PM) example

```yaml
id: pm_overview
title: PM Overview
group: pm
icon: pie-chart
adapter: pm_overview               # resolved via dispatch.py
params: {}
refresh_s: 300
layout:
  - {kind: kpi_row, tiles: [...]}
  - {kind: rag,   title: "...", source: rag}
  - {kind: line,  title: "...", source: dv_trend, x: week, series: [...]}
  - {kind: bar,   title: "...", source: jira_trend, x: week, series: [...]}
  - {kind: donut, title: "...", source: bugs_area, name: area, value: count}
  - {kind: feed,  title: "...", source: feed}
  - {kind: table, title: "...", source: blockers, columns: [...]}
```

### Adapter contract

```python
def get_data(params: dict) -> dict: ...
```

`dispatch.get(name)`:
- if `HDS_DATA_MODE == "live"` and `name` is registered in `_LIVE`, return that callable
- otherwise return a loader that reads `backend/mock_data/<name>.json`

Each live adapter must define `_fallback()` that reads the matching mock JSON and return it when env is missing or upstream errors out — the UI never breaks.

### Other backend rules

- `yaml.safe_load` only (never `yaml.load`).
- CORS default: `http://localhost:5173,http://127.0.0.1:5173`, overridable via `HDS_CORS_ORIGINS`.
- uvicorn binds to `127.0.0.1:8000` by default. No auth layer — explicitly document that it's loopback-only and require SSO/proxy for any other binding.
- `runs/` and `jobstore.sqlite` are runtime state; create on first start, exclude from git.
- Generate sample mock data with at least 12 weeks of trend points, ~10 blockers, sensible KPIs.

## Frontend specifics

### Routing (React Router v6)

```
/                                   → Home
/config                             → ProjectConfigPage
/rtl                                → GroupPage(group="rtl")
/dv                                 → GroupPage(group="dv")
/pm                                 → GroupPage(group="pm")
/rtl/rtl_subsystem_integration      → SubsystemIntegrationPage  (bespoke, has Diagram Builder)
/rtl/:taskId                        → TaskPage
/dv/:taskId                         → TaskPage
/pm/:dashId                         → DashboardPage
*                                   → redirect to /
```

All routes use **direct imports** (no `React.lazy`) to keep dev simple and avoid stale-chunk hangs.

### Vite config

- proxy `/api` → `http://127.0.0.1:8000` and `/ws` → `ws://127.0.0.1:8000`
- `build.rollupOptions.output.manualChunks: undefined` (single-chunk prod build)
- `@/` alias to `src/`

### Stale-chunk auto-recovery

In `main.tsx`:
```ts
window.addEventListener("vite:preloadError", () => window.location.reload());
```

### Theme

Solid colors (no gradients on text). Tailwind tokens drive dark/light. Light is the default; toggle in topbar.

Palette goals:
- Primary accent: **muted teal** — `hsl(178 24% 48%)` light / `hsl(178 26% 54%)` dark. Elegant, professional, not too bright.
- Background: soft slate, not pure black, not warm brown. Use a single solid background across sidebar + main page (no two-tone).
- Headings on RTL/DV/PM pages: same teal as the Memory Studio main heading, NOT a gradient. Solid color throughout.
- Status colors: `success`/`warning`/`destructive` with low saturation.

Use shadcn/ui token names: `--background`, `--foreground`, `--muted`, `--accent`, `--primary`, `--destructive`, `--success`, `--warning`. Define both `:root` and `.dark` blocks in `globals.css`.

### SchemaForm

- Renders sections + fields from the YAML schema.
- Uses `react-hook-form` with a `zod` schema derived from field types.
- `password` type uses `<input type="password">`.
- Submit calls `POST /api/runs` with `{taskId, config}` and navigates the run pane to streaming mode.

### RunPane

- Subscribes to `WS /ws/runs/{run_id}`.
- Renders status badge, scrollable log area (mono font), copy-log button.
- When a `prompt` event arrives, shows an inline form with the requested fields and POSTs the answer to `POST /api/runs/{run_id}/prompt-response`.

### Subsystem Diagram Builder (bespoke)

On `/rtl/rtl_subsystem_integration`, a `Tabs` UI: **Form** / **Diagram Builder**.

Diagram Builder is a `reactflow` canvas:
- Left palette (categories: Memory, Interconnect, Safety/MMU, Custom).
  - Memory: DDR Controller, HBM Controller, PHY, Memory Channel
  - Interconnect: NoC, AXI Bridge, Crossbar
  - Safety/MMU: RAS, SMMU, IOMMU
  - Custom: Custom Block + a small "Add new block type" form (label + category, persisted to localStorage).
- Drag a tile onto the canvas to drop a node (snap-to-grid, default styling matches theme).
- Click two ports to draw an edge.
- Right "Properties" panel: shows selected node's label, channels (for Memory Channel), protocol (for controllers).
- Buttons: **Apply to Form** (counts blocks by type → fills the YAML form fields like `channels=N`, `protocol=...`, `noc=...`, etc., then switches to the Form tab), **Save (local)**, **Load saved**, **Clear canvas**.

### DashboardPage

Reads dashboard YAML from `/api/dashboards/{id}` and renders each `layout` item by `kind`:
- `kpi_row` → grid of `<Card>` tiles with metric + delta + accent color
- `rag` → horizontal segment bar (red/amber/green counts)
- `line` / `bar` → recharts line/bar with given series
- `donut` → recharts pie
- `feed` → vertical timeline list
- `table` → sortable table with optional `kind: "status"` column rendering badges
- `heatmap` → simple grid

Refresh: refetch every `refresh_s` seconds.

### Topbar features

- Search: fuzzy across tasks + dashboards (client-side).
- Run History drawer: most recent runs across all tasks, click → opens that run's log.
- Theme toggle: sun / moon icon, sets `class="dark"` on `<html>`.
- Settings dropdown.

## Integration guide (write `docs/INTEGRATION.md`)

Cover:
1. **Script-style tasks** (RTL/DV) — three replacement options: edit the dummy in place, point `script.path` at your own file, or wrap your tool in the dummy.
2. **Adapter-style dashboards** (PM) — two modes (mock by overwriting JSON, or live by setting `HDS_DATA_MODE=live` and filling in the adapter's `get_data`).
3. The full stdin/stdout/exit-code contract with an example.
4. The `##HDS-PROMPT##` mid-run prompt protocol.

## Dummy scripts (mandatory)

Each of the 11 scripts must be a runnable Python file that:
- prints a banner with the form values it received,
- prints 5–10 progress lines with `time.sleep(0.2–0.4)` between them,
- exits 0.

`debug.py` and `regression_run.py` should additionally demonstrate the
mid-run prompt protocol (ask for a JIRA token / queue token).

Add a docstring on every script:
```
REPLACE: placeholder. Plug in your real <X> tool.
Contract: JSON line on stdin (form fields) → progress on stdout → exit code.
See docs/INTEGRATION.md.
```

## Mock data (mandatory)

Every PM dashboard must have a matching JSON in `backend/mock_data/` with
realistic-looking numbers that exercise every widget on its layout. Add a
top-level `_note` key in each:
```
"_note": "REPLACE: mock data. Either overwrite this JSON with real exports or implement backend/app/adapters/<name>.py. See docs/INTEGRATION.md."
```

## launch.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM
( cd "$ROOT/backend";  [ -d .venv ] && source .venv/bin/activate; exec uvicorn app.main:app --reload --port 8000 ) &
( cd "$ROOT/frontend"; exec npm run dev ) &
wait
```

`frontend/package.json` `dev` script: `vite --host 127.0.0.1 --port 5173`.

## Acceptance criteria — verify before saying "done"

1. `python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt` succeeds on a clean machine.
2. `(cd frontend && npm install)` succeeds.
3. `./launch.sh` starts both servers without errors. `curl http://127.0.0.1:8000/api/health` returns `{"ok":true}`.
4. Open `http://localhost:5173`. Sidebar shows three groups: **RTL Toolkit** (3 tasks), **DV Workbench** (8 tasks), **PM Central** (6 dashboards).
5. Click any RTL/DV task → form renders → fill in → click Run → progress streams live in the run pane → status flips to **success**.
6. `regression_run` with `ask_token` checked → mid-run prompt appears → answering it lets the run continue.
7. Click any PM dashboard → renders KPIs/charts/tables/RAG from the mock JSON.
8. `/rtl/rtl_subsystem_integration` → switch to **Diagram Builder** tab → drag a DDR Controller and 4 Memory Channels and a NoC → click **Apply to Form** → tab switches to Form with `channels=4, noc=NoC, protocol=...` filled in.
9. Light/dark theme toggle works; both look professional with the muted teal accent and a soft slate background (no orange).
10. Leave the tab idle for several minutes, then click a different sidebar entry — page loads (the `vite:preloadError` handler hard-reloads on any stale chunk).
11. `git status` clean — no `.venv`, no `node_modules`, no tsc-emitted `.js` next to `.tsx`.

## Constraints / things to avoid

- Do NOT add authentication. Document the loopback-only assumption in README.
- Do NOT include hardcoded secrets, tokens, or example credentials.
- Do NOT use `shell=True` in `subprocess.Popen`.
- Do NOT use `yaml.load` (only `yaml.safe_load`).
- Do NOT add telemetry, analytics, or auto-update.
- Do NOT phone home on startup or on any UI action.
- All outbound network calls (Jira, Jenkins) must be opt-in via env vars and fall back to mock on missing config or error.

## Deliverables

A working repo matching the directory layout above, with `./launch.sh`
producing a fully functional local app, and the acceptance criteria above
all passing.
