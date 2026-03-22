#!/usr/bin/env python3
"""
run_regression.py — S9 dv-regression parallel runner
Runs UVM tests from a reglist file or keyword match, on grid or locally.

Usage:
  python3 run_regression.py --reglist dv_c_reglist.f --jobs 16 --cov
  python3 run_regression.py --test UART --seeds 10 --jobs 4 --local
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── Import sibling scripts ────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from parse_sim_log import parse_log

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_LOCAL_JOBS = 4
DEFAULT_GRID_JOBS  = 16
POLL_INTERVAL      = 10   # seconds between grid job status polls


# ── Reglist / sequence data parsing ──────────────────────────────────────────

def parse_reglist(reglist_path):
    """Parse a .f reglist file → list of job dicts."""
    jobs = []
    with open(reglist_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entry = {}
            for tok in line.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    entry[k.upper()] = v
                else:
                    entry["PLUSARGS"] = entry.get("PLUSARGS", "") + " " + tok
            if "TEST" not in entry:
                continue
            jobs.append(entry)
    return jobs


def load_seq_data(seq_data_path):
    """Load dv_sequences_data.json → list of test dicts."""
    if not seq_data_path or not os.path.exists(seq_data_path):
        return []
    with open(seq_data_path) as f:
        data = json.load(f)
    return data.get("tests", [])


def filter_by_keyword(seq_tests, keyword):
    """Return test dicts whose class name contains keyword (case-insensitive)."""
    kw = keyword.lower()
    return [t for t in seq_tests if kw in t.get("class", "").lower()
                                  or kw in t.get("file",  "").lower()]


def build_jobs_from_seq(seq_tests, seeds_override=None, seed_config=None):
    """Convert seq_data tests → reglist-style job dicts."""
    seed_cfg = seed_config or {"directed": 1, "random_dvc": 5}
    jobs = []
    for t in seq_tests:
        cls       = t.get("class", "")
        milestone = t.get("milestone", "DV-C")
        plusargs  = " ".join(t.get("plusargs", []))
        is_rand   = cls.lower().endswith("_rand_test") or "_rand_" in cls.lower()
        if seeds_override:
            n_seeds = seeds_override
        elif is_rand:
            key = f"random_{milestone.replace('-','').lower()}"
            n_seeds = seed_cfg.get(key, seed_cfg.get("random_dvc", 5))
        else:
            n_seeds = 1
        jobs.append({
            "TEST":      cls,
            "SEEDS":     str(n_seeds),
            "MILESTONE": milestone,
            "PLUSARGS":  plusargs,
        })
    return jobs


def expand_seeds(jobs, seeds_override=None):
    """
    Expand each job entry into N individual run entries with random seeds.
    Directed tests always get SEED=1.
    """
    expanded = []
    for job in jobs:
        test      = job["TEST"]
        n_seeds   = int(seeds_override or job.get("SEEDS", 1))
        plusargs  = job.get("PLUSARGS", "")
        milestone = job.get("MILESTONE", "DV-C")
        is_rand   = test.lower().endswith("_rand_test") or "_rand_" in test.lower()
        actual_seeds = n_seeds if is_rand else 1
        for i in range(actual_seeds):
            seed = random.randint(1, 2**31 - 1) if is_rand else 1
            expanded.append({
                "test":      test,
                "seed":      seed,
                "plusargs":  plusargs,
                "milestone": milestone,
            })
    return expanded


# ── Sim command builder ───────────────────────────────────────────────────────

def build_sim_cmd(job, dv_root, extra_plusargs=""):
    """Build the VCS ./simv command for one job."""
    sim_dir  = os.path.join(dv_root, "sim")
    simv     = os.path.join(sim_dir, "simv")
    plusargs = job.get("plusargs", "")
    return (
        f"{simv} "
        f"+UVM_TESTNAME={job['test']} "
        f"+ntb_random_seed={job['seed']} "
        f"+UVM_VERBOSITY=UVM_MEDIUM "
        f"{plusargs} {extra_plusargs}"
    ).strip()


# ── Grid submission ───────────────────────────────────────────────────────────

def submit_grid_job(job, sim_cmd, log_path, grid_cfg):
    """Submit one job to the grid. Returns job_id string."""
    template = grid_cfg.get("submit_cmd", "")
    if not template:
        raise RuntimeError("Grid submit_cmd not configured in grid_config.json")
    queue    = grid_cfg.get("default_queue", "normal")
    job_name = f"{job['test']}_s{job['seed']}"
    cmd      = template.format(
        job_name=job_name,
        log_file=log_path,
        cmd=sim_cmd,
        queue=queue,
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Grid submission failed: {result.stderr}")
    # Extract job ID from stdout (common pattern: "Job <12345> is submitted")
    m = re.search(r'\b(\d{4,})\b', result.stdout)
    return m.group(1) if m else result.stdout.strip()


def poll_grid_job(job_id, grid_cfg):
    """Returns True if the grid job is still running."""
    status_tmpl = grid_cfg.get("status_cmd", "")
    if not status_tmpl:
        return False
    cmd    = status_tmpl.format(job_id=job_id)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    # If command exits non-zero or output is empty/contains "not found" → done
    if result.returncode != 0:
        return False
    out = result.stdout.lower()
    return bool(out.strip()) and "not found" not in out and "unknown" not in out


def kill_grid_jobs(job_ids, grid_cfg):
    kill_tmpl = grid_cfg.get("kill_cmd", "")
    if not kill_tmpl:
        return
    for jid in job_ids:
        subprocess.run(kill_tmpl.format(job_id=jid), shell=True,
                       capture_output=True)


# ── Local job runner ──────────────────────────────────────────────────────────

def run_local_job(job, sim_cmd, job_dir):
    """Run one sim job locally. Returns result dict."""
    os.makedirs(job_dir, exist_ok=True)
    log_path = os.path.join(job_dir, "sim.log")
    start    = time.time()
    proc = subprocess.run(
        sim_cmd, shell=True,
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
    )
    elapsed = time.time() - start
    result  = parse_log(log_path)
    result["test"]     = job["test"]
    result["seed"]     = job["seed"]
    result["elapsed"]  = round(elapsed, 2)
    result["exit_code"] = proc.returncode
    if proc.returncode != 0 and result["status"] == "PASS":
        result["status"] = "FAIL"
        result["parse_errors"].append("Non-zero exit code")
    return result


# ── Progress display ──────────────────────────────────────────────────────────

def print_progress(done, total, n_pass, n_fail, n_running):
    bar_w = 30
    filled = int(bar_w * done / total) if total else 0
    bar = "=" * filled + ">" + " " * (bar_w - filled - 1)
    sys.stdout.write(
        f"\r  [{bar}] {done}/{total}  "
        f"PASS={n_pass}  FAIL={n_fail}  RUNNING={n_running}  "
    )
    sys.stdout.flush()


# ── Main regression loop ──────────────────────────────────────────────────────

def run_regression(args):
    # ── Load grid config ──────────────────────────────────────────────────────
    grid_cfg = {}
    if args.grid_cfg and os.path.exists(args.grid_cfg):
        with open(args.grid_cfg) as f:
            grid_cfg = json.load(f)
    use_grid = args.grid and grid_cfg.get("grid_type", "local") != "local"
    max_jobs = args.jobs or (DEFAULT_GRID_JOBS if use_grid else DEFAULT_LOCAL_JOBS)

    # ── Build job list ────────────────────────────────────────────────────────
    if args.reglist:
        raw_jobs = parse_reglist(args.reglist)
    elif args.test:
        seq_tests = load_seq_data(args.seq_data)
        if not seq_tests:
            print(f"ERROR: --test requires --seq-data with a valid dv_sequences_data.json")
            sys.exit(1)
        matched = filter_by_keyword(seq_tests, args.test)
        if not matched:
            print(f"No tests found matching keyword '{args.test}'")
            sys.exit(0)
        print(f"  Keyword '{args.test}' matched {len(matched)} test(s)")
        raw_jobs = build_jobs_from_seq(matched, seeds_override=args.seeds)
    else:
        print("ERROR: Provide --reglist or --test")
        sys.exit(1)

    expanded = expand_seeds(raw_jobs, seeds_override=args.seeds)
    total    = len(expanded)

    # ── Setup results directory ───────────────────────────────────────────────
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join(args.results or
                               os.path.join(args.dv_root, "sim", "results"), ts)
    os.makedirs(results_dir, exist_ok=True)

    proj = args.project or "project"
    print(f"""
============================================================
  Regression Run: {proj}
  Reglist      : {args.reglist or ('keyword: ' + args.test)}
  Total jobs   : {total}
  Mode         : {'Grid (' + grid_cfg.get('grid_type','?') + ')' if use_grid else 'Local'}
  Max parallel : {max_jobs}
  Results dir  : {results_dir}
============================================================""")

    all_results  = []
    active_grid  = {}  # job_id → (job, job_dir)
    n_pass = n_fail = 0
    stop   = False

    if use_grid:
        # ── Grid execution loop ───────────────────────────────────────────────
        submitted = 0
        for job in expanded:
            if stop:
                break
            job_tag  = f"{job['test']}_s{job['seed']}"
            job_dir  = os.path.join(results_dir, job_tag)
            os.makedirs(job_dir, exist_ok=True)
            log_path = os.path.join(job_dir, "sim.log")
            sim_cmd  = build_sim_cmd(job, args.dv_root)
            try:
                jid = submit_grid_job(job, sim_cmd, log_path, grid_cfg)
                active_grid[jid] = (job, job_dir)
                submitted += 1
                # Throttle to max_jobs
                while len(active_grid) >= max_jobs:
                    time.sleep(grid_cfg.get("poll_interval_sec", POLL_INTERVAL))
                    done_ids = [jid for jid in active_grid
                                if not poll_grid_job(jid, grid_cfg)]
                    for did in done_ids:
                        j, jdir = active_grid.pop(did)
                        lp = os.path.join(jdir, "sim.log")
                        r  = parse_log(lp)
                        r["test"] = j["test"]; r["seed"] = j["seed"]
                        _save_result(r, jdir)
                        all_results.append(r)
                        if r["status"] == "PASS": n_pass += 1
                        else:                     n_fail += 1
                        print_progress(len(all_results), total, n_pass, n_fail,
                                       len(active_grid))
            except Exception as e:
                print(f"\n  [ERROR] Failed to submit {job['test']}: {e}")

        # Wait for remaining grid jobs
        while active_grid:
            time.sleep(grid_cfg.get("poll_interval_sec", POLL_INTERVAL))
            done_ids = [jid for jid in active_grid
                        if not poll_grid_job(jid, grid_cfg)]
            for did in done_ids:
                j, jdir = active_grid.pop(did)
                lp = os.path.join(jdir, "sim.log")
                r  = parse_log(lp)
                r["test"] = j["test"]; r["seed"] = j["seed"]
                _save_result(r, jdir)
                all_results.append(r)
                if r["status"] == "PASS": n_pass += 1
                else:                     n_fail += 1
                print_progress(len(all_results), total, n_pass, n_fail, 0)

    else:
        # ── Local parallel execution ──────────────────────────────────────────
        try:
            with ThreadPoolExecutor(max_workers=max_jobs) as pool:
                futures = {}
                for job in expanded:
                    job_tag = f"{job['test']}_s{job['seed']}"
                    job_dir = os.path.join(results_dir, job_tag)
                    sim_cmd = build_sim_cmd(job, args.dv_root)
                    fut     = pool.submit(run_local_job, job, sim_cmd, job_dir)
                    futures[fut] = (job, job_dir)

                for fut in as_completed(futures):
                    job, job_dir = futures[fut]
                    try:
                        r = fut.result()
                    except Exception as e:
                        r = {"test": job["test"], "seed": job["seed"],
                             "status": "FAIL", "uvm_error": 0, "uvm_fatal": 0,
                             "chk_fails": [], "parse_errors": [str(e)]}
                    _save_result(r, job_dir)
                    all_results.append(r)
                    if r["status"] == "PASS": n_pass += 1
                    else:                     n_fail += 1
                    print_progress(len(all_results), total, n_pass, n_fail,
                                   total - len(all_results))
                    if args.stop_on_fail and n_fail > 0:
                        stop = True
                        pool.shutdown(wait=False)
                        break
        except KeyboardInterrupt:
            print("\n  [INTERRUPTED] Killing remaining jobs...")

    print()  # newline after progress bar

    # ── Save master results ───────────────────────────────────────────────────
    summary_json = os.path.join(results_dir, "results.json")
    with open(summary_json, "w") as f:
        json.dump(all_results, f, indent=2)

    # ── Print failing tests ───────────────────────────────────────────────────
    failures = [r for r in all_results if r["status"] != "PASS"]
    if failures:
        print("\n  FAILED TESTS:")
        for r in failures:
            tag = f"{r['test']}_s{r['seed']}"
            log = os.path.join(results_dir, tag, "sim.log")
            print(f"    {tag:<50} → {log}")

    # ── HTML report ───────────────────────────────────────────────────────────
    try:
        from gen_regression_report import generate_report
        rpt_path = os.path.join(results_dir, "regression_summary.html")
        generate_report(all_results, rpt_path, proj, total)
        print(f"\n  Report: {rpt_path}")
    except ImportError:
        print("  [WARN] gen_regression_report not found — skipping HTML report")

    # ── Coverage merge ────────────────────────────────────────────────────────
    if args.cov:
        try:
            from merge_coverage import merge_coverage
            cov_out = os.path.join(results_dir, "coverage")
            merge_coverage(results_dir, cov_out)
        except ImportError:
            print("  [WARN] merge_coverage not found — skipping coverage merge")

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"""
============================================================
  Regression Complete: {proj}
  Total: {total}  PASS: {n_pass}  FAIL: {n_fail}
  Pass rate: {100*n_pass/total:.1f}%
============================================================""")

    return 0 if n_fail == 0 else 1


def _save_result(result, job_dir):
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, "result.json"), "w") as f:
        json.dump(result, f, indent=2)


# ── Argument parsing ──────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="S9 regression runner")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--reglist",   help="Reglist .f file")
    g.add_argument("--test",      help="Keyword to match test names")
    p.add_argument("--seeds",     type=int, default=None,
                   help="Override SEEDS for all tests")
    p.add_argument("--jobs",      type=int, default=None,
                   help="Max parallel jobs")
    p.add_argument("--grid",      action="store_true", help="Submit to grid")
    p.add_argument("--local",     action="store_true", help="Force local run")
    p.add_argument("--cov",       action="store_true", help="Merge coverage after run")
    p.add_argument("--stop-on-fail", action="store_true")
    p.add_argument("--results",   default=None,        help="Results directory")
    p.add_argument("--project",   default="project",   help="Project name")
    p.add_argument("--dv-root",   default=".",          help="dv/ root directory")
    p.add_argument("--tb-data",   default=None)
    p.add_argument("--seq-data",  default=None,
                   help="dv_sequences_data.json (required for --test)")
    p.add_argument("--grid-cfg",  default=None,
                   help="grid_config.json path")
    args = p.parse_args()

    if args.local:
        args.grid = False

    sys.exit(run_regression(args))


if __name__ == "__main__":
    main()
