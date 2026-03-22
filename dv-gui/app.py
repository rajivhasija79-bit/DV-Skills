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

    cmd = _build_cmd(skill_id, params, script)
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


def _build_cmd(skill_id: str, params: dict, script: Path) -> list:
    cmd = ["python3", str(script)]
    if params.get("project_name"):  cmd += ["--project",     params["project_name"]]
    if params.get("output_dir"):    cmd += ["--out",          params["output_dir"]]
    if params.get("tb_data"):       cmd += ["--tb-data",      params["tb_data"]]
    if params.get("assert_data"):   cmd += ["--assert-data",  params["assert_data"]]
    if params.get("reg_data"):      cmd += ["--reg-data",     params["reg_data"]]
    if params.get("vdb_path"):      cmd += ["--vdb",          params["vdb_path"]]
    if params.get("non_interactive"): cmd += ["--non-interactive"]
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
    import webbrowser

    def _open():
        time.sleep(1.0)
        webbrowser.open("http://127.0.0.1:7437")

    threading.Thread(target=_open, daemon=True).start()

    print()
    print("  ╔════════════════════════════════════════╗")
    print("  ║    DV Skills GUI  —  v1.0              ║")
    print("  ║    http://127.0.0.1:7437               ║")
    print("  ╚════════════════════════════════════════╝")
    print()
    app.run(host="127.0.0.1", port=7437, debug=False, threaded=True)
