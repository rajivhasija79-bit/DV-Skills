#!/usr/bin/env python3
"""
generate_verif_plan_pdf.py — DV Skills S3 PDF generator
Assembles the complete DV Verification Plan PDF from collected data.

PDF engine priority:
  1. Pandoc + LaTeX (pdflatex/xelatex) — best typography
  2. WeasyPrint (HTML → PDF) — no LaTeX needed, good layout
  3. ReportLab — pure Python fallback

Usage:
    python3 generate_verif_plan_pdf.py \
        --data     /tmp/APB_UART_verif_plan_data.json \
        --output   ./dv_verif_plan_out/ \
        --project  APB_UART \
        --tb-diagram   ./dv_verif_plan_out/tb_architecture.png \
        --dut-diagram  ./dv_verif_plan_out/dut_block_diagram.png \
        --gantt        ./dv_verif_plan_out/gantt_schedule.png
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_data(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# HTML/Markdown content builder
# ─────────────────────────────────────────────────────────────────────────────

def _img(path: str, alt: str, width: str = "100%") -> str:
    if path and os.path.exists(path):
        abs_path = os.path.abspath(path)
        return f'<img src="file://{abs_path}" alt="{alt}" style="width:{width};margin:12px 0;border-radius:4px;"/>'
    return f'<p style="color:#999;font-style:italic;">[{alt} — diagram not generated]</p>'


def _table(headers: list, rows: list, col_widths: list = None) -> str:
    w = ""
    if col_widths:
        w = "<colgroup>" + "".join(f'<col style="width:{cw}"/>' for cw in col_widths) + "</colgroup>"
    head = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
    body = ""
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body += f"<tr>{cells}</tr>"
    return f'<table class="dv-table">{w}<thead>{head}</thead><tbody>{body}</tbody></table>'


def _status_badge(status: str) -> str:
    colors = {
        "COVERED":     ("#27ae60", "white"),
        "PARTIAL":     ("#f39c12", "black"),
        "NOT_COVERED": ("#e74c3c", "white"),
        "WAIVED":      ("#95a5a6", "white"),
        "PRELIMINARY": ("#3498db", "white"),
    }
    bg, fg = colors.get(status.upper(), ("#eeeeee", "black"))
    return f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:10px;font-size:0.8em;font-weight:bold;">{status}</span>'


def _milestone_badge(ms: str) -> str:
    colors = {"DV-I": "#2e6da4", "DV-C": "#27ae60", "DV-F": "#c0392b",
              "NEG": "#e74c3c", "STRESS": "#e67e22", "CORNER": "#8e44ad"}
    bg = colors.get(ms.upper(), "#555555")
    return f'<span style="background:{bg};color:white;padding:2px 7px;border-radius:4px;font-size:0.8em;font-weight:bold;">{ms}</span>'


CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap');
  * { box-sizing: border-box; }
  body {
    font-family: 'Source Sans Pro', 'Helvetica Neue', sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1a1a2e;
    margin: 0;
    padding: 0;
  }
  .cover-page {
    page-break-after: always;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    height: 100vh;
    background: linear-gradient(135deg, #1a3a5c 0%, #2e6da4 100%);
    color: white;
    padding: 40px;
  }
  .cover-page h1 { font-size: 2.4em; margin-bottom: 0.2em; font-weight: 700; }
  .cover-page h2 { font-size: 1.4em; font-weight: 300; margin-bottom: 2em; opacity: 0.85; }
  .cover-meta { font-size: 0.9em; opacity: 0.75; margin-top: 2em; }
  .toc-page { page-break-after: always; padding: 40px 60px; }
  .toc-page h2 { color: #2e6da4; border-bottom: 2px solid #2e6da4; padding-bottom: 8px; }
  .toc-entry { display: flex; justify-content: space-between; padding: 4px 0;
               border-bottom: 1px dotted #cccccc; }
  .toc-entry a { color: #2e6da4; text-decoration: none; }
  .section {
    padding: 30px 60px 20px 60px;
    page-break-before: always;
  }
  .section:first-of-type { page-break-before: avoid; }
  h1 { color: #1a3a5c; font-size: 1.8em; border-bottom: 3px solid #2e6da4;
       padding-bottom: 8px; margin-bottom: 16px; }
  h2 { color: #2e6da4; font-size: 1.3em; margin-top: 24px; margin-bottom: 10px;
       border-left: 4px solid #2e6da4; padding-left: 10px; }
  h3 { color: #34495e; font-size: 1.05em; margin-top: 16px; }
  .section-number { color: #2e6da4; font-weight: 700; margin-right: 8px; }
  .dv-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 0.88em;
  }
  .dv-table th {
    background: #2e6da4;
    color: white;
    padding: 7px 10px;
    text-align: left;
    font-weight: 600;
  }
  .dv-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #e0e0e0;
    vertical-align: top;
  }
  .dv-table tr:nth-child(even) td { background: #f4f8fb; }
  .dv-table tr:hover td { background: #eaf4fb; }
  code, pre {
    font-family: 'Source Code Pro', 'Courier New', monospace;
    background: #f4f4f4;
    border-radius: 3px;
  }
  code { padding: 1px 5px; font-size: 0.9em; }
  pre {
    padding: 12px 16px;
    overflow-x: auto;
    border-left: 3px solid #2e6da4;
    font-size: 0.82em;
    line-height: 1.5;
  }
  .info-box {
    background: #eaf4fb;
    border-left: 4px solid #2e6da4;
    padding: 10px 16px;
    border-radius: 0 4px 4px 0;
    margin: 12px 0;
  }
  .warn-box {
    background: #fef9e7;
    border-left: 4px solid #f39c12;
    padding: 10px 16px;
    border-radius: 0 4px 4px 0;
    margin: 12px 0;
  }
  .risk-high   { color: #c0392b; font-weight: bold; }
  .risk-medium { color: #e67e22; font-weight: bold; }
  .risk-low    { color: #27ae60; font-weight: bold; }
  .footer { position: fixed; bottom: 20px; left: 60px; right: 60px;
            font-size: 8pt; color: #999; border-top: 1px solid #eee;
            padding-top: 6px; display: flex; justify-content: space-between; }
  @page {
    size: A4;
    margin: 20mm 15mm 25mm 15mm;
    @bottom-center {
      content: "CONFIDENTIAL — " string(project) " DV Verification Plan";
      font-size: 8pt;
      color: #999;
    }
    @bottom-right {
      content: counter(page) " / " counter(pages);
      font-size: 8pt;
      color: #999;
    }
  }
</style>
"""


def build_html(data: dict, tb_diagram: str, dut_diagram: str, gantt: str) -> str:
    project  = data.get("project", "Project")
    gen_date = datetime.now().strftime("%B %d, %Y")
    dut      = data.get("dut", {})
    team     = data.get("team_info", {})
    dv_lead  = team.get("dv_lead", {})
    lead_name = dv_lead.get("name", "<DV Lead>") if isinstance(dv_lead, dict) else str(dv_lead)

    sections = []

    # ── Cover page ────────────────────────────────────────────────────────
    sections.append(f"""
<div class="cover-page">
  <div>
    <div style="font-size:1em;letter-spacing:4px;text-transform:uppercase;opacity:0.7;margin-bottom:12px;">
      Design Verification
    </div>
    <h1>{project}</h1>
    <h2>Verification Plan</h2>
    <div style="width:80px;height:3px;background:rgba(255,255,255,0.5);margin:0 auto 30px;"></div>
    <div class="cover-meta">
      <div>Prepared by: {lead_name}</div>
      <div>Generated: {gen_date}</div>
      <div style="margin-top:12px;font-size:0.85em;opacity:0.6;">CONFIDENTIAL</div>
    </div>
  </div>
</div>
""")

    # ── TOC ───────────────────────────────────────────────────────────────
    toc_entries = [
        ("1", "DUT Description"),
        ("2", "Testplan Summary"),
        ("3", "Coverage Plan"),
        ("4", "Checker Plan"),
        ("5", "Testbench Architecture"),
        ("6", "Compilation &amp; Simulation Flow"),
        ("7", "Directory Structure"),
        ("8", "DV Resources"),
        ("9", "Debug Guidelines"),
        ("10", "Sign-off Criteria"),
        ("11", "Schedule"),
        ("12", "Team Information &amp; Responsibilities"),
        ("13", "Assumptions, Risks &amp; Mitigation"),
        ("14", "Collateral List"),
        ("A",  "Traceability Matrix"),
    ]
    toc_rows = "".join(
        f'<div class="toc-entry"><span><a href="#sec{n}">{n}. {t}</a></span><span>·</span></div>'
        for n, t in toc_entries
    )
    sections.append(f"""
<div class="toc-page">
  <h2>Table of Contents</h2>
  {toc_rows}
</div>
""")

    # ── Section 1: DUT Description ────────────────────────────────────────
    ifaces = dut.get("interfaces", [])
    if isinstance(ifaces, list):
        iface_rows = []
        for iface in ifaces:
            if isinstance(iface, dict):
                iface_rows.append([iface.get("name","—"), iface.get("type","—"),
                                   iface.get("direction","—"), iface.get("description","—")])
            else:
                iface_rows.append([str(iface), "—", "—", "—"])
    else:
        iface_rows = []

    features = dut.get("features", [])
    feat_list = "".join(f"<li>{f}</li>" for f in features) if features else "<li>—</li>"

    reg_count  = dut.get("register_count", "—")
    clk_info   = dut.get("clocks", "—")
    rst_info   = dut.get("resets", "—")
    dut_ver    = dut.get("version", "—")
    dut_desc   = dut.get("description", "Refer to the architectural specification for full DUT details.")

    iface_table = _table(
        ["Interface", "Type", "Direction", "Description"],
        iface_rows if iface_rows else [["—", "—", "—", "—"]],
        ["20%", "15%", "15%", "50%"]
    )

    sections.append(f"""
<div class="section" id="sec1">
  <h1><span class="section-number">1</span>DUT Description</h1>
  <div class="info-box">
    <strong>IP Name:</strong> {dut.get("name", project)} &nbsp;|&nbsp;
    <strong>Version:</strong> {dut_ver} &nbsp;|&nbsp;
    <strong>Registers:</strong> {reg_count} &nbsp;|&nbsp;
    <strong>Clocks:</strong> {clk_info} &nbsp;|&nbsp;
    <strong>Resets:</strong> {rst_info}
  </div>
  <p>{dut_desc}</p>

  <h2>Key Features</h2>
  <ul>{feat_list}</ul>

  <h2>Interface Summary</h2>
  {iface_table}

  <h2>DUT Block Diagram</h2>
  {_img(dut_diagram, "DUT Block Diagram", "80%")}
</div>
""")

    # ── Section 2: Testplan Summary ───────────────────────────────────────
    tp = data.get("testplan_summary", {})
    tp_counts = tp.get("counts_by_milestone", {})
    tp_rows = [[ms, str(cnt)] for ms, cnt in tp_counts.items()] if tp_counts else [["—", "—"]]
    tp_total = sum(tp_counts.values()) if tp_counts else "—"
    tp_note  = tp.get("note", "")
    tp_warn  = f'<div class="warn-box">⚠ {tp_note}</div>' if tp_note else ""

    sections.append(f"""
<div class="section" id="sec2">
  <h1><span class="section-number">2</span>Testplan Summary</h1>
  {tp_warn}
  <div class="info-box">
    <strong>Total planned tests:</strong> {tp_total}
  </div>
  <h2>Tests by Milestone</h2>
  {_table(["Milestone", "Test Count"], tp_rows)}
  <p>The complete testplan is maintained in <code>testplan.xlsx</code> (see Section 8 — DV Resources).
     The testplan covers all features derived from the architectural specification and is updated
     throughout the DV lifecycle.</p>
</div>
""")

    # ── Section 3: Coverage Plan ──────────────────────────────────────────
    cov_plan = data.get("coverage_plan", [])
    cov_targets = data.get("coverage_plan_targets", {
        "DV-I": "70%", "DV-C": "90%", "DV-F": "100%"
    })
    target_rows = [[ms, tgt] for ms, tgt in cov_targets.items()]

    cov_html = ""
    for cg in cov_plan:
        cg_name  = cg.get("name", "cg_unnamed")
        cg_desc  = cg.get("description", "")
        cg_code  = cg.get("code", f"covergroup {cg_name};\n  // coverpoints\nendgroup")
        cp_rows  = [[cp.get("name","—"), cp.get("signal","—"),
                     cp.get("bins","—"), cp.get("illegal_bins","—")]
                    for cp in cg.get("coverpoints", [])]
        cp_table = _table(
            ["Coverpoint", "Signal", "Bins", "Illegal Bins"],
            cp_rows if cp_rows else [["—","—","—","—"]]
        ) if cp_rows else ""

        cov_html += f"""
  <h2>{cg_name}</h2>
  <p>{cg_desc}</p>
  {cp_table}
  <pre><code>{cg_code}</code></pre>
"""

    if not cov_html:
        cov_html = '<div class="warn-box">Coverage plan not yet defined. Run S2 dv-testplan skill and re-run S3.</div>'

    sections.append(f"""
<div class="section" id="sec3">
  <h1><span class="section-number">3</span>Coverage Plan</h1>

  <h2>Coverage Targets by Milestone</h2>
  {_table(["Milestone", "Functional Coverage Target"], target_rows)}

  <h2>Coverage Categories</h2>
  <ul>
    <li><strong>Functional coverage</strong> — UVM covergroups as defined below</li>
    <li><strong>Line coverage</strong> — every RTL line exercised</li>
    <li><strong>Branch coverage</strong> — all if/else/case branches taken</li>
    <li><strong>Toggle coverage</strong> — all DUT I/O and internal signals toggled</li>
    <li><strong>FSM coverage</strong> — all reachable states and transitions exercised</li>
  </ul>

  <h2>Covergroup Definitions</h2>
  {cov_html}
</div>
""")

    # ── Section 4: Checker Plan ───────────────────────────────────────────
    checkers = data.get("checker_plan", [])
    comp_groups = {}
    for chk in checkers:
        comp = chk.get("component", "scoreboard")
        comp_groups.setdefault(comp, []).append(chk)

    checker_html = ""
    for comp, chks in comp_groups.items():
        rows = [[c.get("id","—"), c.get("description","—"),
                 c.get("type","—"), c.get("assertion_code","—")]
                for c in chks]
        checker_html += f"""
  <h2>Component: <code>{comp}</code></h2>
  {_table(["Checker ID", "Description", "Type", "Assertion Code"], rows,
          ["18%", "35%", "12%", "35%"])}
"""

    if not checker_html:
        checker_html = '<div class="warn-box">Checker plan not yet defined.</div>'

    comp_table = _table(
        ["Component", "Description", "Typical Use"],
        [
            ["scoreboard",  "Reference model comparison and data integrity checks", "Most functional checks"],
            ["testcase",    "Simple pass/fail checks within test body",             "One-off or test-specific"],
            ["interface",   "SVA assertions, protocol compliance checks",           "Timing, protocol rules"],
            ["coverage",    "Illegal bins acting as implicit checks",               "Illegal state combinations"],
            ["monitor",     "Passive protocol observers and sequence checkers",     "Bus snooping, ordering"],
        ]
    )

    sections.append(f"""
<div class="section" id="sec4">
  <h1><span class="section-number">4</span>Checker Plan</h1>

  <h2>Checker Component Reference</h2>
  {comp_table}

  <h2>Checker Assignments</h2>
  {checker_html}
</div>
""")

    # ── Section 5: TB Architecture ────────────────────────────────────────
    tb_arch  = data.get("tb_architecture", {})
    comps    = tb_arch.get("components", [])
    comp_rows = [[c.get("name","—"), c.get("type","—"), c.get("description","—")]
                 for c in comps] if comps else []

    sections.append(f"""
<div class="section" id="sec5">
  <h1><span class="section-number">5</span>Testbench Architecture</h1>

  <h2>TB Block Diagram</h2>
  {_img(tb_diagram, "TB Architecture Diagram", "90%")}

  <h2>Component Descriptions</h2>
  {_table(["Component", "Type", "Description"],
          comp_rows if comp_rows else [["See diagram above", "—", "—"]],
          ["25%", "15%", "60%"])}

  <h2>UVM Hierarchy</h2>
  <pre><code>uvm_test (base_test)
  └── dv_env (uvm_env)
        ├── &lt;if&gt;_agent (uvm_agent)  [one per DUT interface]
        │     ├── &lt;if&gt;_sequencer
        │     ├── &lt;if&gt;_driver
        │     └── &lt;if&gt;_monitor
        ├── scoreboard
        ├── coverage_collector
        ├── reg_model (uvm_reg_block)
        └── virtual_sequencer</code></pre>
</div>
""")

    # ── Section 6: Compilation & Simulation Flow ──────────────────────────
    cf = data.get("compilation_flow", {})
    sim  = cf.get("simulator", "VCS")
    co   = cf.get("compile_cmd",   "make compile")
    ro   = cf.get("run_cmd",       "make sim TEST=<test_name> SEED=<seed>")
    wv   = cf.get("waveform_cmd",  "make waves")
    cov  = cf.get("coverage_cmd",  "make cov")
    log  = cf.get("log_path",      "sim/<test_name>/sim.log")
    defs = cf.get("defines",       [])
    pargs= cf.get("plusargs",       [])
    reg  = cf.get("regression_cmd", "make regression")
    chk  = cf.get("repo_checkout",  "git clone <DV_REPO_URL>")

    def_rows  = [[d.get("name","—"), d.get("description","—")] for d in defs] if defs else [["—","—"]]
    parg_rows = [[p.get("name","—"), p.get("description","—")] for p in pargs] if pargs else [["—","—"]]

    sections.append(f"""
<div class="section" id="sec6">
  <h1><span class="section-number">6</span>Compilation &amp; Simulation Flow</h1>

  <h2>6.1 Repository Checkout</h2>
  <pre><code>{chk}</code></pre>

  <h2>6.2 Compilation</h2>
  <p><strong>Simulator:</strong> {sim}</p>
  <pre><code>{co}</code></pre>

  <h2>6.3 Running a Test</h2>
  <pre><code>{ro}</code></pre>

  <h2>6.3 Running Full Regression</h2>
  <pre><code>{reg}</code></pre>

  <h2>6.4 Opening Waveforms</h2>
  <pre><code>{wv}</code></pre>

  <h2>6.5 Analyzing Coverage</h2>
  <pre><code>{cov}</code></pre>

  <h2>6.6 Log File</h2>
  <p>Log file location: <code>{log}</code></p>
  <pre><code>grep -n "UVM_ERROR\\|UVM_FATAL\\|PASS\\|FAIL" {log}</code></pre>

  <h2>6.7 Available +define+ Options</h2>
  {_table(["+define+", "Description"], def_rows)}

  <h2>6.8 Available Plusargs</h2>
  {_table(["Plusarg", "Description"], parg_rows)}
</div>
""")

    # ── Section 7: Directory Structure ────────────────────────────────────
    dir_struct = data.get("directory_structure", """
<ip_name>_dv/
├── tb/              # Testbench — env, agents, sequences, scoreboards
├── tests/           # Test files
├── sim/             # Simulation run directory
├── scripts/         # Compile/run scripts, Makefile
├── cov/             # Coverage databases and reports
├── waves/           # Waveform databases (FSDB/VCD)
├── docs/            # Verification plan, testplan documents
└── rtl_ref/         # RTL reference (read-only)
""".strip())

    sections.append(f"""
<div class="section" id="sec7">
  <h1><span class="section-number">7</span>Directory Structure</h1>
  <pre><code>{dir_struct}</code></pre>
</div>
""")

    # ── Section 8: DV Resources ───────────────────────────────────────────
    res = data.get("dv_resources", {})

    def link(url: str, label: str) -> str:
        if url and url != "<TBD — INSERT LINK>":
            return f'<a href="{url}">{label}</a>'
        return f"<em>{label}: &lt;TBD — INSERT LINK&gt;</em>"

    res_rows = [
        ["Verification Plan (this document)", link(res.get("verif_plan_url",""), "VP Link")],
        ["Testplan",                          link(res.get("testplan_url",""),   "Testplan Link")],
        ["DV Git Repository",                 link(res.get("dv_repo_url",""),    "DV Repo")],
        ["RTL Git Repository",                link(res.get("rtl_repo_url",""),   "RTL Repo")],
        ["JIRA / Bug Tracker",                link(res.get("jira_url",""),       "JIRA Project")],
        ["Confluence / Wiki",                 link(res.get("wiki_url",""),       "Wiki Page")],
        ["Simulator License Server",          res.get("sim_license","<TBD>")],
    ]
    extra = res.get("other_links", [])
    for e in extra:
        res_rows.append([e.get("label","—"), link(e.get("url",""), e.get("label","—"))])

    sections.append(f"""
<div class="section" id="sec8">
  <h1><span class="section-number">8</span>DV Resources</h1>
  {_table(["Resource", "Link / Location"], res_rows, ["35%", "65%"])}
</div>
""")

    # ── Section 9: Debug Guidelines ───────────────────────────────────────
    dbg = data.get("debug_guidelines", [
        "Check simulation log for first UVM_ERROR or UVM_FATAL: <code>grep -n 'UVM_ERROR|UVM_FATAL' sim.log</code>",
        "Open waveform at the timestep of the first error",
        "Check scoreboard mismatches: compare exp_pkt vs act_pkt in scoreboard log",
        "Enable verbose: <code>+UVM_VERBOSITY=UVM_HIGH</code>",
        "Stop at first error: <code>+UVM_MAX_QUIT_COUNT=1</code>",
        "Isolate failing test with fixed seed: <code>+ntb_random_seed=&lt;SEED&gt;</code>",
        "For register issues: call <code>uvm_reg_block::check_mirror_values()</code>",
    ])
    dbg_list = "".join(f"<li>{tip}</li>" for tip in dbg) if isinstance(dbg, list) else f"<p>{dbg}</p>"

    sections.append(f"""
<div class="section" id="sec9">
  <h1><span class="section-number">9</span>Debug Guidelines</h1>
  <h2>Recommended Debug Workflow</h2>
  <ol>{dbg_list}</ol>
</div>
""")

    # ── Section 10: Sign-off Criteria ─────────────────────────────────────
    so = data.get("signoff_criteria", {})
    cov_tgt  = so.get("coverage",  {"functional":"100%","line":"100%","branch":"100%","toggle":"100%","fsm":"100%"})
    tp_tgt   = so.get("testplan",  {"pass_rate":"100%","skip_blocked":"Zero at DV-F"})
    bug_tgt  = so.get("bugs",      {"p1_p2_open":"Zero","p3_blocking":"Zero","waivers":"All documented"})

    if isinstance(cov_tgt, dict):
        cov_rows = [[k, v] for k, v in cov_tgt.items()]
    else:
        cov_rows = [["All", str(cov_tgt)]]

    sections.append(f"""
<div class="section" id="sec10">
  <h1><span class="section-number">10</span>Sign-off Criteria</h1>

  <div class="info-box">
    DV is considered complete when ALL of the following criteria are met simultaneously.
    Any open exceptions must be formally waived by the design and verification leads.
  </div>

  <h2>Coverage Criteria</h2>
  {_table(["Coverage Type", "Target"], cov_rows)}

  <h2>Testplan Criteria</h2>
  <ul>
    <li><strong>Testplan pass rate:</strong> {tp_tgt.get("pass_rate","100%") if isinstance(tp_tgt,dict) else tp_tgt}</li>
    <li><strong>SKIP/BLOCKED tests:</strong> {tp_tgt.get("skip_blocked","Zero at DV-F") if isinstance(tp_tgt,dict) else ""}</li>
  </ul>

  <h2>Bug Criteria</h2>
  <ul>
    <li><strong>Open P1/P2 JIRAs:</strong> {bug_tgt.get("p1_p2_open","Zero") if isinstance(bug_tgt,dict) else bug_tgt}</li>
    <li><strong>Open P3 DV-blocking JIRAs:</strong> {bug_tgt.get("p3_blocking","Zero") if isinstance(bug_tgt,dict) else ""}</li>
    <li><strong>Coverage waivers:</strong> {bug_tgt.get("waivers","All documented and reviewed") if isinstance(bug_tgt,dict) else ""}</li>
  </ul>
</div>
""")

    # ── Section 11: Schedule ──────────────────────────────────────────────
    sections.append(f"""
<div class="section" id="sec11">
  <h1><span class="section-number">11</span>Schedule</h1>
  {_img(gantt, "DV Milestone Gantt Chart", "100%")}

  <h2>Milestone Definitions</h2>
  {_table(
    ["Milestone", "Trigger Condition", "Key DV Deliverables"],
    [
        ["DV-I", "Initial RTL available; register access functional",
         "TB compiles, register access test passes, testplan approved"],
        ["DV-C", "RTL feature-complete (coding complete)",
         "All directed tests pass, ≥90% functional coverage, ≥95% regression pass rate"],
        ["DV-F", "Final, frozen RTL",
         "100% testplan passing, 100% coverage, zero blocking bugs, VP signed off"],
    ]
  )}
</div>
""")

    # ── Section 12: Team Info ─────────────────────────────────────────────
    team     = data.get("team_info", {})
    dv_lead  = team.get("dv_lead", {})
    engineers = team.get("engineers", [])
    design_owner = team.get("design_owner", {})

    def person_row(role, info):
        if isinstance(info, dict):
            return [role, info.get("name","<TBD>"), info.get("email","<TBD>"),
                    info.get("responsibility","—")]
        return [role, str(info), "—", "—"]

    team_rows = [person_row("DV Lead", dv_lead)]
    for eng in (engineers if isinstance(engineers, list) else []):
        team_rows.append(person_row("DV Engineer", eng))
    team_rows.append(person_row("Design Owner", design_owner))

    for role_key, label in [("rtl_owner","RTL Owner"),
                              ("verif_mgr","Verification Manager"),
                              ("pm","Project Manager")]:
        if role_key in team:
            team_rows.append(person_row(label, team[role_key]))

    sections.append(f"""
<div class="section" id="sec12">
  <h1><span class="section-number">12</span>Team Information &amp; Responsibilities</h1>
  {_table(["Role", "Name", "Email", "Responsibility"],
          team_rows if team_rows else [["—","—","—","—"]],
          ["18%","22%","30%","30%"])}
</div>
""")

    # ── Section 13: Assumptions, Risks & Mitigation ───────────────────────
    assumptions = data.get("assumptions", [
        "RTL is delivered per the agreed milestone schedule",
        "DV environment uses UVM 1.2 or later",
        "Register model is generated from IP-XACT or equivalent",
        "Formal verification is out of scope for this DV plan",
    ])
    risks = data.get("risks", [
        {"risk": "RTL delivery slippage",     "probability":"Medium","impact":"High",
         "mitigation":"TB development against golden model; schedule floats with RTL"},
        {"risk": "Coverage closure difficulty","probability":"Medium","impact":"High",
         "mitigation":"Coverage analysis from DV-I; waiver process in place"},
        {"risk": "Protocol spec ambiguity",   "probability":"Medium","impact":"High",
         "mitigation":"Raise spec questions early; DV team tracks discrepancies"},
    ])

    assump_html = "".join(f"<li>{a}</li>" for a in assumptions)

    risk_rows = []
    for r in risks:
        prob = r.get("probability","—")
        prob_html = f'<span class="risk-{"high" if prob=="High" else "medium" if prob=="Medium" else "low"}">{prob}</span>'
        imp  = r.get("impact","—")
        imp_html = f'<span class="risk-{"high" if imp=="High" else "medium" if imp=="Medium" else "low"}">{imp}</span>'
        risk_rows.append([r.get("risk","—"), prob_html, imp_html, r.get("mitigation","—")])

    sections.append(f"""
<div class="section" id="sec13">
  <h1><span class="section-number">13</span>Assumptions, Risks &amp; Mitigation</h1>

  <h2>Assumptions</h2>
  <ol>{assump_html}</ol>

  <h2>Risk Register</h2>
  {_table(["Risk", "Probability", "Impact", "Mitigation"],
          risk_rows if risk_rows else [["—","—","—","—"]],
          ["30%","12%","12%","46%"])}
</div>
""")

    # ── Section 14: Collateral List ───────────────────────────────────────
    recv = data.get("collateral", {}).get("receivables", [
        "RTL source files + integration guide",
        "Architectural specification (final version)",
        "Register specification (IP-XACT or Excel)",
        "Interface timing diagrams / waveforms",
        "Existing UVM agents for DUT interfaces (if any)",
    ])
    deliv = data.get("collateral", {}).get("deliverables", [
        "Verification Plan (this document)",
        "Testplan (Excel)",
        "UVM Testbench source code",
        "Simulation regression scripts",
        "Coverage closure report",
        "Bug report (JIRA export)",
        "Verification sign-off report",
    ])

    recv_html  = "".join(f"<li>{r}</li>" for r in recv)
    deliv_html = "".join(f"<li>{d}</li>" for d in deliv)

    sections.append(f"""
<div class="section" id="sec14">
  <h1><span class="section-number">14</span>Collateral List</h1>

  <h2>Receivables (DV Team receives)</h2>
  <ul>{recv_html}</ul>

  <h2>Deliverables (DV Team delivers)</h2>
  <ul>{deliv_html}</ul>
</div>
""")

    # ── Appendix A: Traceability Matrix ───────────────────────────────────
    tm = data.get("traceability_matrix", [])
    tm_rows = []
    for entry in tm:
        status    = entry.get("status", "NOT_COVERED")
        badge     = _status_badge(status)
        ms_list   = ", ".join(_milestone_badge(m) for m in entry.get("milestones", [])) or "—"
        chk_ids   = ", ".join(entry.get("checker_ids", [])) or "—"
        test_names = ", ".join(entry.get("test_names",  [])) or "—"
        cov_bins  = entry.get("coverage_bins", "—")
        tm_rows.append([
            entry.get("feature","—"),
            entry.get("spec_section","—"),
            chk_ids,
            test_names,
            ms_list,
            cov_bins,
            badge,
        ])

    warn_count = sum(1 for e in tm if e.get("status","") in ("NOT_COVERED","PARTIAL"))
    warn_box   = f'<div class="warn-box">⚠ {warn_count} feature(s) are NOT_COVERED or PARTIAL — review required before DV-F signoff.</div>' if warn_count else ""

    sections.append(f"""
<div class="section" id="secA">
  <h1><span class="section-number">A</span>Traceability Matrix</h1>
  {warn_box}
  {_table(
    ["Feature", "Spec Section", "Checker ID(s)", "Test Name(s)", "Milestone(s)", "Coverage Bin", "Status"],
    tm_rows if tm_rows else [["No traceability data","—","—","—","—","—","—"]],
    ["18%","10%","14%","18%","12%","16%","12%"]
  )}
</div>
""")

    # ── Assemble final HTML ───────────────────────────────────────────────
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>{project} — DV Verification Plan</title>
{CSS}
</head>
<body>
{body}
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# PDF generation engines
# ─────────────────────────────────────────────────────────────────────────────

def try_pandoc(html_path: str, pdf_path: str) -> bool:
    if not shutil.which("pandoc"):
        return False
    latex_engine = "pdflatex"
    for eng in ("xelatex", "pdflatex", "lualatex"):
        if shutil.which(eng):
            latex_engine = eng
            break
    cmd = ["pandoc", html_path, "-o", pdf_path,
           "--pdf-engine", latex_engine, "--standalone"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            print(f"  ✓ PDF generated with pandoc + {latex_engine}")
            return True
        print(f"  ⚠ pandoc error: {r.stderr[:200]}")
        return False
    except Exception as e:
        print(f"  ⚠ pandoc exception: {e}")
        return False


def try_weasyprint(html_path: str, pdf_path: str) -> bool:
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        print("  ✓ PDF generated with WeasyPrint")
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"  ⚠ WeasyPrint error: {e}")
        return False


def try_reportlab(data: dict, pdf_path: str, tb_diag: str,
                  dut_diag: str, gantt: str) -> bool:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, Image, PageBreak)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
    except ImportError:
        print("  ✗ ReportLab not available. Install: pip3 install reportlab")
        return False

    project = data.get("project", "Project")
    styles  = getSampleStyleSheet()

    H1 = ParagraphStyle("H1", parent=styles["Heading1"],
                         textColor=colors.HexColor("#1a3a5c"), fontSize=14)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"],
                         textColor=colors.HexColor("#2e6da4"), fontSize=11)
    NR = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=9.5)

    def p(text, style=None):
        return Paragraph(text, style or NR)

    def h1(text):
        return Paragraph(text, H1)

    def h2(text):
        return Paragraph(text, H2)

    def img_el(path, w_cm=14):
        if path and os.path.exists(path):
            try:
                return Image(path, width=w_cm*cm, height=w_cm*cm*0.6)
            except Exception:
                pass
        return p(f"[diagram not available]", styles["Italic"])

    story = [
        h1(f"{project} — DV Verification Plan"),
        Spacer(1, 0.5*cm),
        p(f"Generated: {datetime.now().strftime('%B %d, %Y')}"),
        PageBreak(),
        h1("1. DUT Description"),
        p(str(data.get("dut", {}).get("description", "See spec."))),
        Spacer(1, 0.3*cm),
        img_el(dut_diag),
        PageBreak(),
        h1("5. Testbench Architecture"),
        img_el(tb_diag),
        PageBreak(),
        h1("11. Schedule"),
        img_el(gantt, 16),
    ]

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    doc.build(story)
    print("  ✓ PDF generated with ReportLab (basic layout)")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate DV Verification Plan PDF")
    parser.add_argument("--data",        required=True)
    parser.add_argument("--output",      required=True)
    parser.add_argument("--project",     required=True)
    parser.add_argument("--tb-diagram",  default=None)
    parser.add_argument("--dut-diagram", default=None)
    parser.add_argument("--gantt",       default=None)
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: Data file not found: {args.data}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_data(args.data)
    print(f"\n  Generating Verification Plan PDF for: {args.project}")
    print("=" * 56)

    # Build HTML
    html_content = build_html(data,
                              args.tb_diagram  or "",
                              args.dut_diagram or "",
                              args.gantt       or "")

    # Write HTML to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html",
                                     delete=False, encoding="utf-8") as tf:
        tf.write(html_content)
        html_tmp = tf.name

    # Also save HTML for reference
    html_out = output_dir / f"{args.project}_verif_plan.html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html_content)

    pdf_out = str(output_dir / "dv_verif_plan.pdf")

    # Try engines in order
    success = (try_pandoc(html_tmp, pdf_out) or
               try_weasyprint(html_tmp, pdf_out) or
               try_reportlab(data, pdf_out, args.tb_diagram,
                              args.dut_diagram, args.gantt))

    os.unlink(html_tmp)

    if success:
        print(f"\n  ✓ Verification Plan PDF : {pdf_out}")
        print(f"  ✓ HTML version           : {html_out}\n")
    else:
        print(f"\n  ✗ PDF generation failed. HTML available at: {html_out}")
        print("  Install pandoc: brew install pandoc")
        print("  Or install WeasyPrint: pip3 install weasyprint")
        print("  Or install ReportLab: pip3 install reportlab\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
