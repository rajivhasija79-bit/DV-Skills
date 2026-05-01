#!/usr/bin/env python3
"""Demo testplan generator.

REPLACE: placeholder. Plug in your real testplan generator.
Contract: JSON line on stdin (form fields) → progress on stdout → exit code.
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
import sys
import time


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    print(f"[testplan] spec={cfg.get('spec_path')} milestone={cfg.get('milestone')} cov={cfg.get('cov_target')}%", flush=True)
    scope = cfg.get("feature_scope") or ["Address", "Data", "Control"]
    print(f"[testplan] scope={', '.join(scope)}", flush=True)
    steps = ["Parsing spec", "Extracting features",
             *[f"Generating tests for {s}" for s in scope],
             "Resolving deps", "Writing testplan.md", "Writing testplan.json"]
    for i, s in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {s}", flush=True)
        time.sleep(0.2)
    print("[testplan] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
