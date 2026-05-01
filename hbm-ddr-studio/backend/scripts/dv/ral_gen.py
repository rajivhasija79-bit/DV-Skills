#!/usr/bin/env python3
"""Demo UVM RAL generator.

REPLACE: placeholder. Plug in your real RAL generator.
Contract: JSON line on stdin (form fields) → progress on stdout → exit code.
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
import sys
import time


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    print(f"[ral] reg_spec={cfg.get('reg_spec')} fmt={cfg.get('spec_format')} pkg={cfg.get('package_name')}", flush=True)
    parts = ["Parsing register spec", "Building register model",
             "Emitting reg classes", "Emitting block class",
             "Emitting package wrapper", "Writing files"]
    for i, p in enumerate(parts, 1):
        print(f"[{i}/{len(parts)}] {p}", flush=True)
        time.sleep(0.2)
    print(f"[ral] wrote {cfg.get('package_name')}.sv to {cfg.get('output_dir')}", flush=True)
    print("[ral] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
