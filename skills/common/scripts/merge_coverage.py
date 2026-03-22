#!/usr/bin/env python3
"""
merge_coverage.py — DV Skills VCS Coverage Merge + Verdi Launch
Merges per-test VDB databases with `urg`, generates coverage reports,
and optionally launches Verdi for interactive coverage review.

Usage:
    from merge_coverage import merge_coverage
    merge_coverage(vdb_dirs, output_dir, config)

    python3 merge_coverage.py --vdb-dir sim_results/ --out cov_merge/
    python3 merge_coverage.py --vdb-dir sim_results/ --out cov_merge/ --verdi
    python3 merge_coverage.py --vdb-list vdbs.txt   --out cov_merge/
"""

import subprocess
import sys
import os
import re
import json
import glob
import shutil
import argparse
from pathlib import Path
from datetime import datetime


# ── URG invocation ───────────────────────────────────────────────────────────────

def find_vdb_dirs(search_root: str) -> list:
    """
    Recursively find all *.vdb directories under search_root.
    Returns sorted list of paths.
    """
    pattern = os.path.join(search_root, "**", "*.vdb")
    found = glob.glob(pattern, recursive=True)
    # Also check for simv.vdb or cm.vdb at top level
    top_pattern = os.path.join(search_root, "*.vdb")
    found += glob.glob(top_pattern)
    return sorted(set(found))


def run_urg_merge(vdb_dirs: list, output_dir: str,
                  full64: bool = True,
                  report_format: str = "both",
                  extra_args: list = None) -> dict:
    """
    Run `urg` to merge VDB files and generate coverage report.

    Args:
        vdb_dirs:      List of *.vdb directory paths
        output_dir:    Where to write merged DB + reports
        full64:        Use -full64 flag
        report_format: "text" | "html" | "both"
        extra_args:    Additional urg flags

    Returns dict:
        {
            "status":       "PASS" | "FAIL",
            "returncode":   int,
            "merged_vdb":   str,
            "report_dir":   str,
            "coverage_pct": float | None,
            "cmd":          str,
            "stdout":       str,
            "stderr":       str,
        }
    """
    result = {
        "status":       "FAIL",
        "returncode":   -1,
        "merged_vdb":   "",
        "report_dir":   "",
        "coverage_pct": None,
        "cmd":          "",
        "stdout":       "",
        "stderr":       "",
    }

    if not vdb_dirs:
        result["stderr"] = "No VDB directories provided."
        return result

    # Check urg is available
    urg_path = shutil.which("urg")
    if urg_path is None:
        result["stderr"] = ("'urg' not found in PATH. "
                            "Ensure VCS is installed and $VCS_HOME/bin is in PATH.")
        return result

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    merged_vdb = str(out / "merged.vdb")
    report_dir = str(out / "urgReport")

    # Build command
    cmd = ["urg"]
    if full64:
        cmd.append("-full64")
    for vdb in vdb_dirs:
        cmd += ["-dir", vdb]
    cmd += ["-dbname", merged_vdb]
    cmd += ["-report", report_dir]

    if report_format in ("html", "both"):
        cmd += ["-format", "html"]
    if report_format == "both":
        # Run text report separately after html
        pass

    if extra_args:
        cmd.extend(extra_args)

    result["cmd"] = " ".join(cmd)

    print(f"  Running: {result['cmd']}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    result["returncode"] = proc.returncode
    result["stdout"]     = proc.stdout
    result["stderr"]     = proc.stderr
    result["merged_vdb"] = merged_vdb
    result["report_dir"] = report_dir

    if proc.returncode != 0:
        result["status"] = "FAIL"
        return result

    # If "both" requested, run text report as well
    if report_format == "both":
        text_dir = str(out / "urgReport_text")
        cmd_text = ["urg"]
        if full64:
            cmd_text.append("-full64")
        cmd_text += ["-dir", merged_vdb, "-report", text_dir, "-format", "text"]
        subprocess.run(cmd_text, capture_output=True)

    # ── Parse coverage percentage from stdout ─────────────────────────
    cov_pct = _parse_coverage_pct(proc.stdout + proc.stderr)
    result["coverage_pct"] = cov_pct
    result["status"] = "PASS"
    return result


def _parse_coverage_pct(output: str) -> float | None:
    """
    Extract total coverage percentage from urg output.
    Looks for patterns like:
      Overall coverage: 87.32%
      Total Coverage: 87.32%
      coverage = 87.32%
    """
    patterns = [
        r"Overall\s+[Cc]overage\s*[=:]\s*([\d.]+)\s*%",
        r"Total\s+[Cc]overage\s*[=:]\s*([\d.]+)\s*%",
        r"[Cc]overage\s*[=:]\s*([\d.]+)\s*%",
        r"([\d.]+)\s*%\s+coverage",
    ]
    for pat in patterns:
        m = re.search(pat, output)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


# ── Verdi launch ─────────────────────────────────────────────────────────────────

def launch_verdi(merged_vdb: str, extra_args: list = None) -> subprocess.Popen | None:
    """
    Launch Verdi for interactive coverage review.
    Returns the Popen handle or None if Verdi not found.
    """
    verdi_path = shutil.which("verdi")
    if verdi_path is None:
        print("  ⚠  'verdi' not found in PATH. Set $VERDI_HOME/bin in PATH.")
        return None

    cmd = ["verdi", "-cov", "-covdir", merged_vdb]
    if extra_args:
        cmd.extend(extra_args)

    print(f"  Launching Verdi: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd)
        return proc
    except OSError as exc:
        print(f"  ✗ Failed to launch Verdi: {exc}")
        return None


# ── Coverage report summary ───────────────────────────────────────────────────────

def read_coverage_summary(report_dir: str) -> dict:
    """
    Read coverage summary from urg text report if available.
    Returns dict with metric totals:
    {
        "line":       float | None,
        "toggle":     float | None,
        "branch":     float | None,
        "expression": float | None,
        "fsm":        float | None,
        "functional": float | None,
        "overall":    float | None,
    }
    """
    summary = {k: None for k in ("line","toggle","branch","expression","fsm","functional","overall")}

    # Try urgReport_text/dashboard.txt or similar
    candidates = [
        os.path.join(report_dir, "dashboard.txt"),
        os.path.join(report_dir + "_text", "dashboard.txt"),
        os.path.join(report_dir, "coverage.txt"),
        os.path.join(os.path.dirname(report_dir), "urgReport_text", "dashboard.txt"),
    ]
    text_file = None
    for c in candidates:
        if os.path.isfile(c):
            text_file = c
            break

    if text_file is None:
        return summary

    try:
        content = Path(text_file).read_text(errors="replace")
    except OSError:
        return summary

    _map = {
        "line":       r"Line\s+Coverage[^%]*?([\d.]+)\s*%",
        "toggle":     r"Toggle\s+Coverage[^%]*?([\d.]+)\s*%",
        "branch":     r"Branch\s+Coverage[^%]*?([\d.]+)\s*%",
        "expression": r"Expression\s+Coverage[^%]*?([\d.]+)\s*%",
        "fsm":        r"FSM\s+Coverage[^%]*?([\d.]+)\s*%",
        "functional": r"Functional\s+Coverage[^%]*?([\d.]+)\s*%",
        "overall":    r"Overall[^%]*?([\d.]+)\s*%",
    }
    for key, pat in _map.items():
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            try:
                summary[key] = float(m.group(1))
            except ValueError:
                pass

    return summary


# ── Write merge result JSON ───────────────────────────────────────────────────────

def write_merge_result(result: dict, coverage_summary: dict, output_dir: str):
    """Write dv_coverage_merge.json to output_dir."""
    data = {
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status":          result.get("status"),
        "merged_vdb":      result.get("merged_vdb"),
        "report_dir":      result.get("report_dir"),
        "coverage_pct":    result.get("coverage_pct"),
        "coverage_detail": coverage_summary,
        "urg_cmd":         result.get("cmd"),
        "returncode":      result.get("returncode"),
    }
    out_file = os.path.join(output_dir, "dv_coverage_merge.json")
    with open(out_file, "w") as fh:
        json.dump(data, fh, indent=2)
    return out_file


# ── High-level entry point ───────────────────────────────────────────────────────

def merge_coverage(vdb_dirs_or_root,
                   output_dir: str,
                   config: dict = None,
                   launch_verdi_after: bool = False) -> dict:
    """
    High-level coverage merge function called by run_regression.py.

    Args:
        vdb_dirs_or_root: Either a list of *.vdb paths OR a single root directory
                          to search for *.vdb dirs recursively
        output_dir:       Where to write merged DB and reports
        config:           Optional dict with keys:
                          - format: "html" | "text" | "both" (default "both")
                          - full64: bool (default True)
                          - extra_urg_args: list of extra urg flags
                          - verdi_args: list of extra verdi flags
        launch_verdi_after: If True, launch Verdi after merge

    Returns:
        dict with merge status, paths, and coverage percentages
    """
    if config is None:
        config = {}

    # Resolve VDB directories
    if isinstance(vdb_dirs_or_root, str):
        vdb_dirs = find_vdb_dirs(vdb_dirs_or_root)
        if not vdb_dirs:
            # Also check if it's directly a vdb dir
            if vdb_dirs_or_root.endswith(".vdb") and os.path.isdir(vdb_dirs_or_root):
                vdb_dirs = [vdb_dirs_or_root]
    else:
        vdb_dirs = list(vdb_dirs_or_root)

    print(f"\n  Coverage Merge")
    print(f"  {'─'*50}")
    print(f"  Found {len(vdb_dirs)} VDB database(s)")
    for v in vdb_dirs[:10]:
        print(f"    {v}")
    if len(vdb_dirs) > 10:
        print(f"    ... {len(vdb_dirs)-10} more")

    # Run merge
    merge_result = run_urg_merge(
        vdb_dirs       = vdb_dirs,
        output_dir     = output_dir,
        full64         = config.get("full64", True),
        report_format  = config.get("format", "both"),
        extra_args     = config.get("extra_urg_args"),
    )

    # Read detailed coverage summary from text report
    cov_summary = read_coverage_summary(merge_result.get("report_dir", ""))

    # Print results
    if merge_result["status"] == "PASS":
        pct = merge_result.get("coverage_pct")
        print(f"\n  ✓  Coverage merge completed")
        if pct is not None:
            print(f"     Overall Coverage : {pct}%")
        if cov_summary.get("line")    is not None: print(f"     Line             : {cov_summary['line']}%")
        if cov_summary.get("toggle")  is not None: print(f"     Toggle           : {cov_summary['toggle']}%")
        if cov_summary.get("branch")  is not None: print(f"     Branch           : {cov_summary['branch']}%")
        if cov_summary.get("functional") is not None: print(f"     Functional       : {cov_summary['functional']}%")
        print(f"     Merged VDB       : {merge_result['merged_vdb']}")
        print(f"     HTML Report      : {merge_result['report_dir']}")
    else:
        print(f"\n  ✗  Coverage merge FAILED (rc={merge_result['returncode']})")
        if merge_result.get("stderr"):
            for line in merge_result["stderr"].splitlines()[:10]:
                print(f"     {line}")

    # Write JSON summary
    json_path = write_merge_result(merge_result, cov_summary, output_dir)
    print(f"     JSON summary     : {json_path}")

    # Launch Verdi if requested
    if launch_verdi_after and merge_result["status"] == "PASS":
        launch_verdi(merge_result["merged_vdb"],
                     extra_args=config.get("verdi_args"))

    return {
        "status":       merge_result["status"],
        "merged_vdb":   merge_result["merged_vdb"],
        "report_dir":   merge_result["report_dir"],
        "coverage_pct": merge_result.get("coverage_pct"),
        "coverage_detail": cov_summary,
        "json_path":    json_path,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Merge VCS coverage databases and generate report")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--vdb-dir",  metavar="DIR",
                     help="Root directory to search for *.vdb databases recursively")
    src.add_argument("--vdb-list", metavar="FILE",
                     help="Text file with one *.vdb path per line")
    src.add_argument("--vdb",      metavar="PATH", nargs="+",
                     help="Explicit list of *.vdb paths")
    parser.add_argument("--out",    required=True,  help="Output directory for merged DB + report")
    parser.add_argument("--format", default="both", choices=["html","text","both"],
                        help="Report format (default: both)")
    parser.add_argument("--verdi",  action="store_true", help="Launch Verdi after merge")
    parser.add_argument("--no-full64", action="store_true", help="Omit -full64 flag")
    args = parser.parse_args()

    # Resolve VDB list
    if args.vdb_dir:
        vdb_dirs = find_vdb_dirs(args.vdb_dir)
    elif args.vdb_list:
        vdb_dirs = [l.strip() for l in open(args.vdb_list) if l.strip()]
    else:
        vdb_dirs = args.vdb

    if not vdb_dirs:
        print("  ✗ No VDB directories found.")
        sys.exit(1)

    config = {
        "format": args.format,
        "full64": not args.no_full64,
    }

    result = merge_coverage(
        vdb_dirs_or_root   = vdb_dirs,
        output_dir         = args.out,
        config             = config,
        launch_verdi_after = args.verdi,
    )

    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
