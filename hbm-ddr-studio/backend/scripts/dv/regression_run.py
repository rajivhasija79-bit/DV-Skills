#!/usr/bin/env python3
"""Mock regression runner. Demonstrates progress + mid-run prompt.

REPLACE: placeholder. Plug in your real LSF/Slurm/Jenkins kicker.
Contract: JSON line on stdin → progress on stdout → exit code. Use the
##HDS-PROMPT## marker (see prompt() below) to ask the user mid-run.
See docs/INTEGRATION.md.

If config['ask_token'] is true, the script prints a HDS-PROMPT marker and waits
for a JSON line on stdin with the response, then continues.
"""
from __future__ import annotations
import json
import random
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
    suite = cfg.get("suite", "smoke")
    seeds = int(cfg.get("seeds", 4))
    sim = cfg.get("simulator", "VCS")
    jobs = int(cfg.get("jobs", 4))
    out(f"[regress] suite={suite} seeds={seeds} sim={sim} jobs={jobs}")

    if cfg.get("ask_token"):
        out("[regress] queue is gated; requesting token from user")
        ans = prompt({"id": "queue_token", "label": "LSF queue token", "type": "password", "required": True})
        if not ans.get("value"):
            out("[regress] no token given, aborting")
            return 2
        out("[regress] token accepted, proceeding")

    total = seeds * 5
    pass_count = 0
    fail_count = 0
    for i in range(1, total + 1):
        ok = random.random() > 0.1
        pass_count += int(ok)
        fail_count += int(not ok)
        out(f"[{i}/{total}] seed={i} {'PASS' if ok else 'FAIL'}")
        time.sleep(0.15)
    out(f"[regress] done: pass={pass_count} fail={fail_count}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
