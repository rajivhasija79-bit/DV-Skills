#!/usr/bin/env python3
"""Demo debug task — wraps an rtl-sim-debug-style flow with mid-run prompt."""
from __future__ import annotations
import json
import sys
import time


def out(msg: str) -> None:
    print(msg, flush=True)


def prompt(spec: dict) -> dict:
    out("##HDS-PROMPT## " + json.dumps(spec))
    line = sys.stdin.readline()
    return json.loads(line or "{}")


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    out(f"[debug] sim_log={cfg.get('sim_log')} mode={cfg.get('mode')} subsystem={cfg.get('subsystem')}")
    out("[1/6] Reading log")
    time.sleep(0.4)
    out("[2/6] Classifying failure (TB vs RTL vs config vs env)")
    time.sleep(0.4)
    out("[3/6] Searching JIRA + regression history for similar")
    time.sleep(0.4)
    if cfg.get("mode") == "Deep":
        out("[debug] Deep mode requires a JIRA token to query history")
        ans = prompt({"id": "jira_token", "label": "JIRA token", "type": "password", "required": True})
        if not ans.get("value"):
            out("[debug] no token, falling back to triage")
        else:
            out("[debug] token accepted, querying JIRA")
    out("[4/6] Pulling waveform driver trace")
    time.sleep(0.4)
    out("[5/6] Forming RCA hypothesis")
    time.sleep(0.4)
    out("[6/6] Emitting writeup.md")
    out("[debug] done — likely root cause: refresh-in-flight race in ddr_ctrl::refresh_fsm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
