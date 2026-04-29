#!/usr/bin/env python3
"""Demo script for RTL Subsystem Integration. Reads JSON config from stdin."""
from __future__ import annotations
import json
import sys
import time


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    raw = sys.stdin.readline()
    cfg = json.loads(raw or "{}")
    log(f"[integrate] starting protocol={cfg.get('protocol')} phy={cfg.get('phy_vendor')} channels={cfg.get('channels')}")
    steps = [
        "Resolving IP versions",
        "Generating subsystem hierarchy",
        f"Wiring {cfg.get('channels', 4)} channels",
        f"Stitching NoC ({cfg.get('noc', 'Custom')})",
        f"Inserting RAS infra ({cfg.get('ras_ip', 'None')})",
        f"Inserting SMMU ({cfg.get('smmu_ip', 'None')})",
        "Running quick lint",
        "Writing integration_report.json",
    ]
    for i, s in enumerate(steps, 1):
        log(f"[{i}/{len(steps)}] {s}")
        time.sleep(0.4)
    log("[integrate] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
