#!/usr/bin/env python3
"""Demo script for DV Testbench Creation."""
from __future__ import annotations
import json
import sys
import time


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    print(f"[tb] level={cfg.get('level')} name={cfg.get('name')} -> {cfg.get('output_dir')}", flush=True)
    files = ["env.sv", "agent.sv", "scoreboard.sv", "sequencer.sv", "test_base.sv", "Makefile"]
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] writing {f}", flush=True)
        time.sleep(0.25)
    print("[tb] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
