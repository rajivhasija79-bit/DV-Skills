#!/usr/bin/env python3
"""Demo SDC generator.

REPLACE: placeholder. Plug in your real SDC-generation tool.
Contract: JSON line on stdin (form fields) → progress on stdout → exit code.
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
import sys
import time


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    style = cfg.get("style", "Synopsys")
    n_clocks = int(cfg.get("clock_count", 3))
    fmax = int(cfg.get("max_freq_mhz", 1600))
    print(f"[sdc] style={style} clocks={n_clocks} fmax={fmax} top={cfg.get('top_module')}", flush=True)
    steps = ["Parsing RTL hierarchy", "Discovering clock roots",
             *[f"Constraining clock {i+1}/{n_clocks} @ {fmax} MHz" for i in range(n_clocks)],
             "Adding I/O delays", "Adding false_paths" if cfg.get("include_false_paths", True) else "Skipping false_paths",
             "Writing constraints.sdc"]
    for i, s in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {s}", flush=True)
        time.sleep(0.2)
    print("[sdc] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
