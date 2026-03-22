# DV Skills GUI — Generation Prompts & Design Decisions

All prompts and Q&A that drove the design and implementation of the DV Skills GUI wizard.

---

## Prompt 1 — Initial GUI Request

> Build a Flask-based interactive GUI wizard for all 10 DV skills (S1–S10).
> Each skill should have a multi-step wizard with inputs, a terminal output panel,
> and live streaming of script output via SSE.

---

## Prompt 2 — Project Settings Section

> I want you to add project specific options separately which will include following:
> 1. Project name
> 2. Workspace directory
> 3. GitHub repo
> 4. Username
> 5. Choose tool — VCS, Questa, Mentor (with path)
> 6. Coding guidelines path
> 7. IP to SoC Integration guidelines
> 8. Spec path
> 9. Other standard input for a DV project
>
> Also improve the design with dark luxurious mode with deep charcoal background,
> soft neon indigo glows and elegant glassmorphism cards with frosted blur,
> neumorphic shadows.

---

## Prompt 3 — Per-Section Run Buttons

> Now I want you to add one run/generate button for each section which becomes
> active when all fields are filled and executes a batch file when clicked.
> It should be added in a way that the design becomes more elegant.

**Design decisions made:**
- Button activates only when all required fields in that section are filled
- State machine: `incomplete → ready → running → success / error`
- Button label changes per state: "Fill required fields" / "Run" / "Running…" / "✓ Done" / "✗ Failed"
- Orange dot indicator next to each section shows current status

---

## Prompt 4 — Bash Script Execution

> Modify the GUI again to call `run_chipagent_<section_id>.bash` script in the
> background when Run is clicked.

**Implementation decisions:**
- Scripts stored in `dv-gui/scripts/` directory
- Named `run_chipagent_<section_id>.bash` (e.g. `run_chipagent_identity.bash`)
- All project config fields injected as UPPER_CASE environment variables
- If script doesn't exist → falls back to demo mode with warning
- Script output streamed live to terminal via SSE
- Project config auto-saved to `runs/project_config.json` before each run

**Section → Action mapping:**
| Section ID  | Action ID         | Script                              |
|-------------|-------------------|-------------------------------------|
| identity    | init_project      | run_chipagent_identity.bash         |
| workspace   | setup_workspace   | run_chipagent_workspace.bash        |
| tools       | verify_tools      | run_chipagent_tools.bash            |
| guidelines  | validate_docs     | run_chipagent_guidelines.bash       |
| dut         | gen_dut_config    | run_chipagent_dut.bash              |
| sim         | gen_sim_defaults  | run_chipagent_sim.bash              |

**Bash scripts generated:**
- `run_chipagent_identity.bash` — creates DV dir scaffold, git init, .gitignore, README, project_config.json
- `run_chipagent_workspace.bash` — creates runs/logs/reports/artifacts dirs, checks disk space, writes workspace.yaml
- `run_chipagent_tools.bash` — checks EDA binary (vcs/vsim/xrun), tests license server port
- `run_chipagent_guidelines.bash` — validates coding & SoC doc files, copies to workspace/doc/, writes guidelines_index.yaml
- `run_chipagent_dut.bash` — derives clock period/half-period, writes dut_config.yaml, dut_params_pkg.sv, dut_clk_rst_if.sv
- `run_chipagent_sim.bash` — writes sim_defaults.yaml, Makefile.sim_defaults, run_sim.sh (VCS/Questa/Xcelium runner)

---

## Prompt 5 — Sutera-Inspired Redesign

> Use https://www.awwwards.com/sites/sutera as inspiration for color and layout
> idea for DV GUI, and make it look super rich and professional and functional.

**Design system adopted:**
| Token          | Value                        |
|----------------|------------------------------|
| Font           | Inter Tight (Google Fonts, 300–900) |
| Primary accent | `#FA5D29` (Sutera orange)    |
| Void bg        | `#0A0907`                    |
| Page bg        | `#111009`                    |
| Card bg        | `#1A1714`                    |
| Body text      | `#C8C0B8`                    |
| Border         | `rgba(255,255,255,0.06)`     |
| Button height  | 40px                         |
| Border radius  | 8px                          |
| Transition     | 0.3s ease                    |

**Visual changes:**
- Replaced glassmorphism with solid warm espresso surfaces
- Switched indigo accent → Sutera signature orange `#FA5D29`
- Dashboard editorial stats bar (large tabular-number display)
- Skill cards: orange left-border slide-in on hover
- Sidebar: 272px, warm charcoal, orange left accent on active items
- Terminal: warm espresso bg, orange running/system line colours
- No glassmorphism — solid surfaces with subtle 1px borders
- Large `clamp()` typography for section headers

---

## Prompt 6 — S6/S7 Instantly Failing

> Can you check why run assertion and run sequences always show up as failed
> when I click run section button?

**Root cause:** S1–S5 run in demo mode (AI skills with no real output files).
S6/S7 real scripts require `testplan_rows` and `tb_data` from upstream skills.
When those JSON files don't exist on disk, S6 exits with `sys.exit(1)` —
"ERROR: No testplan rows found."

**Fix:** In `_execute_skill()`, check whether upstream data files exist before
running the real script. If missing → fall back to demo mode for S6/S7/S8
with a terminal warning explaining which files are missing.

---

## Prompt 7 — Linux Deployment

> How can I open this in Linux if I clone this repo?

**Setup on Linux:**
```bash
git clone https://github.com/rajivhasija79-bit/DV-Skills.git
cd DV-Skills
pip3 install flask openpyxl
python3 dv-gui/app.py
```

---

## Prompt 8 — Port Issues on Linux

> Port 7437 is in use by another program and it doesn't say use some other
> port instead. Could it be because of security issues in my organisation?

**Root cause 1:** `SO_REUSEADDR` in port probe gave a false "port is free"
result on Linux — our probe succeeded but werkzeug's own bind failed.

**Root cause 2:** Hardcoded fallback ports (8080, 8888, 9000) are commonly
blocked by org security policies.

**Fix applied:**
- Probe WITHOUT `SO_REUSEADDR` (matches werkzeug's exact bind behaviour)
- If preferred port (7437) blocked → fall back to OS-assigned ephemeral port
  (`bind(0)`) in range 32768–60999 — never targeted by any org security policy
- Or override via env var: `PORT=9999 python3 dv-gui/app.py`
- Terminal always prints the actual URL being served

---

## Prompt 9 — TemplateNotFound on Linux

> It gave `jinja2.exceptions.TemplateNotFound: index.html` error.

**Root cause:** Flask resolves `templates/` relative to the current working
directory. Running `python3 dv-gui/app.py` from the repo root caused Flask
to look for `templates/` in the repo root instead of `dv-gui/templates/`.

**Fix:** Pin `template_folder` to the script's own directory:
```python
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
```

---

## Architecture Notes

### Backend (`dv-gui/app.py`)
- Flask with SSE for live terminal streaming
- `POST /api/project-action/<section_id>` — runs project setup scripts
- `POST /api/skills/<skill_id>/run` — runs S1–S10 skill scripts
- `GET  /api/stream/<run_id>` — SSE stream for terminal output
- `GET  /api/status` — returns all skill statuses
- `GET  /api/project-config` — returns saved project config
- `GET  /api/browse` — filesystem browser for path picker

### Frontend (`dv-gui/templates/index.html`)
- Vanilla JS — no framework
- `State` module — skill statuses, project config, active run
- `Wizard` module — multi-step skill wizard, terminal, file picker
- `ProjectSettings` module — 6-section project config with per-section run buttons
- `Terminal` module — SSE consumer, colour-coded output lines
- `FilePicker` module — inline filesystem browser

### File Layout
```
dv-gui/
├── app.py                          # Flask backend
├── requirements.txt                # flask, openpyxl
├── templates/
│   └── index.html                  # full SPA frontend
├── scripts/
│   ├── run_chipagent_identity.bash
│   ├── run_chipagent_workspace.bash
│   ├── run_chipagent_tools.bash
│   ├── run_chipagent_guidelines.bash
│   ├── run_chipagent_dut.bash
│   └── run_chipagent_sim.bash
└── runs/
    ├── project_config.json         # saved project settings
    ├── skill_status.json           # S1–S10 run statuses
    └── <run_id>_input.json         # per-run input snapshots
```
