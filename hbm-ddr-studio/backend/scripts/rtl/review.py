#!/usr/bin/env python3
"""Demo RTL review against spec checklist."""
from __future__ import annotations
import json
import sys
import time


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    print(f"[review] spec={cfg.get('spec_path')} rtl={cfg.get('rtl_path')}", flush=True)
    print(f"[review] focus={cfg.get('focus') or '[All]'} threshold={cfg.get('severity_threshold')}", flush=True)
    checks = [
        ("Spec parser", "Loaded 42 features from PRD"),
        ("RTL inventory", "Found 17 modules, 124 always_ff blocks"),
        ("Functional", "38/42 features mapped, 4 TODO"),
        ("Lint",       "12 warnings, 0 errors"),
        ("CDC",        "3 unsynced paths flagged"),
        ("Power",      "OK"),
        ("Synthesis",  "Reviewed reset tree, OK"),
        ("Report",     "Wrote review_report.md, issues.json"),
    ]
    for i, (name, msg) in enumerate(checks, 1):
        print(f"[{i}/{len(checks)}] {name}: {msg}", flush=True)
        time.sleep(0.25)
    print("[review] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
