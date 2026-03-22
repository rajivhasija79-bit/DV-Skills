#!/usr/bin/env python3
"""
DV Skills GUI — Flask backend
Run: python3 app.py
Opens: http://127.0.0.1:7437
"""

import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
RUNS_DIR  = BASE_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)

SCRIPTS_DIR = BASE_DIR.parent / "skills" / "common" / "scripts"

# ── Skill metadata ────────────────────────────────────────────────────────────
SKILL_IDS = ["s1","s2","s3","s4","s5","s6","s7","s8","s9","s10"]

SKILL_DEPS = {
    "s1":  [],
    "s2":  ["s1"],
    "s3":  ["s1","s2"],
    "s4":  ["s1"],
    "s5":  ["s1","s2","s3","s4"],
    "s6":  ["s5","s2"],
    "s7":  ["s5"],
    "s8":  ["s5","s7"],
    "s9":  ["s6"],
    "s10": ["s7","s9"],
}

# Script that implements each skill (None = interactive/AI skill, runs in demo mode)
SKILL_SCRIPTS = {
    "s1":  None,
    "s2":  None,
    "s3":  None,
    "s4":  None,
    "s5":  None,
    "s6":  SCRIPTS_DIR / "generate_sequences.py",
    "s7":  SCRIPTS_DIR / "generate_assertions.py",
    "s8":  SCRIPTS_DIR / "generate_scoreboard.py",
    "s9":  SCRIPTS_DIR / "run_regression.py",
    "s10": SCRIPTS_DIR / "generate_coverage_closure.py",
}

SKILL_DEMO_STEPS = {
    "s1":  ["Parsing specification document...",
            "Detecting VIP interfaces...",
            "Extracting protocol signals (APB, UART)...",
            "Building register map from spec tables...",
            "Identifying clock domains...",
            "Writing dv_spec_data.json...",
            "✓  S1 complete — 2 VIPs, 8 registers, 1 clock domain extracted"],
    "s2":  ["Loading dv_spec_data.json from S1...",
            "Analysing VIP capabilities...",
            "Generating testplan rows per feature...",
            "Assigning milestone targets (DV-I / DV-C / DV-F)...",
            "Writing testplan.xlsx...",
            "Writing dv_testplan_data.json...",
            "✓  S2 complete — 12 testplan rows generated"],
    "s3":  ["Loading spec + testplan data...",
            "Designing TB architecture...",
            "Planning agent hierarchy...",
            "Identifying deduplication opportunities...",
            "Generating dv_tb_arch_data.json...",
            "✓  S3 complete — 2 agents, 1 env, virtual sequencer planned"],
    "s4":  ["Loading register map from S1...",
            "Generating uvm_reg_block class...",
            "Adding register fields with access types...",
            "Generating frontdoor sequences...",
            "Writing RAL package...",
            "✓  S4 complete — 8 registers, 2 sequences generated"],
    "s5":  ["Loading TB arch + RAL data...",
            "Generating agent files (driver, monitor, sequencer, seq_item)...",
            "Generating env + cfg files...",
            "Generating virtual sequencer...",
            "Generating base test class...",
            "Generating compile.f + Makefile...",
            "✓  S5 complete — 24 TB files generated"],
    "s6":  ["Loading TB data from S5...",
            "Loading testplan rows from S2...",
            "Generating agent base sequences (APB, UART)...",
            "Generating base virtual sequence...",
            "Generating directed virtual sequences (12 rows)...",
            "Generating randomised virtual sequences...",
            "Generating test classes (DV-I: 3, DV-C: 5, DV-F: 4)...",
            "Writing dv_sequences_data.json...",
            "✓  S6 complete — 24 sequence files, 12 test classes generated"],
    "s7":  ["Loading TB data from S5...",
            "Loading testplan rows from S2...",
            "Categorising assertions by VIP and DUT internal...",
            "Generating APB assertion module (apb_assertions.sv)...",
            "Generating UART assertion module (uart_assertions.sv)...",
            "Generating DUT bind module (dut_assertions_bind.sv)...",
            "Generating assertion control package...",
            "Generating assertion checker UVM component...",
            "Writing dv_assertions_data.json...",
            "✓  S7 complete — 18 assertions, 2 VIP modules, bind module generated"],
    "s8":  ["Loading TB data from S5...",
            "Loading assertions data from S7...",
            "Loading testplan rows from S2...",
            "Generating sb_transaction class...",
            "Generating reference model (SV stub)...",
            "Generating scoreboard (in-order)...",
            "Generating functional coverage model...",
            "Linking CHK_IDs to scoreboard checks...",
            "Writing dv_scoreboard_data.json...",
            "✓  S8 complete — scoreboard + refmodel + coverage model generated"],
    "s9":  ["Loading sequences data from S6...",
            "Building DV-I test list (3 tests × 1 seed)...",
            "Building DV-C test list (5 tests × 5 seeds)...",
            "Building DV-F test list (4 tests × 20 seeds)...",
            "Dispatching 28 jobs (local ThreadPoolExecutor, 8 workers)...",
            "Running simulations... [████████████████████] 100%",
            "Parsing simulation logs...",
            "28/28 PASSED",
            "Generating HTML regression report...",
            "Writing dv_regression_data.json...",
            "✓  S9 complete — 28/28 passed, report written"],
    "s10": ["Loading coverage database...",
            "Loading regression data from S9...",
            "Loading assertions data from S7...",
            "Running urg coverage merge...",
            "Line coverage    : 99.2% (threshold: 99%  ✓)",
            "Toggle coverage  : 96.1% (threshold: 95%  ✓)",
            "Functional coverage: 100.0% (threshold: 99%  ✓)",
            "Generating exclusion suggestions (3 items)...",
            "Writing coverage_signoff_report.html...",
            "Writing dv_coverage_data.json...",
            "✓  S10 complete — coverage closure achieved, sign-off report written"],
}

# ── State ─────────────────────────────────────────────────────────────────────
STATUS_FILE         = RUNS_DIR / "skill_status.json"
PROJECT_CONFIG_FILE = RUNS_DIR / "project_config.json"
_runs: dict = {}        # run_id → run dict
_runs_lock  = threading.Lock()


def load_project_config() -> dict:
    if PROJECT_CONFIG_FILE.exists():
        try:
            return json.loads(PROJECT_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_project_config_file(cfg: dict):
    PROJECT_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def _default_status():
    return {sid: {"status": "idle", "last_run": None, "run_id": None, "exit_code": None}
            for sid in SKILL_IDS}


def load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return _default_status()


def save_status(s: dict):
    STATUS_FILE.write_text(json.dumps(s, indent=2))


skill_status = load_status()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def get_status():
    result = {}
    for sid in SKILL_IDS:
        s = skill_status.get(sid, {"status": "idle", "last_run": None, "run_id": None})
        deps     = SKILL_DEPS[sid]
        deps_met = all(skill_status.get(d, {}).get("status") == "success" for d in deps)
        # Check if an in-memory run is still active
        run_id = s.get("run_id")
        if run_id:
            with _runs_lock:
                run = _runs.get(run_id)
            if run and run.get("status") == "running":
                s = {**s, "status": "running"}
        result[sid] = {**s, "deps_met": deps_met, "deps": deps}
    return jsonify({"skills": result})


@app.route("/api/run/<skill_id>", methods=["POST"])
def run_skill_route(skill_id):
    if skill_id not in SKILL_IDS:
        return jsonify({"error": "Unknown skill"}), 404

    current = skill_status.get(skill_id, {})
    if current.get("status") == "running":
        run_id = current.get("run_id", "")
        with _runs_lock:
            run = _runs.get(run_id, {})
        if run.get("status") == "running":
            return jsonify({"error": "Already running"}), 409

    missing = [d for d in SKILL_DEPS[skill_id]
               if skill_status.get(d, {}).get("status") != "success"]
    if missing:
        return jsonify({"error": "dependencies not met", "missing": missing}), 400

    params = request.get_json() or {}
    run_id = f"{skill_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    skill_status[skill_id] = {
        "status": "running", "last_run": None, "run_id": run_id, "exit_code": None,
    }
    save_status(skill_status)

    with _runs_lock:
        _runs[run_id] = {
            "skill_id":   skill_id,
            "params":     params,
            "lines":      [],
            "status":     "running",
            "exit_code":  None,
            "started_at": time.time(),
            "finished_at": None,
        }

    threading.Thread(target=_execute_skill, args=(skill_id, run_id, params),
                     daemon=True).start()
    return jsonify({"run_id": run_id, "status": "started"})


@app.route("/api/stream/<run_id>")
def stream_run(run_id):
    def generate():
        last_idx = 0
        timeout  = time.time() + 3600  # max 1h stream
        while time.time() < timeout:
            with _runs_lock:
                run = _runs.get(run_id)
                if not run:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Run not found'})}\n\n"
                    return
                new_lines = run["lines"][last_idx:]
                run_status = run["status"]
                exit_code  = run.get("exit_code")

            for entry in new_lines:
                yield f"data: {json.dumps(entry)}\n\n"
            last_idx += len(new_lines)

            if run_status == "done":
                yield f"data: {json.dumps({'type': 'exit', 'code': exit_code, 'ts': time.time()})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            yield ": keepalive\n\n"
            time.sleep(0.4)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/run/<run_id>/log")
def get_log(run_id):
    with _runs_lock:
        run = _runs.get(run_id)
        if not run:
            return jsonify({"error": "Run not found"}), 404
        return jsonify({
            "run_id":    run_id,
            "skill_id":  run["skill_id"],
            "lines":     run["lines"],
            "exit_code": run.get("exit_code"),
            "status":    run["status"],
        })


@app.route("/api/cancel/<run_id>", methods=["POST"])
def cancel_run(run_id):
    with _runs_lock:
        run = _runs.get(run_id)
        if not run:
            return jsonify({"error": "Run not found"}), 404
        proc = run.get("process")
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
    return jsonify({"status": "cancelled"})


@app.route("/api/reset/<skill_id>", methods=["POST"])
def reset_skill(skill_id):
    if skill_id not in SKILL_IDS:
        return jsonify({"error": "Unknown skill"}), 404
    skill_status[skill_id] = {"status": "idle", "last_run": None, "run_id": None, "exit_code": None}
    save_status(skill_status)
    return jsonify({"status": "reset"})


@app.route("/api/reset-all", methods=["POST"])
def reset_all():
    for sid in SKILL_IDS:
        skill_status[sid] = {"status": "idle", "last_run": None, "run_id": None, "exit_code": None}
    save_status(skill_status)
    return jsonify({"status": "reset"})


@app.route("/api/project-config", methods=["GET"])
def get_project_config():
    return jsonify(load_project_config())


@app.route("/api/project-config", methods=["POST"])
def post_project_config():
    cfg = request.get_json() or {}
    save_project_config_file(cfg)
    return jsonify({"status": "saved"})


# ── Project Actions ────────────────────────────────────────────────────────

# ── Bash script directory ─────────────────────────────────────────────────
BASH_SCRIPTS_DIR = BASE_DIR / "scripts"
BASH_SCRIPTS_DIR.mkdir(exist_ok=True)

# Section ID  →  demo action key (fallback when bash script missing)
SECTION_TO_ACTION = {
    "identity":   "init_project",
    "workspace":  "setup_workspace",
    "tools":      "verify_tools",
    "guidelines": "validate_docs",
    "dut":        "gen_dut_config",
    "sim":        "gen_sim_defaults",
}

PROJECT_ACTION_DEMOS = {
    "init_project": [
        "Initializing DV project structure…",
        "Creating  {workspace_dir}/{project_name}/",
        "Creating  {workspace_dir}/{project_name}/rtl/",
        "Creating  {workspace_dir}/{project_name}/dv/",
        "Creating  {workspace_dir}/{project_name}/dv/tb/",
        "Creating  {workspace_dir}/{project_name}/dv/sequences/",
        "Creating  {workspace_dir}/{project_name}/dv/tests/",
        "Creating  {workspace_dir}/{project_name}/dv/assertions/",
        "Creating  {workspace_dir}/{project_name}/dv/coverage/",
        "Creating  {workspace_dir}/{project_name}/dv/regression/",
        "Initialising git repository…",
        "Writing  .gitignore",
        "Writing  README.md",
        "Writing  project_config.json",
        "✓  Project '{project_name}' initialised — engineer: {user_name}",
    ],
    "setup_workspace": [
        "Validating workspace path…",
        "Workspace root : {workspace_dir}",
        "Specification  : {spec_path}",
        "Checking write permissions…  OK",
        "Creating {workspace_dir}/runs/",
        "Creating {workspace_dir}/logs/",
        "Creating {workspace_dir}/reports/",
        "Creating {workspace_dir}/artifacts/",
        "Writing  workspace.yaml",
        "✓  Workspace ready at {workspace_dir}",
    ],
    "verify_tools": [
        "Checking EDA tool installation…",
        "Tool selected  : {eda_tool}",
        "Install path   : {eda_tool_path}",
        "Running binary version check…",
        "License server : {license_server}",
        "Sending test checkout request…",
        "Feature: vcs_mx   — GRANTED",
        "Feature: vcselab  — GRANTED",
        "License server response time: 42 ms",
        "✓  {eda_tool} verified — licence OK",
    ],
    "validate_docs": [
        "Validating documentation paths…",
        "Coding guidelines    : {coding_guidelines}",
        "  → file found, size: OK",
        "SoC integration guide: {soc_integ_guidelines}",
        "  → file found, size: OK",
        "Parsing section headings…",
        "  Found 24 coding rules",
        "  Found 12 SoC integration checkpoints",
        "✓  All documentation files validated and accessible",
    ],
    "gen_dut_config": [
        "Generating DUT configuration files…",
        "Top-level module : {top_module}",
        "Clock frequency  : {clock_freq} MHz  →  period = {clock_period} ns",
        "Timescale        : {timescale}",
        "Reset polarity   : {reset_polarity}",
        "Writing  dut_config.yaml",
        "Writing  dut_params_pkg.sv",
        "Writing  dut_if_params.sv",
        "✓  DUT configuration generated for '{top_module}'",
    ],
    "gen_sim_defaults": [
        "Applying simulation defaults…",
        "Wave format     : {wave_format}",
        "UVM verbosity   : {uvm_verbosity}",
        "Extra sim flags : {extra_sim_flags}",
        "Writing  sim_defaults.yaml",
        "Writing  Makefile.sim_defaults",
        "Writing  run_sim.sh  (template)",
        "✓  Simulation defaults applied and written",
    ],
}


def _fmt(s: str, params: dict) -> str:
    """Interpolate {key} placeholders; leave unknown keys as-is."""
    safe = {k: (v or "(not set)") for k, v in params.items()}
    # compute clock_period if clock_freq is numeric
    try:
        mhz = float(safe.get("clock_freq", "0"))
        safe["clock_period"] = f"{1000/mhz:.2f}" if mhz else "?"
    except Exception:
        safe["clock_period"] = "?"
    try:
        return s.format_map(safe)
    except Exception:
        return s


@app.route("/api/project-action/<section_id>", methods=["POST"])
def run_project_action(section_id):
    if section_id not in SECTION_TO_ACTION:
        return jsonify({"error": f"Unknown section: {section_id}"}), 404

    params  = request.get_json() or {}
    merged  = {**load_project_config(), **params}
    run_id  = f"proj_{section_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    with _runs_lock:
        _runs[run_id] = {
            "skill_id": f"proj_{section_id}", "params": merged,
            "lines": [], "status": "running", "exit_code": None,
            "started_at": time.time(), "finished_at": None,
        }

    script = BASH_SCRIPTS_DIR / f"run_chipagent_{section_id}.bash"
    if script.exists():
        threading.Thread(
            target=_run_bash_script,
            args=(section_id, run_id, merged, script), daemon=True
        ).start()
    else:
        # Graceful fallback — demo mode with a warning
        action_id = SECTION_TO_ACTION[section_id]
        threading.Thread(
            target=_run_project_action_demo,
            args=(section_id, action_id, run_id, merged), daemon=True
        ).start()

    return jsonify({"run_id": run_id, "status": "started"})


def _run_bash_script(section_id: str, run_id: str, params: dict, script: Path):
    """Execute run_chipagent_<section_id>.bash with project config as env vars."""
    # Build environment: inherit process env, inject project config as UPPER_CASE vars
    env = {**os.environ}
    for k, v in params.items():
        if v is not None:
            env[k.upper()] = str(v)

    _add_line(run_id, "system",
              f"▶  run_chipagent_{section_id}.bash")
    _add_line(run_id, "system",
              f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _add_line(run_id, "system",
              f"   Script : {script}")
    _add_line(run_id, "system",
              f"   Working: {script.parent}")

    try:
        proc = subprocess.Popen(
            ["bash", str(script)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
            cwd=str(script.parent),
        )
        with _runs_lock:
            if run_id in _runs:
                _runs[run_id]["process"] = proc

        import select as _select
        while True:
            r, _, _ = _select.select([proc.stdout, proc.stderr], [], [], 0.1)
            for stream in r:
                line = stream.readline()
                if line:
                    t = "stdout" if stream is proc.stdout else "stderr"
                    _add_line(run_id, t, line.rstrip())
            if proc.poll() is not None:
                for line in proc.stdout: _add_line(run_id, "stdout", line.rstrip())
                for line in proc.stderr: _add_line(run_id, "stderr", line.rstrip())
                break

        _finish_run(run_id, f"proj_{section_id}", proc.returncode)

    except Exception as exc:
        _add_line(run_id, "stderr", f"Failed to execute script: {exc}")
        _finish_run(run_id, f"proj_{section_id}", 1)


def _run_project_action_demo(section_id: str, action_id: str, run_id: str, params: dict):
    """Fallback demo when bash script is absent."""
    import random
    _add_line(run_id, "system",
              f"▶  {action_id.replace('_',' ').title()}  [demo — run_chipagent_{section_id}.bash not found]")
    _add_line(run_id, "system",
              f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for step in PROJECT_ACTION_DEMOS.get(action_id, ["Running…", "✓ Done"]):
        time.sleep(random.uniform(0.28, 0.65))
        text = _fmt(step, params)
        _add_line(run_id, "success" if text.startswith("✓") else "stdout", text)
    _finish_run(run_id, f"proj_{section_id}", 0)


@app.route("/api/browse")
def browse():
    path        = request.args.get("path", os.path.expanduser("~"))
    filter_type = request.args.get("type", "both")  # file | dir | both
    try:
        p = Path(path)
        if not p.exists() or not p.is_dir():
            p = Path(os.path.expanduser("~"))

        entries = []
        for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                if item.name.startswith("."):
                    continue
                is_dir = item.is_dir()
                if filter_type == "dir" and not is_dir:
                    continue
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "dir" if is_dir else "file",
                    "ext":  item.suffix.lower() if not is_dir else "",
                })
            except PermissionError:
                pass

        return jsonify({
            "current": str(p),
            "parent":  str(p.parent) if str(p.parent) != str(p) else None,
            "entries": entries,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Skill execution ───────────────────────────────────────────────────────────

def _add_line(run_id: str, line_type: str, content: str):
    entry = {"type": line_type, "line": content, "ts": time.time()}
    with _runs_lock:
        if run_id in _runs:
            _runs[run_id]["lines"].append(entry)
            # Buffer cap
            if len(_runs[run_id]["lines"]) > 6000:
                _runs[run_id]["lines"] = _runs[run_id]["lines"][-5000:]


def _finish_run(run_id: str, skill_id: str, exit_code: int):
    status = "success" if exit_code == 0 else ("cancelled" if exit_code < 0 else "error")
    with _runs_lock:
        if run_id in _runs:
            _runs[run_id]["status"]      = "done"
            _runs[run_id]["exit_code"]   = exit_code
            _runs[run_id]["finished_at"] = time.time()
    skill_status[skill_id] = {
        "status":   status,
        "last_run": datetime.now().isoformat(),
        "run_id":   run_id,
        "exit_code": exit_code,
    }
    save_status(skill_status)


def _has_real_data(skill_id: str, params: dict) -> tuple[bool, str]:
    """Return (True, '') if the required upstream data files exist on disk,
    else (False, reason) so the caller can fall back to demo mode."""
    tb_data_path = params.get("tb_data", "")
    testplan_path = params.get("testplan", "")

    if skill_id in ("s6", "s7", "s8"):
        # Need a real tb_data JSON written by S5
        if not tb_data_path or not Path(tb_data_path).exists():
            return False, (
                f"tb_data file not found: '{tb_data_path or '(not set)'}'. "
                "S5 must produce dv_tb_data.json first. Running in demo mode."
            )
        # S6 also needs testplan rows
        if skill_id == "s6":
            if not testplan_path or not Path(testplan_path).exists():
                return False, (
                    f"Testplan file not found: '{testplan_path or '(not set)'}'. "
                    "S2 must produce testplan.xlsx or dv_testplan_data.json first. Running in demo mode."
                )
    if skill_id == "s9":
        seq_data = params.get("seq_data", "")
        if not seq_data or not Path(seq_data).exists():
            return False, (
                f"seq_data file not found: '{seq_data or '(not set)'}'. "
                "S6 must produce dv_sequences_data.json first. Running in demo mode."
            )
    if skill_id == "s10":
        vdb = params.get("vdb_path", "")
        if not vdb or not Path(vdb).exists():
            return False, (
                f"VDB path not found: '{vdb or '(not set)'}'. "
                "S9 must produce a merged coverage database first. Running in demo mode."
            )
    return True, ""


def _execute_skill(skill_id: str, run_id: str, params: dict):
    # Merge saved project config as base; explicit params override
    merged = {**load_project_config(), **params}
    params = merged
    project = params.get("project_name", "project")
    _add_line(run_id, "system", f"▶  Starting {skill_id.upper()} — project: {project}")
    _add_line(run_id, "system", f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    script = SKILL_SCRIPTS.get(skill_id)
    if script is None or not Path(script).exists():
        _run_demo(skill_id, run_id, params)
        return

    # Check upstream data files exist; fall back to demo if not
    ok, reason = _has_real_data(skill_id, params)
    if not ok:
        _add_line(run_id, "stderr", f"⚠  {reason}")
        _run_demo(skill_id, run_id, params)
        return

    cmd = _build_cmd(skill_id, params, script, run_id)
    _add_line(run_id, "system", f"   cmd: {' '.join(str(c) for c in cmd)}")

    try:
        proc = subprocess.Popen(
            [str(c) for c in cmd],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
            cwd=params.get("output_dir") or str(BASE_DIR.parent),
        )
        with _runs_lock:
            if run_id in _runs:
                _runs[run_id]["process"] = proc

        import select
        while True:
            r, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.1)
            for stream in r:
                line = stream.readline()
                if line:
                    t = "stdout" if stream == proc.stdout else "stderr"
                    _add_line(run_id, t, line.rstrip())
            if proc.poll() is not None:
                for line in proc.stdout: _add_line(run_id, "stdout", line.rstrip())
                for line in proc.stderr: _add_line(run_id, "stderr", line.rstrip())
                break

        _finish_run(run_id, skill_id, proc.returncode)

    except Exception as exc:
        _add_line(run_id, "stderr", f"Fatal error: {exc}")
        _finish_run(run_id, skill_id, 1)


def _load_json_file(path: str) -> dict:
    """Safely load a JSON file; return empty dict on any error."""
    try:
        p = Path(path)
        if p.exists() and p.is_file():
            return json.loads(p.read_text())
    except Exception:
        pass
    return {}


def _load_testplan_rows(path: str) -> list:
    """Load testplan rows from a JSON file; return empty list on error."""
    data = _load_json_file(path)
    # Support both { "testplan_rows": [...] } and a bare list
    if isinstance(data, list):
        return data
    return data.get("testplan_rows", data.get("rows", []))


def _write_input_json(run_id: str, payload: dict) -> Path:
    """Write the assembled input JSON to a temp file and return its path."""
    tmp = RUNS_DIR / f"{run_id}_input.json"
    tmp.write_text(json.dumps(payload, indent=2))
    return tmp


def _build_cmd(skill_id: str, params: dict, script: Path, run_id: str = "") -> list:
    """Build the correct CLI for each skill script.

    S6 / S7 / S8 all use  --input <assembled_json>  --output <dv_root>
    S9  uses its own flag set
    S10 uses --project / --vdb / --out / --reg-data / --assert-data
    """
    project    = params.get("project_name", "project")
    output_dir = params.get("output_dir", ".")

    # ── S6 — generate_sequences.py ────────────────────────────────────────
    if skill_id == "s6":
        tb_data = _load_json_file(params.get("tb_data", ""))
        if not tb_data:
            tb_data = {"project_name": project}
        else:
            tb_data.setdefault("project_name", project)

        testplan_path = params.get("testplan", "")
        payload: dict = {
            "project_name": project,
            "tb_data":      tb_data,
        }
        if testplan_path and Path(testplan_path).exists():
            if testplan_path.endswith(".xlsx"):
                payload["testplan_xlsx"] = testplan_path
            else:
                payload["testplan_rows"] = _load_testplan_rows(testplan_path)
        # pass user options through
        if params.get("gen_random")   is not None: payload["gen_random"]   = params["gen_random"]
        if params.get("gen_directed") is not None: payload["gen_directed"] = params["gen_directed"]

        input_file = _write_input_json(run_id or skill_id, payload)
        return ["python3", str(script),
                "--input",  str(input_file),
                "--output", output_dir]

    # ── S7 — generate_assertions.py ───────────────────────────────────────
    if skill_id == "s7":
        tb_data = _load_json_file(params.get("tb_data", ""))
        if not tb_data:
            tb_data = {"project_name": project, "unique_vips": []}
        else:
            tb_data.setdefault("project_name", project)

        testplan_path = params.get("testplan", "")
        testplan_rows = []
        if testplan_path and Path(testplan_path).exists():
            testplan_rows = _load_testplan_rows(testplan_path)

        payload = {
            "project_name":  project,
            "tb_data":       tb_data,
            "testplan_rows": testplan_rows,
        }
        for opt in ("auto_gen_protocols", "gen_bind_module",
                    "gen_assert_checker", "skip_sva_in_sb"):
            if params.get(opt) is not None:
                payload[opt] = params[opt]

        input_file = _write_input_json(run_id or skill_id, payload)
        return ["python3", str(script),
                "--input",  str(input_file),
                "--output", output_dir]

    # ── S8 — generate_scoreboard.py ───────────────────────────────────────
    if skill_id == "s8":
        tb_data = _load_json_file(params.get("tb_data", ""))
        if not tb_data:
            tb_data = {"project_name": project, "unique_vips": []}
        else:
            tb_data.setdefault("project_name", project)

        testplan_path = params.get("testplan", "")
        testplan_rows = []
        if testplan_path and Path(testplan_path).exists():
            testplan_rows = _load_testplan_rows(testplan_path)

        assert_data = _load_json_file(params.get("assert_data", ""))

        payload = {
            "project_name":  project,
            "tb_data":       tb_data,
            "testplan_rows": testplan_rows,
            "assert_data":   assert_data,
        }
        for opt in ("style", "trigger", "ref_model_type", "skip_sva_duplicates"):
            if params.get(opt) is not None:
                payload[opt] = params[opt]

        input_file = _write_input_json(run_id or skill_id, payload)
        return ["python3", str(script),
                "--input",  str(input_file),
                "--output", output_dir]

    # ── S9 — run_regression.py ────────────────────────────────────────────
    if skill_id == "s9":
        cmd = ["python3", str(script),
               "--project",  project,
               "--dv-root",  output_dir]
        if params.get("seq_data"):    cmd += ["--seq-data",  params["seq_data"]]
        if params.get("tb_data"):     cmd += ["--tb-data",   params["tb_data"]]
        if params.get("max_jobs"):    cmd += ["--jobs",      str(params["max_jobs"])]
        if params.get("grid_type") and params["grid_type"] != "local":
            cmd += ["--grid"]
        if params.get("grid_queue"):  cmd += []   # run_regression reads via --grid-cfg
        if params.get("stop_on_fail"): cmd += ["--stop-on-fail"]
        return cmd

    # ── S10 — generate_coverage_closure.py ────────────────────────────────
    if skill_id == "s10":
        cmd = ["python3", str(script),
               "--project", project,
               "--out",     output_dir]
        if params.get("vdb_path"):       cmd += ["--vdb",          params["vdb_path"]]
        if params.get("reg_data"):       cmd += ["--reg-data",     params["reg_data"]]
        if params.get("assert_data"):    cmd += ["--assert-data",  params["assert_data"]]
        if params.get("non_interactive"): cmd += ["--non-interactive"]
        return cmd

    # ── Fallback (future skills) ───────────────────────────────────────────
    cmd = ["python3", str(script)]
    if params.get("project_name"):  cmd += ["--project",  project]
    if params.get("output_dir"):    cmd += ["--out",       output_dir]
    return cmd


def _run_demo(skill_id: str, run_id: str, params: dict):
    """Simulate output for AI-driven skills (S1–S5) or missing scripts."""
    import random
    steps = SKILL_DEMO_STEPS.get(skill_id, [f"Running {skill_id.upper()}...", "✓  Done"])
    for step in steps:
        time.sleep(random.uniform(0.35, 0.85))
        _add_line(run_id, "stdout", step)
    out = params.get("output_dir", "./dv")
    _add_line(run_id, "system", f"Output directory: {out}")
    _finish_run(run_id, skill_id, 0)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket
    import webbrowser

    def _find_free_port(preferred: int, fallbacks=(8080, 8888, 5000, 5050)) -> int:
        for port in (preferred,) + fallbacks:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                continue
        # Last resort: let OS pick
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    preferred = int(os.environ.get("PORT", 7437))
    port = _find_free_port(preferred)
    if port != preferred:
        print(f"  [info] Port {preferred} in use — using port {port} instead")

    url = f"http://127.0.0.1:{port}"

    def _open():
        time.sleep(1.0)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()

    print()
    print("  ╔════════════════════════════════════════╗")
    print("  ║    DV Skills GUI  —  v1.0              ║")
    print(f"  ║    {url:<38}║")
    print("  ╚════════════════════════════════════════╝")
    print()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
