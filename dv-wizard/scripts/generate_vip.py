#!/usr/bin/env python3
"""
DV Wizard — VIP Generation Script
This script generates a Verification IP component.
Replace this dummy with your actual generation logic.
"""
import sys
import json
import time
import os

def main():
    config = json.load(sys.stdin)

    project   = config.get('project', {})
    component = config.get('component_name', 'unknown_vip')
    vip_info  = config.get('vip_info', {})
    tb_root   = project.get('tb_root', '.')

    protocol  = vip_info.get('protocol', 'Custom')
    bus_width = vip_info.get('bus_width', '32')
    mode      = vip_info.get('mode', 'Master')
    out_path  = vip_info.get('output_path', f'common/{component}')

    print(f"[generate_vip] Starting VIP generation for: {component}")
    print(f"[generate_vip] Protocol: {protocol}")
    print(f"[generate_vip] Bus Width: {bus_width}")
    print(f"[generate_vip] Mode: {mode}")
    print(f"[generate_vip] Output Path: {out_path}")
    time.sleep(0.3)

    # Create directory structure
    vip_dir = os.path.join(tb_root, out_path)
    dirs = ['src', 'sequences', 'tests']
    print(f"[generate_vip] Creating directory structure under: {vip_dir}")
    for d in dirs:
        path = os.path.join(vip_dir, d)
        print(f"[generate_vip]   ✓ {path}")
        time.sleep(0.1)

    time.sleep(0.2)

    # Generate files
    files = [
        f"{component}_if.sv",
        f"{component}_item.sv",
        f"{component}_driver.sv",
        f"{component}_monitor.sv",
        f"{component}_agent.sv",
        f"{component}_config.sv",
        f"{component}_seq_lib.sv",
        f"{component}_coverage.sv",
        f"{component}_pkg.sv",
    ]
    print(f"[generate_vip] Generating VIP files...")
    for f in files:
        print(f"[generate_vip]   ✓ Generated: {f}")
        time.sleep(0.1)

    print(f"[generate_vip] ──────────────────────────────────────")
    print(f"[generate_vip] 🎉 VIP generation complete for '{component}'!")
    print(f"[generate_vip] Output: {vip_dir}")

if __name__ == '__main__':
    main()
