#!/usr/bin/env python3
"""
parse_sim_log.py — DV Skills VCS simulation log parser
Parses a VCS sim.log for UVM_FATAL/ERROR counts, [PASS]/[FAIL] CHK_ID messages,
and simulation completion status.

Usage:
    from parse_sim_log import parse_log
    result = parse_log("/path/to/sim.log")

    python3 parse_sim_log.py sim.log          # CLI usage
    python3 parse_sim_log.py sim.log --json   # output JSON
"""

import re
import json
import sys
import os
from pathlib import Path

# ── Regex patterns ──────────────────────────────────────────────────────────────

# UVM severity lines
_RE_UVM_FATAL   = re.compile(r"UVM_FATAL\s*[@:]?\s*(\d+)")
_RE_UVM_ERROR   = re.compile(r"UVM_ERROR\s*[@:]?\s*(\d+)")
_RE_UVM_WARNING = re.compile(r"UVM_WARNING\s*[@:]?\s*(\d+)")
_RE_UVM_INFO    = re.compile(r"UVM_INFO\s*[@:]?\s*(\d+)")

# UVM summary block (last report)
_RE_SUMMARY_FATAL   = re.compile(r"UVM_FATAL\s*:\s*(\d+)")
_RE_SUMMARY_ERROR   = re.compile(r"UVM_ERROR\s*:\s*(\d+)")
_RE_SUMMARY_WARNING = re.compile(r"UVM_WARNING\s*:\s*(\d+)")

# CHK_ID pass/fail messages
# Matches: [PASS] CHK_UART_TX_001 - message text
#          [FAIL] CHK_UART_TX_001 - message text
_RE_CHK_PASS = re.compile(r"\[PASS\]\s+(CHK_[A-Z0-9_]+)(.*)")
_RE_CHK_FAIL = re.compile(r"\[FAIL\]\s+(CHK_[A-Z0-9_]+)(.*)")
_RE_CHK_COV  = re.compile(r"\[COV\]\s+(CHK_[A-Z0-9_]+)(.*)")

# Scoreboard report lines
_RE_SB_PASS = re.compile(r"\[PASS\]\s+All scoreboard checks")
_RE_SB_FAIL = re.compile(r"\[FAIL\]\s+Scoreboard")

# Simulation completion
_RE_SIM_END      = re.compile(r"\$finish")
_RE_SIM_KILLED   = re.compile(r"killed|KILLED|signal|SIGSEGV|SIGABRT", re.IGNORECASE)
_RE_SIM_TIMEOUT  = re.compile(r"timeout|TIMEOUT|simulation time limit", re.IGNORECASE)

# VCS compile/elab errors (in sim log occasionally)
_RE_VCS_ERROR = re.compile(r"^Error-\[", re.MULTILINE)

# Seed line
_RE_SEED = re.compile(r"ntb_random_seed\s*[=:]\s*(\d+)")

# Test name
_RE_TEST_NAME = re.compile(r"UVM_TESTNAME\s*[=:]?\s*(\S+)")

# Time stamp for last CHK message
_RE_SIMTIME = re.compile(r"@\s*(\d+(?:\.\d+)?)\s*(ns|us|ps|fs)?")


# ── Core parser ─────────────────────────────────────────────────────────────────

def parse_log(log_path: str) -> dict:
    """
    Parse a VCS simulation log file.

    Returns a dict:
    {
        "log_path":     str,
        "status":       "PASS" | "FAIL" | "TIMEOUT" | "KILLED" | "INCOMPLETE",
        "test_name":    str | None,
        "seed":         int | None,
        "uvm_fatal":    int,
        "uvm_error":    int,
        "uvm_warning":  int,
        "uvm_info":     int,
        "chk_pass":     { "CHK_ID": count, ... },
        "chk_fail":     { "CHK_ID": count, ... },
        "chk_cov":      { "CHK_ID": count, ... },
        "chk_pass_total": int,
        "chk_fail_total": int,
        "fail_messages": [ {"chk_id": str, "message": str, "line": int}, ... ],
        "sim_finished": bool,
        "error_details": [ str, ... ],
    }
    """
    result = {
        "log_path":       log_path,
        "status":         "INCOMPLETE",
        "test_name":      None,
        "seed":           None,
        "uvm_fatal":      0,
        "uvm_error":      0,
        "uvm_warning":    0,
        "uvm_info":       0,
        "chk_pass":       {},
        "chk_fail":       {},
        "chk_cov":        {},
        "chk_pass_total": 0,
        "chk_fail_total": 0,
        "fail_messages":  [],
        "sim_finished":   False,
        "error_details":  [],
    }

    if not os.path.isfile(log_path):
        result["status"] = "INCOMPLETE"
        result["error_details"].append(f"Log file not found: {log_path}")
        return result

    in_summary = False
    summary_fatal   = None
    summary_error   = None
    summary_warning = None

    try:
        with open(log_path, "r", errors="replace") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.rstrip()

                # ── test name + seed from plusargs ──────────────────────────
                if result["test_name"] is None:
                    m = _RE_TEST_NAME.search(line)
                    if m:
                        result["test_name"] = m.group(1).strip()

                if result["seed"] is None:
                    m = _RE_SEED.search(line)
                    if m:
                        result["seed"] = int(m.group(1))

                # ── CHK_ID pass/fail/cover ──────────────────────────────────
                m = _RE_CHK_PASS.search(line)
                if m:
                    chk_id = m.group(1)
                    result["chk_pass"][chk_id] = result["chk_pass"].get(chk_id, 0) + 1
                    result["chk_pass_total"] += 1

                m = _RE_CHK_FAIL.search(line)
                if m:
                    chk_id  = m.group(1)
                    msg_txt = m.group(2).strip(" -")
                    result["chk_fail"][chk_id] = result["chk_fail"].get(chk_id, 0) + 1
                    result["chk_fail_total"] += 1
                    result["fail_messages"].append({
                        "chk_id":  chk_id,
                        "message": msg_txt,
                        "line":    lineno,
                    })

                m = _RE_CHK_COV.search(line)
                if m:
                    chk_id = m.group(1)
                    result["chk_cov"][chk_id] = result["chk_cov"].get(chk_id, 0) + 1

                # ── UVM summary block detection ─────────────────────────────
                if "--- UVM Report Summary ---" in line or "UVM Report Summary" in line:
                    in_summary = True

                if in_summary:
                    m = _RE_SUMMARY_FATAL.search(line)
                    if m:
                        summary_fatal = int(m.group(1))
                    m = _RE_SUMMARY_ERROR.search(line)
                    if m:
                        summary_error = int(m.group(1))
                    m = _RE_SUMMARY_WARNING.search(line)
                    if m:
                        summary_warning = int(m.group(1))

                # ── Sim finish ──────────────────────────────────────────────
                if _RE_SIM_END.search(line):
                    result["sim_finished"] = True

                # ── Timeout / killed ────────────────────────────────────────
                if _RE_SIM_TIMEOUT.search(line):
                    result["status"] = "TIMEOUT"
                if _RE_SIM_KILLED.search(line):
                    result["status"] = "KILLED"

    except OSError as exc:
        result["error_details"].append(str(exc))
        return result

    # ── Use summary block counts if available ───────────────────────────────
    if summary_fatal   is not None: result["uvm_fatal"]   = summary_fatal
    if summary_error   is not None: result["uvm_error"]   = summary_error
    if summary_warning is not None: result["uvm_warning"] = summary_warning

    # ── Determine final status ───────────────────────────────────────────────
    if result["status"] not in ("TIMEOUT", "KILLED"):
        if not result["sim_finished"]:
            result["status"] = "INCOMPLETE"
        elif result["uvm_fatal"] > 0:
            result["status"] = "FAIL"
        elif result["uvm_error"] > 0:
            result["status"] = "FAIL"
        elif result["chk_fail_total"] > 0:
            result["status"] = "FAIL"
        else:
            result["status"] = "PASS"

    return result


# ── Batch parser ─────────────────────────────────────────────────────────────────

def parse_logs(log_paths: list) -> list:
    """Parse a list of log file paths. Returns list of result dicts."""
    return [parse_log(p) for p in log_paths]


def summarise_results(results: list) -> dict:
    """
    Aggregate a list of parse_log() results into a summary dict:
    {
        "total": int,
        "pass":  int,
        "fail":  int,
        "timeout": int,
        "killed":  int,
        "incomplete": int,
        "pass_rate": float,
        "total_uvm_errors": int,
        "total_uvm_fatals": int,
        "unique_chk_ids_failed": list[str],
    }
    """
    summary = {
        "total":      len(results),
        "pass":       0,
        "fail":       0,
        "timeout":    0,
        "killed":     0,
        "incomplete": 0,
        "pass_rate":  0.0,
        "total_uvm_errors": 0,
        "total_uvm_fatals": 0,
        "unique_chk_ids_failed": [],
    }
    all_failed_chk = set()
    for r in results:
        status = r.get("status", "INCOMPLETE").upper()
        if   status == "PASS":       summary["pass"]       += 1
        elif status == "FAIL":       summary["fail"]       += 1
        elif status == "TIMEOUT":    summary["timeout"]    += 1
        elif status == "KILLED":     summary["killed"]     += 1
        else:                        summary["incomplete"] += 1
        summary["total_uvm_errors"] += r.get("uvm_error", 0)
        summary["total_uvm_fatals"] += r.get("uvm_fatal", 0)
        all_failed_chk.update(r.get("chk_fail", {}).keys())

    if summary["total"] > 0:
        summary["pass_rate"] = round(100.0 * summary["pass"] / summary["total"], 1)
    summary["unique_chk_ids_failed"] = sorted(all_failed_chk)
    return summary


# ── CLI ──────────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse VCS simulation log(s)")
    parser.add_argument("logs", nargs="+", help="Log file(s) to parse")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--summary", action="store_true", help="Print batch summary only")
    args = parser.parse_args()

    results = parse_logs(args.logs)

    if args.json:
        if len(results) == 1:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps(results, indent=2))
        return

    if args.summary:
        s = summarise_results(results)
        print(f"\n  Regression Summary")
        print(f"  {'─'*40}")
        print(f"  Total      : {s['total']}")
        print(f"  PASS       : {s['pass']}")
        print(f"  FAIL       : {s['fail']}")
        print(f"  TIMEOUT    : {s['timeout']}")
        print(f"  KILLED     : {s['killed']}")
        print(f"  INCOMPLETE : {s['incomplete']}")
        print(f"  Pass Rate  : {s['pass_rate']}%")
        if s["unique_chk_ids_failed"]:
            print(f"\n  Failed CHK_IDs:")
            for c in s["unique_chk_ids_failed"]:
                print(f"    ✗  {c}")
        print()
        return

    for r in results:
        status_icon = {"PASS": "✓", "FAIL": "✗", "TIMEOUT": "⏱", "KILLED": "✗", "INCOMPLETE": "?"}.get(r["status"], "?")
        print(f"\n  {status_icon}  [{r['status']}]  {r['log_path']}")
        print(f"     Test : {r['test_name'] or 'unknown'}")
        print(f"     Seed : {r['seed'] or 'unknown'}")
        print(f"     UVM_FATAL={r['uvm_fatal']}  UVM_ERROR={r['uvm_error']}  UVM_WARNING={r['uvm_warning']}")
        print(f"     CHK PASS={r['chk_pass_total']}  CHK FAIL={r['chk_fail_total']}")
        if r["fail_messages"]:
            print(f"     Failed checks:")
            for fm in r["fail_messages"][:10]:
                print(f"       ✗ {fm['chk_id']} (line {fm['line']}): {fm['message'][:80]}")
            if len(r["fail_messages"]) > 10:
                print(f"       ... {len(r['fail_messages'])-10} more")


if __name__ == "__main__":
    main()
