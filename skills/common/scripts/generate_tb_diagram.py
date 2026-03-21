#!/usr/bin/env python3
"""
generate_tb_diagram.py — DV Skills S3 diagram generator
Produces:
  - tb_architecture.png  : UVM testbench hierarchy block diagram (Graphviz)
  - dut_block_diagram.png: DUT interface/block diagram (Graphviz)

Usage:
    python3 generate_tb_diagram.py --data /tmp/<PROJECT>_verif_plan_data.json \
                                    --output ./out/ \
                                    --project APB_UART
"""

import argparse
import json
import os
import sys
from pathlib import Path


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_data(data_path: str) -> dict:
    with open(data_path) as f:
        return json.load(f)


def ensure_graphviz():
    try:
        import graphviz
        return graphviz
    except ImportError:
        print("ERROR: graphviz Python package not installed.")
        print("  Run: pip3 install graphviz")
        print("  Also ensure Graphviz system tools are installed: brew install graphviz")
        sys.exit(1)


# ── TB Architecture Diagram ──────────────────────────────────────────────────

def build_tb_diagram(data: dict, output_dir: Path, project: str):
    """Generate UVM testbench hierarchy PNG using Graphviz."""
    gv = ensure_graphviz()

    tb = data.get("tb_architecture", {})
    components = tb.get("components", [])
    dut_name   = data.get("dut", {}).get("name", "DUT")
    interfaces = data.get("dut", {}).get("interfaces", [])

    # Build agent list from components or interfaces
    agents = [c for c in components if "agent" in c.get("type", "").lower()]
    if not agents and interfaces:
        agents = [{"name": f"{iface}_agent", "type": "agent",
                   "sub": [f"{iface}_sequencer", f"{iface}_driver", f"{iface}_monitor"]}
                  for iface in (interfaces if isinstance(interfaces, list) else
                                [i.get("name", i) if isinstance(i, dict) else i
                                 for i in interfaces])]

    # Default agent if nothing found
    if not agents:
        agents = [{"name": "apb_agent", "type": "agent",
                   "sub": ["apb_sequencer", "apb_driver", "apb_monitor"]}]

    dot = gv.Digraph(
        name=f"{project}_TB_Architecture",
        format="png",
        graph_attr={
            "rankdir":   "TB",
            "bgcolor":   "white",
            "fontname":  "Helvetica",
            "fontsize":  "12",
            "splines":   "ortho",
            "nodesep":   "0.6",
            "ranksep":   "0.8",
            "pad":       "0.4",
            "label":     f"{project} — UVM Testbench Architecture",
            "labelloc":  "t",
            "labelfontsize": "16",
            "labelfontname": "Helvetica-Bold",
        },
        node_attr={
            "shape":    "box",
            "style":    "filled,rounded",
            "fontname": "Helvetica",
            "fontsize": "11",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "9",
            "color":    "#555555",
        }
    )

    # ── Colour palette ────────────────────────────────────────────────────
    CLR = {
        "top":       ("#1a3a5c", "white"),   # dark navy
        "env":       ("#2e6da4", "white"),   # blue
        "agent":     ("#3a7ebf", "white"),   # medium blue
        "driver":    ("#5ba3d4", "black"),   # light blue
        "monitor":   ("#7bbcdf", "black"),
        "sequencer": ("#a8d4ef", "black"),
        "scoreboard":("#c0392b", "white"),   # red — functional check
        "coverage":  ("#27ae60", "white"),   # green
        "regmodel":  ("#8e44ad", "white"),   # purple
        "vseq":      ("#d35400", "white"),   # orange
        "dut":       ("#2c3e50", "white"),   # charcoal
        "test":      ("#f39c12", "black"),   # amber
    }

    def node(name, label, kind):
        fc, fc_txt = CLR.get(kind, ("#eeeeee", "black"))
        dot.node(name, label=label,
                 fillcolor=fc, fontcolor=fc_txt,
                 color="#333333")

    def edge(a, b, label="", style="solid"):
        dot.edge(a, b, label=label, style=style)

    # ── Test layer ────────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_test") as c:
        c.attr(label="Test Layer", style="dashed", color="#aaaaaa")
        node("base_test",    "base_test\n(uvm_test)",    "test")
        node("directed_seq", "Directed\nSequences",      "sequencer")
        node("rand_seq",     "Random\nSequences",        "sequencer")
        edge("base_test", "directed_seq")
        edge("base_test", "rand_seq")

    # ── Environment ───────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_env") as env_c:
        env_c.attr(label=f"{project} DV Environment  (dv_env)",
                   style="filled", fillcolor="#eaf4fb",
                   color="#2e6da4", fontcolor="#2e6da4")

        node("vseqr", "Virtual\nSequencer", "vseq")
        node("sb",    "Scoreboard\n(Reference Model + Checks)", "scoreboard")
        node("cov",   "Coverage\nCollector", "coverage")
        node("rgm",   "Register Model\n(UVM RAL)", "regmodel")

        # One sub-cluster per agent
        for idx, ag in enumerate(agents):
            ag_name  = ag.get("name", f"agent_{idx}")
            ag_label = ag_name.replace("_", "\n", 1)
            subs     = ag.get("sub",
                               [f"{ag_name.replace('_agent','')}_sequencer",
                                f"{ag_name.replace('_agent','')}_driver",
                                f"{ag_name.replace('_agent','')}_monitor"])

            sq_id = f"sq_{idx}"
            dr_id = f"dr_{idx}"
            mn_id = f"mn_{idx}"
            ag_id = f"ag_{idx}"

            with dot.subgraph(name=f"cluster_agent_{idx}") as ac:
                ac.attr(label=ag_label, style="filled,rounded",
                        fillcolor="#d6eaf8", color="#3a7ebf")
                node(ag_id, ag_label, "agent")
                node(sq_id, subs[0] if len(subs) > 0 else "sequencer", "sequencer")
                node(dr_id, subs[1] if len(subs) > 1 else "driver",    "driver")
                node(mn_id, subs[2] if len(subs) > 2 else "monitor",   "monitor")

                edge(ag_id, sq_id)
                edge(sq_id, dr_id)
                edge(ag_id, mn_id)

            edge("vseqr", sq_id,  label="seq",  style="dashed")
            edge(mn_id,   "sb",   label="txn",  style="dashed")
            edge(mn_id,   "cov",  label="txn",  style="dashed")

        edge("vseqr", "rgm", label="reg\naccess", style="dashed")
        edge("rgm",   "sb",  style="dashed")

    # ── tb_top ────────────────────────────────────────────────────────────
    with dot.subgraph(name="cluster_top") as t:
        t.attr(label="tb_top", style="dashed", color="#aaaaaa")
        node("tb_top",  "tb_top\n(SV module)",      "top")
        node("clk_rst", "Clock &\nReset Gen",        "top")
        node("dut_box", f"{dut_name}\n(DUT)",        "dut")
        edge("tb_top",  "clk_rst")
        edge("tb_top",  "dut_box")

    # ── Top-level edges ───────────────────────────────────────────────────
    edge("base_test", "vseqr", style="dashed")
    edge("tb_top",    "base_test", style="invis")

    for idx in range(len(agents)):
        dr_id = f"dr_{idx}"
        edge(dr_id, "dut_box", label="IF",
             style="bold", constraint="true")

    out_path = output_dir / "tb_architecture"
    dot.render(str(out_path), cleanup=True)
    print(f"  ✓ TB architecture diagram: {out_path}.png")
    return str(out_path) + ".png"


# ── DUT Block Diagram ─────────────────────────────────────────────────────────

def build_dut_diagram(data: dict, output_dir: Path, project: str):
    """Generate DUT interface/block diagram PNG."""
    gv = ensure_graphviz()

    dut       = data.get("dut", {})
    dut_name  = dut.get("name", project)
    ifaces    = dut.get("interfaces", [])
    features  = dut.get("features",   [])

    dot = gv.Digraph(
        name=f"{project}_DUT",
        format="png",
        graph_attr={
            "rankdir":  "LR",
            "bgcolor":  "white",
            "fontname": "Helvetica",
            "label":    f"{dut_name} — DUT Interface Diagram",
            "labelloc": "t",
            "labelfontsize": "14",
            "labelfontname": "Helvetica-Bold",
            "pad":      "0.5",
            "splines":  "ortho",
        },
        node_attr={
            "shape":    "box",
            "style":    "filled,rounded",
            "fontname": "Helvetica",
            "fontsize": "10",
        }
    )

    # Central DUT block
    dut_label = dut_name
    if features:
        feat_str = "\\n".join(f"• {f}" for f in features[:6])
        dut_label = f"{dut_name}\\n\\n{feat_str}"
    dot.node("DUT_CORE", dut_label,
             shape="box", style="filled", fillcolor="#2c3e50",
             fontcolor="white", fontsize="11", width="3", height="2.5")

    # Input/output interfaces
    input_ifaces  = []
    output_ifaces = []
    if isinstance(ifaces, list):
        for i, iface in enumerate(ifaces):
            name = iface.get("name", f"if_{i}") if isinstance(iface, dict) else str(iface)
            direction = iface.get("direction", "").lower() if isinstance(iface, dict) else ""
            if "out" in direction:
                output_ifaces.append(name)
            else:
                input_ifaces.append(name)

    if not input_ifaces and not output_ifaces:
        input_ifaces  = [f"{project}_in"]
        output_ifaces = [f"{project}_out"]

    for name in input_ifaces:
        safe_id = name.replace(" ", "_").replace("-", "_")
        dot.node(safe_id, name, fillcolor="#3498db", fontcolor="white")
        dot.edge(safe_id, "DUT_CORE", label="")

    for name in output_ifaces:
        safe_id = name.replace(" ", "_").replace("-", "_") + "_out"
        dot.node(safe_id, name, fillcolor="#27ae60", fontcolor="white")
        dot.edge("DUT_CORE", safe_id, label="")

    # Clock & reset
    dot.node("CLK_RST", "clk / rst_n",
             shape="ellipse", fillcolor="#f39c12", fontcolor="black")
    dot.edge("CLK_RST", "DUT_CORE", style="dashed")

    out_path = output_dir / "dut_block_diagram"
    dot.render(str(out_path), cleanup=True)
    print(f"  ✓ DUT block diagram:       {out_path}.png")
    return str(out_path) + ".png"


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate TB + DUT diagrams as PNG")
    parser.add_argument("--data",    required=True, help="Path to verif_plan_data.json")
    parser.add_argument("--output",  required=True, help="Output directory for PNGs")
    parser.add_argument("--project", required=True, help="Project/IP name")
    args = parser.parse_args()

    data_path  = args.data
    output_dir = Path(args.output)
    project    = args.project

    if not os.path.exists(data_path):
        print(f"ERROR: Data file not found: {data_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_data(data_path)

    print(f"\n  Generating diagrams for: {project}")
    print("=" * 56)

    tb_png  = build_tb_diagram(data,  output_dir, project)
    dut_png = build_dut_diagram(data, output_dir, project)

    print("\n  Done.")
    print(f"  TB diagram : {tb_png}")
    print(f"  DUT diagram: {dut_png}\n")


if __name__ == "__main__":
    main()
