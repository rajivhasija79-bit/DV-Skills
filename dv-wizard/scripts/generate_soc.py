#!/usr/bin/env python3
"""
DV Wizard — SoC Testbench Generation Script
This script generates a SoC-level UVM testbench.
Replace this dummy with your actual generation logic.
"""
import sys
import json
import time
import os

def main():
    config = json.load(sys.stdin)

    project    = config.get('project', {})
    component  = config.get('component_name', 'unknown_soc')
    components = config.get('components', [])
    vips       = config.get('vips', [])
    ral        = config.get('ral', {})
    c_model    = config.get('c_model', {})
    sim_tool   = project.get('sim_tool', 'VCS')
    tb_root    = project.get('tb_root', '.')

    print(f"[generate_soc] Starting SoC testbench generation for: {component}")
    print(f"[generate_soc] Project: {project.get('name', 'N/A')}")
    print(f"[generate_soc] TB Root: {tb_root}")
    print(f"[generate_soc] Sim Tool: {sim_tool}")
    time.sleep(0.3)

    # Create directory structure
    soc_dir = os.path.join(tb_root, component, 'dv')
    dirs = ['env', 'tb', 'tests', 'sequences', 'docs', 'firmware']
    print(f"[generate_soc] Creating directory structure under: {soc_dir}")
    for d in dirs:
        path = os.path.join(soc_dir, d)
        print(f"[generate_soc]   ✓ {path}")
        time.sleep(0.1)

    # Process components (SS and IP)
    print(f"[generate_soc] Integrating {len(components)} component(s)...")
    for comp in components:
        name = comp.get('name', 'unnamed')
        ctype = comp.get('type', 'SS')
        count = comp.get('count', 1)
        comp_vips = comp.get('vips', [])
        print(f"[generate_soc]   ✓ {ctype}: {name} (x{count}) — {len(comp_vips)} VIP(s)")
        for v in comp_vips:
            src = v.get('source', '')
            src_label = f" (from {src})" if src else ""
            print(f"[generate_soc]       └─ {v.get('name','?')} [{v.get('mode','Active')}]{src_label}")
        time.sleep(0.15)

    # Extra VIPs
    if vips:
        print(f"[generate_soc] Adding {len(vips)} extra SoC-level VIP(s)...")
        for v in vips:
            print(f"[generate_soc]   ✓ VIP: {v.get('name','unnamed')} [{v.get('mode','Active')}]")
            time.sleep(0.1)

    # RAL
    if ral.get('enabled'):
        print(f"[generate_soc] RAL Model: enabled (interface: {ral.get('interface', 'N/A')})")
    else:
        print(f"[generate_soc] RAL Model: disabled")

    # C Model
    if c_model.get('enabled'):
        print(f"[generate_soc] C Model: enabled")
    else:
        print(f"[generate_soc] C Model: disabled")

    time.sleep(0.2)

    # Generate files
    files = [
        f"{component}_tb_top.sv",
        f"{component}_env.sv",
        f"{component}_virtual_sequencer.sv",
        f"{component}_scoreboard.sv",
        f"{component}_coverage.sv",
        f"{component}_base_test.sv",
        f"{component}_seq_lib.sv",
        f"{component}_firmware_loader.sv",
        f"Makefile",
        f"{component}.f",
    ]
    print(f"[generate_soc] Generating SoC UVM testbench files...")
    for f in files:
        print(f"[generate_soc]   ✓ Generated: {f}")
        time.sleep(0.1)

    print(f"[generate_soc] ──────────────────────────────────────")
    print(f"[generate_soc] 🎉 SoC Testbench generation complete for '{component}'!")
    print(f"[generate_soc] Output: {soc_dir}")

if __name__ == '__main__':
    main()
