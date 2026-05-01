# Integration guide — replacing the dummy scripts and adapters

This studio ships with **placeholder** implementations for every task and
dashboard so the UI is fully usable end-to-end. Every placeholder is meant to
be replaced with your real tool / data source. The contracts are stable, so
you can swap them one at a time without touching the frontend.

---

## 1. RTL Toolkit & DV Workbench tasks (script-style)

These tasks run a script when the user clicks "Run" in the form.

### Where to find them

| Task                      | YAML                                            | Script (replace this)                          |
|---------------------------|-------------------------------------------------|------------------------------------------------|
| RTL Review                | `backend/tasks/rtl/review.yaml`                 | `backend/scripts/rtl/review.py`                |
| SDC Generation            | `backend/tasks/rtl/sdc_gen.yaml`                | `backend/scripts/rtl/sdc_gen.py`               |
| Subsystem Integration     | `backend/tasks/rtl/subsystem_integration.yaml`  | `backend/scripts/rtl/integrate_subsystem.py`   |
| Coverage Model            | `backend/tasks/dv/coverage_model.yaml`          | `backend/scripts/dv/coverage_model.py`         |
| Debug                     | `backend/tasks/dv/debug.yaml`                   | `backend/scripts/dv/debug.py`                  |
| RAL Generation            | `backend/tasks/dv/ral_gen.yaml`                 | `backend/scripts/dv/ral_gen.py`                |
| Regression Run            | `backend/tasks/dv/regression_run.yaml`          | `backend/scripts/dv/regression_run.py`         |
| Test Strategy             | `backend/tasks/dv/test_strategy.yaml`           | `backend/scripts/dv/test_strategy.py`          |
| Testbench Creation        | `backend/tasks/dv/testbench_create.yaml`        | `backend/scripts/dv/testbench_create.py`       |
| Testplan Generation       | `backend/tasks/dv/testplan_gen.yaml`            | `backend/scripts/dv/testplan_gen.py`           |
| VIP Integration           | `backend/tasks/dv/vip_integration.yaml`         | `backend/scripts/dv/vip_integration.py`        |

### Contract

```
stdin:   ONE JSON line containing every form field as a flat dict.
         Keys match the `key:` of each field in the YAML form.
stdout:  free-text progress lines. Each line is streamed live to the UI.
stderr:  ignored by the UI but captured in the run log.
exit:    0 = success, non-zero = failure (the run is marked red).
```

Optional: print a special marker to ask the user a mid-run question and
read the answer from stdin (see `dv/regression_run.py` for an example):

```
HDS-PROMPT {"id":"continue","question":"Continue past failures?","type":"bool"}
```

The runner will pause, show the prompt in the UI, and write the response back
on stdin as a JSON line.

### Replacement options

1. **Edit in place.** Open the dummy `.py`, delete the demo body, and call
   your real tool. The runner doesn't care what language you spawn as long as
   the script eventually prints lines and exits.
2. **Point at a different file.** Edit the YAML's `script.path:` to your own
   script. Set `script.type:` to `bash` or `shell` if it's not Python.
3. **Wrap your tool.** Keep the dummy as a thin wrapper that exec's your real
   binary with the form params (`subprocess.run([...])`). Stream its output
   with `print(line, flush=True)`.

### Adding a new task

1. Drop a new YAML in `backend/tasks/<group>/`.
2. Add a script in `backend/scripts/<group>/`.
3. The sidebar picks it up on backend reload — no frontend change needed.

---

## 2. PM Central dashboards (adapter-style)

PM tabs are dashboards, not runs. Each YAML has an `adapter:` field.
At request time, the backend dispatches it through
`backend/app/adapters/dispatch.py`.

### Two modes

The mode is controlled by env var `HDS_DATA_MODE`:

* **`mock` (default)** — reads `backend/mock_data/<adapter>.json` and returns
  it as-is. This is what you see right now.
* **`live`** — calls `_LIVE[name]` in `dispatch.py` instead. If the live call
  fails, the adapter falls back to the mock JSON so the UI never breaks.

### Where to plug in real data

| Dashboard          | YAML                                           | Mock data (rename/edit)                | Live adapter (edit)                                |
|--------------------|------------------------------------------------|----------------------------------------|----------------------------------------------------|
| PM Overview        | `backend/tasks/pm/pm_overview.yaml`            | `backend/mock_data/pm_overview.json`   | `backend/app/adapters/pm_overview.py`              |
| IP Owners          | `backend/tasks/pm/ip_owners.yaml`              | `backend/mock_data/ip_owners.json`     | `backend/app/adapters/ip_owners.py`                |
| JIRA Bug Trends    | `backend/tasks/pm/jira_trends.yaml`            | `backend/mock_data/jira.json`          | `backend/app/adapters/jira_rest.py` (already wired)|
| Milestones         | `backend/tasks/pm/milestones.yaml`             | `backend/mock_data/milestones.json`    | `backend/app/adapters/milestones.py`               |
| Regression Trends  | `backend/tasks/pm/regression_trends.yaml`      | `backend/mock_data/regression_trends.json` | `backend/app/adapters/regression_db.py` / `jenkins.py` (already wired) |
| RTL Completion     | `backend/tasks/pm/rtl_completion.yaml`         | `backend/mock_data/rtl_completion.json`| `backend/app/adapters/rtl_completion.py`           |

### Contract

```python
def get_data(params: dict) -> dict:
    """Return a JSON-serialisable dict in the same shape as the mock JSON."""
```

* `params` comes from the dashboard YAML's `params:` block (often empty).
* The returned dict is rendered by the layout widgets (`kpi_row`, `line`,
  `bar`, `donut`, `feed`, `table`, `rag`, ...). The shape must match — easiest
  way is to keep the mock JSON next to your live code and copy its structure.

### Quickest path to real data

1. Set `HDS_DATA_MODE=live` (e.g. in your shell or `.env`).
2. Open the relevant adapter file under `backend/app/adapters/`.
3. Replace the body of `get_data()` with your real query.
4. On error, return `_fallback()` so the dashboard degrades to mock instead
   of breaking.

### Even simpler: just regenerate the JSON

If you have a nightly job that writes a JSON file, you don't even need to
touch Python. Have the job overwrite `backend/mock_data/<adapter>.json` and
keep `HDS_DATA_MODE=mock`. The dashboard will pick up the new data on the
next refresh tick (`refresh_s:` in the YAML).
