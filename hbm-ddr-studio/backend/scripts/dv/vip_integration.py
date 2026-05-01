#!/usr/bin/env python3
"""Demo VIP integration.

REPLACE: placeholder. Plug in your real VIP-integration tool.
Contract: JSON line on stdin (form fields) → progress on stdout → exit code.
See docs/INTEGRATION.md.
"""
from __future__ import annotations
import json
import sys
import time


def main() -> int:
    cfg = json.loads(sys.stdin.readline() or "{}")
    vips = cfg.get("vips") or []
    print(f"[vip] tb={cfg.get('tb_path')} vendor={cfg.get('vendor')} adding={vips}", flush=True)
    if not vips:
        print("[vip] nothing to do", flush=True)
        return 0
    for i, v in enumerate(vips, 1):
        print(f"[{i}/{len(vips)}] wiring {v} agent + monitor + sequencer", flush=True)
        time.sleep(0.3)
    if cfg.get("update_makefile", True):
        print(f"[vip] updating Makefile", flush=True)
    print("[vip] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
