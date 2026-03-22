#!/usr/bin/env python3
"""
gen_coverage_signoff_report.py — DV Skills Combined Sign-off HTML Report
Integrates S7 (assertions), S9 (regression), S10 (coverage) data into
a single self-contained HTML sign-off report.

Usage:
    from gen_coverage_signoff_report import gen_signoff_report
    gen_signoff_report(coverage_data, regression_data, assertions_data,
                       milestone_results, output_path, config)

    python3 gen_coverage_signoff_report.py \
        --coverage   dv/dv_coverage_data.json \
        --regression dv/sim/results/dv_regression_data.json \
        --assertions dv/dv_assertions_data.json \
        --milestone  dv/sim/regression/milestone_results.json \
        --project    apb_uart \
        --out        dv/sim/regression/signoff_report/index.html
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# CSS (inline, self-contained)
# ══════════════════════════════════════════════════════════════════════════════

_CSS = """
:root {
  --green:  #27ae60; --red: #e74c3c; --yellow: #f39c12; --blue: #2980b9;
  --grey:   #7f8c8d; --dark: #2c3e50; --light: #ecf0f1; --white: #fff;
  --shadow: 0 2px 8px rgba(0,0,0,.12);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: var(--dark); font-size: 14px; }
a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Header */
.hdr { background: var(--dark); color: var(--white); padding: 20px 32px; }
.hdr h1 { font-size: 1.5rem; font-weight: 600; }
.hdr .meta { font-size: .82rem; color: #aab; margin-top: 5px; }

/* Banner */
.banner { padding: 18px 32px; font-size: 1.1rem; font-weight: 700;
          display: flex; align-items: center; gap: 14px; }
.banner.green  { background: #d5f5e3; color: #1a7340; border-left: 6px solid var(--green); }
.banner.yellow { background: #fef9e7; color: #7d6608; border-left: 6px solid var(--yellow); }
.banner.red    { background: #fde8e8; color: #922b21; border-left: 6px solid var(--red); }
.banner .icon  { font-size: 1.6rem; }

/* Layout */
.container { max-width: 1400px; margin: 0 auto; padding: 24px 32px; }
.section    { margin-bottom: 32px; }
h2 { font-size: 1.05rem; font-weight: 600; margin-bottom: 14px;
     padding-bottom: 7px; border-bottom: 2px solid var(--light); color: var(--dark); }

/* Milestone gate cards */
.gates { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 28px; }
.gate  { flex: 1; min-width: 200px; background: var(--white); border-radius: 8px;
          padding: 16px 20px; box-shadow: var(--shadow); }
.gate h3 { font-size: .85rem; text-transform: uppercase; letter-spacing: .5px;
            color: #888; margin-bottom: 10px; }
.gate .gstatus { font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }
.gate.pass .gstatus { color: var(--green); }
.gate.fail .gstatus { color: var(--red); }
.gate ul { padding-left: 16px; font-size: .82rem; color: #555; }

/* Coverage bars */
.cov-bars { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.cov-bar-row { display: flex; align-items: center; gap: 12px; }
.cov-bar-lbl { width: 110px; font-size: .82rem; font-weight: 500; text-align: right; }
.cov-bar-wrap { flex: 1; height: 18px; background: #e0e0e0; border-radius: 10px; position: relative; }
.cov-bar-fill { height: 100%; border-radius: 10px; }
.cov-bar-fill.g { background: var(--green); }
.cov-bar-fill.y { background: var(--yellow); }
.cov-bar-fill.r { background: var(--red); }
.cov-bar-thr  { position: absolute; top: 0; bottom: 0; width: 2px; background: #555; }
.cov-bar-pct  { width: 55px; font-size: .82rem; text-align: right; font-weight: 600; }

/* Tables */
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: var(--white);
         border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); font-size: .85rem; }
th { background: var(--dark); color: var(--white); padding: 9px 13px;
     text-align: left; font-weight: 500; white-space: nowrap; }
td { padding: 8px 13px; border-bottom: 1px solid #eee; vertical-align: top; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8f9ff; }
.badge { display: inline-block; border-radius: 4px; padding: 2px 8px;
          font-size: .76rem; font-weight: 600; white-space: nowrap; }
.bp  { background:#d5f5e3; color:#1a7340; }
.bf  { background:#fde8e8; color:#922b21; }
.by  { background:#fef9e7; color:#7d6608; }
.bg  { background:#f2f3f4; color:#555; }
code { background:#f2f3f4; padding:1px 5px; border-radius:3px;
        font-family:monospace; font-size:.81rem; }

/* Action items */
.actions { background: #fff9e6; border-left: 4px solid var(--yellow);
            border-radius: 0 8px 8px 0; padding: 14px 18px; }
.actions ul { padding-left: 18px; }
.actions li { margin-bottom: 6px; font-size: .88rem; }

/* Collapsible */
details summary { cursor: pointer; user-select: none; padding: 4px 0; }
details summary::before { content: "▶ "; font-size: .72rem; }
details[open] summary::before { content: "▼ "; }

/* Footer */
.footer { text-align: center; color: #aaa; font-size: .76rem; padding: 16px 0 28px; }
"""


# ══════════════════════════════════════════════════════════════════════════════
# Section renderers
# ══════════════════════════════════════════════════════════════════════════════

def _badge(label: str, style: str = "bg") -> str:
    return f'<span class="badge {style}">{label}</span>'


def _milestone_status(milestone_results: dict) -> tuple[str, str]:
    """Returns (banner_class, banner_text) based on highest milestone achieved."""
    if milestone_results.get("dv_f", {}).get("passed"):
        return "green", "&#10003; READY FOR SIGN-OFF — DV-F criteria met"
    if milestone_results.get("dv_c", {}).get("passed"):
        return "yellow", "&#9888; DV-C COMPLETE — DV-F criteria not yet met"
    if milestone_results.get("dv_i", {}).get("passed"):
        return "yellow", "&#9888; DV-I COMPLETE — DV-C criteria not yet met"
    return "red", "&#10007; NOT READY — DV-I criteria not met"


def render_banner(milestone_results: dict, project: str, timestamp: str) -> str:
    cls, text = _milestone_status(milestone_results)
    return f"""
<div class="banner {cls}">
  <span class="icon">{"✓" if cls=="green" else ("⚠" if cls=="yellow" else "✗")}</span>
  <div>
    <div>{text}</div>
    <div style="font-size:.8rem;font-weight:400;margin-top:4px">{project} &nbsp;|&nbsp; {timestamp}</div>
  </div>
</div>"""


def render_milestone_section(milestone_results: dict) -> str:
    gates_html = ""
    for gate in ("dv_i", "dv_c", "dv_f"):
        result  = milestone_results.get(gate, {})
        passed  = result.get("passed", False)
        cls     = "pass" if passed else "fail"
        status  = "✓ PASS" if passed else "✗ FAIL"
        failing = [f"{m}: {c['actual']} &lt; {c['required']}"
                   for m, c in result.get("checks", {}).items() if not c.get("passed")]
        items_html = "".join(f"<li>{f}</li>" for f in failing) if failing else "<li>All checks passed</li>"
        gates_html += f"""
<div class="gate {cls}">
  <h3>{gate.replace("_","-").upper()}</h3>
  <div class="gstatus">{status}</div>
  <ul>{items_html}</ul>
</div>"""

    return f"""
<div class="section">
  <h2>Milestone Gate Summary</h2>
  <div class="gates">{gates_html}</div>
</div>"""


def render_coverage_dashboard(coverage_data: dict) -> str:
    cc = coverage_data.get("code_coverage", {})
    fc = coverage_data.get("functional_coverage", {})

    # DV-F thresholds for bar markers
    thr = {"line":99.0,"toggle":95.0,"branch":99.0,"expression":99.0,"fsm":99.0,"functional":99.0}

    types = [
        ("line",       cc.get("line", {})),
        ("toggle",     cc.get("toggle", {})),
        ("branch",     cc.get("branch", {})),
        ("expression", cc.get("expression", {})),
        ("fsm",        cc.get("fsm", {})),
        ("functional", {"pct": fc.get("pct", 0.0),
                         "covered": fc.get("covered_bins", 0),
                         "total":   fc.get("total_bins", 0)}),
    ]

    bars_html = ""
    table_rows = ""
    for ctype, data in types:
        if not data:
            continue
        pct      = data.get("pct", 0.0) or 0.0
        covered  = data.get("covered", 0)
        total    = data.get("total", 0)
        excluded = data.get("excluded", 0)
        threshold= thr.get(ctype, 99.0)
        thr_pos  = threshold  # as percentage width
        delta    = round(pct - threshold, 1)
        delta_str= (f"+{delta}%" if delta >= 0 else f"{delta}%")
        cls      = "g" if pct >= threshold else ("y" if pct >= threshold*0.9 else "r")
        dvf_badge= _badge("✓ DV-F","bp") if pct >= threshold else _badge(f"{delta_str}","bf")

        bars_html += f"""
<div class="cov-bar-row">
  <div class="cov-bar-lbl">{ctype}</div>
  <div class="cov-bar-wrap">
    <div class="cov-bar-fill {cls}" style="width:{min(pct,100):.1f}%"></div>
    <div class="cov-bar-thr" style="left:{thr_pos:.1f}%" title="DV-F threshold: {thr_pos}%"></div>
  </div>
  <div class="cov-bar-pct">{pct:.1f}%</div>
</div>"""

        table_rows += (
            f"<tr><td>{ctype}</td>"
            f"<td>{total}</td><td>{covered}</td><td>{excluded}</td>"
            f"<td><b>{pct:.1f}%</b></td><td>{threshold}%</td><td>{dvf_badge}</td></tr>\n"
        )

    return f"""
<div class="section">
  <h2>Coverage Dashboard</h2>
  <div class="cov-bars">{bars_html}</div>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Type</th><th>Total</th><th>Covered</th><th>Excluded</th>
        <th>Coverage</th><th>DV-F Thr</th><th>Delta</th>
      </tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</div>"""


def render_functional_coverage(coverage_data: dict) -> str:
    fc   = coverage_data.get("functional_coverage", {})
    groups = fc.get("covergroups", [])
    if not groups:
        return ""

    rows = ""
    for cg in groups:
        for cp in cg.get("coverpoints", []):
            for b in cp.get("bins", []):
                if b.get("excluded"):
                    status = _badge("EXCL","bg")
                elif b.get("covered"):
                    status = _badge("HIT","bp")
                else:
                    status = _badge("MISSED","bf")
                rows += (
                    f"<tr><td><code>{cg['name']}</code></td>"
                    f"<td><code>{cp['name']}</code></td>"
                    f"<td>{b['name']}</td>"
                    f"<td>{b['hit_count']}</td><td>{b['at_least']}</td>"
                    f"<td>{status}</td></tr>\n"
                )

    return f"""
<details open class="section">
  <summary><h2>Functional Coverage Details</h2></summary>
  <div class="tbl-wrap" style="margin-top:12px">
    <table>
      <thead><tr>
        <th>Covergroup</th><th>Coverpoint</th><th>Bin</th>
        <th>Hits</th><th>At Least</th><th>Status</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</details>"""


def render_gap_analysis(coverage_data: dict) -> str:
    gs = coverage_data.get("gaps_summary", {})
    excl_items = coverage_data.get("exclusions", {}).get("items", [])
    stub_items  = coverage_data.get("stubs",      {}).get("items", [])

    stats = (f"Total: {gs.get('total_gaps',0)}  |  "
             f"Excluded: {gs.get('excluded',0)}  |  "
             f"Stubs: {gs.get('stubs_generated',0)}  |  "
             f"Skipped: {gs.get('skipped',0)}")

    excl_rows = ""
    for e in excl_items[:50]:
        excl_rows += (
            f"<tr><td><code>{e.get('gap_id','')}</code></td>"
            f"<td>{e.get('type','')}</td>"
            f"<td><code>{e.get('path','')[:60]}</code></td>"
            f"<td>{e.get('reason','')[:80]}</td>"
            f"<td>{e.get('reviewer','')}</td></tr>\n"
        )

    stub_rows = ""
    for s in stub_items:
        status_badge = _badge(s.get("status","generated"),"bg")
        stub_rows += (
            f"<tr><td><code>{s.get('gap_id','')}</code></td>"
            f"<td>{s.get('stub_type','')}</td>"
            f"<td><code>{os.path.basename(s.get('file',''))}</code></td>"
            f"<td><code>{s.get('coverage_target','')[:60]}</code></td>"
            f"<td>{status_badge}</td></tr>\n"
        )

    return f"""
<div class="section">
  <h2>Gap Analysis</h2>
  <p style="margin-bottom:12px;color:#555">{stats}</p>

  <details open><summary><b>Exclusions ({len(excl_items)})</b></summary>
  <div class="tbl-wrap" style="margin-top:10px">
    <table>
      <thead><tr><th>Gap ID</th><th>Type</th><th>Path</th><th>Justification</th><th>Reviewer</th></tr></thead>
      <tbody>{excl_rows or '<tr><td colspan=5 style="text-align:center;color:#aaa">No exclusions</td></tr>'}</tbody>
    </table>
  </div></details>

  <details style="margin-top:14px"><summary><b>Coverage Stubs ({len(stub_items)})</b></summary>
  <div class="tbl-wrap" style="margin-top:10px">
    <table>
      <thead><tr><th>Gap ID</th><th>Type</th><th>File</th><th>Coverage Target</th><th>Status</th></tr></thead>
      <tbody>{stub_rows or '<tr><td colspan=5 style="text-align:center;color:#aaa">No stubs</td></tr>'}</tbody>
    </table>
  </div></details>
</div>"""


def render_assertions_section(assertions_data: dict) -> str:
    chk_ids = assertions_data.get("chk_ids", {})
    if not chk_ids:
        return ""

    rows = ""
    for chk_id, info in chk_ids.items():
        chk_type = info.get("checker_type", "")
        module   = info.get("module","") or info.get("vip_name","")
        feature  = info.get("feature","")
        rows += (
            f"<tr><td><code>{chk_id}</code></td>"
            f"<td>{module}</td>"
            f"<td>{feature}</td>"
            f"<td>{chk_type}</td></tr>\n"
        )

    total = len(chk_ids)
    return f"""
<details class="section">
  <summary><h2>Assertions (S7) — {total} CHK_IDs</h2></summary>
  <div class="tbl-wrap" style="margin-top:12px">
    <table>
      <thead><tr><th>CHK_ID</th><th>Module</th><th>Feature</th><th>Type</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</details>"""


def render_regression_section(regression_data: dict) -> str:
    s = regression_data.get("summary", regression_data)
    total   = s.get("total", 0)
    n_pass  = s.get("pass", 0)
    n_fail  = s.get("fail", 0)
    n_other = total - n_pass - n_fail
    prate   = s.get("pass_rate", 0.0)

    top_fail = regression_data.get("failed_tests", [])[:10]
    fail_rows = ""
    for t in top_fail:
        fail_rows += (
            f"<tr><td><code>{t.get('test_name','')}</code></td>"
            f"<td>{t.get('seed','')}</td>"
            f"<td>{t.get('fail_msg','')[:80]}</td></tr>\n"
        )

    prate_cls = "g" if prate >= 98 else ("y" if prate >= 90 else "r")

    return f"""
<details class="section">
  <summary><h2>Regression Summary (S9)</h2></summary>
  <div style="display:flex;gap:20px;margin:12px 0;flex-wrap:wrap">
    <div style="background:#fff;border-radius:8px;padding:14px 22px;box-shadow:var(--shadow);min-width:100px;text-align:center">
      <div style="font-size:1.6rem;font-weight:700;color:var(--blue)">{total}</div><div style="font-size:.75rem;color:#888">Total</div>
    </div>
    <div style="background:#fff;border-radius:8px;padding:14px 22px;box-shadow:var(--shadow);min-width:100px;text-align:center">
      <div style="font-size:1.6rem;font-weight:700;color:var(--green)">{n_pass}</div><div style="font-size:.75rem;color:#888">Pass</div>
    </div>
    <div style="background:#fff;border-radius:8px;padding:14px 22px;box-shadow:var(--shadow);min-width:100px;text-align:center">
      <div style="font-size:1.6rem;font-weight:700;color:var(--red)">{n_fail}</div><div style="font-size:.75rem;color:#888">Fail</div>
    </div>
    <div style="background:#fff;border-radius:8px;padding:14px 22px;box-shadow:var(--shadow);min-width:100px;text-align:center">
      <div style="font-size:1.6rem;font-weight:700">{prate:.1f}%</div><div style="font-size:.75rem;color:#888">Pass Rate</div>
    </div>
  </div>
  {f'''<div class="tbl-wrap"><table>
    <thead><tr><th>Failed Test</th><th>Seed</th><th>Failure</th></tr></thead>
    <tbody>{fail_rows}</tbody>
  </table></div>''' if fail_rows else ""}
</details>"""


def render_recommended_actions(coverage_data: dict, milestone_results: dict) -> str:
    items = []

    # DV-F blocking checks
    dvf = milestone_results.get("dv_f", {})
    for metric, check in dvf.get("checks", {}).items():
        if not check.get("passed"):
            delta = check["required"] - check["actual"]
            items.append(f"Improve <b>{metric}</b>: currently {check['actual']}%, "
                         f"need +{delta:.1f}% to reach DV-F threshold ({check['required']}%)")

    # Stubs to implement
    for stub in coverage_data.get("stubs", {}).get("items", []):
        if stub.get("status") == "generated":
            items.append(f"Implement coverage stub: "
                         f"<code>{os.path.basename(stub.get('file',''))}</code> "
                         f"→ <code>{stub.get('coverage_target','')}</code>")

    # Exclusions needing manual review
    unreviewed = [e for e in coverage_data.get("exclusions",{}).get("items",[])
                  if e.get("reviewer") == "auto"]
    if unreviewed:
        items.append(f"Review {len(unreviewed)} auto-generated exclusion(s) in "
                     f"<code>exclusions/combined.el</code> before sign-off")

    if not items:
        items.append("No actions required. Design is ready for tape-out sign-off.")

    items_html = "".join(f"<li>{i}</li>" for i in items)
    return f"""
<div class="section">
  <h2>Recommended Actions</h2>
  <div class="actions">
    <ul>{items_html}</ul>
  </div>
</div>"""


def render_audit_trail(coverage_data: dict, regression_data: dict, timestamp: str) -> str:
    vdb_path   = coverage_data.get("vdb_path","—")
    urg_report = coverage_data.get("sources",{}).get("urg_report_dir","—")
    reg_run    = regression_data.get("run_dir","—")
    git_hash   = regression_data.get("git_hash","—")

    rows = [
        ("Report generated",   timestamp),
        ("VDB path",           vdb_path),
        ("URG report dir",     urg_report),
        ("Regression run dir", reg_run),
        ("Git commit (RTL/TB)",git_hash),
        ("Schema version",     coverage_data.get("schema_version","1.0")),
    ]
    rows_html = "".join(f"<tr><td><b>{k}</b></td><td><code>{v}</code></td></tr>" for k,v in rows)

    return f"""
<details class="section">
  <summary><h2>Audit Trail</h2></summary>
  <div class="tbl-wrap" style="margin-top:12px">
    <table><tbody>{rows_html}</tbody></table>
  </div>
</details>"""


# ══════════════════════════════════════════════════════════════════════════════
# Main report assembler
# ══════════════════════════════════════════════════════════════════════════════

def gen_signoff_report(coverage_data: dict, regression_data: dict,
                        assertions_data: dict, milestone_results: dict,
                        output_path: str, config: dict = None) -> str:
    """
    Generate the combined DV sign-off HTML report.
    Returns absolute path of written file.
    """
    if config is None:
        config = {}

    project   = config.get("project",   coverage_data.get("project_name", "project"))
    timestamp = config.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    title     = f"{project} — DV Sign-off Report"

    # Banner
    banner_cls, banner_txt = _milestone_status(milestone_results)
    banner_html = render_banner(milestone_results, project, timestamp)

    # Sections
    sections = [
        render_milestone_section(milestone_results),
        render_coverage_dashboard(coverage_data),
        render_functional_coverage(coverage_data),
        render_gap_analysis(coverage_data),
        render_assertions_section(assertions_data),
        render_regression_section(regression_data),
        render_recommended_actions(coverage_data, milestone_results),
        render_audit_trail(coverage_data, regression_data, timestamp),
    ]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="hdr">
  <h1>{title}</h1>
  <div class="meta">Generated: {timestamp}</div>
</div>
{banner_html}
<div class="container">
{"".join(sections)}
</div>
<div class="footer">DV Skills Sign-off Report &mdash; {timestamp}</div>
</body>
</html>"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out.resolve())


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def _load(path: str) -> dict:
    if path and os.path.isfile(path):
        try:
            return json.loads(Path(path).read_text())
        except Exception:
            pass
    return {}


def main():
    parser = argparse.ArgumentParser(description="Generate DV sign-off HTML report")
    parser.add_argument("--coverage",   required=True, help="dv_coverage_data.json")
    parser.add_argument("--regression", default="",    help="dv_regression_data.json")
    parser.add_argument("--assertions", default="",    help="dv_assertions_data.json")
    parser.add_argument("--milestone",  default="",    help="milestone_results.json")
    parser.add_argument("--project",    default="project")
    parser.add_argument("--out",        required=True, help="Output HTML path")
    args = parser.parse_args()

    coverage_data    = _load(args.coverage)
    regression_data  = _load(args.regression)
    assertions_data  = _load(args.assertions)
    milestone_results= _load(args.milestone)

    if not milestone_results:
        # Build minimal milestone from coverage data if available
        milestone_results = coverage_data.get("milestone_results", {})

    config = {
        "project":   args.project,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    out = gen_signoff_report(
        coverage_data, regression_data, assertions_data,
        milestone_results, args.out, config,
    )
    print(f"  Sign-off report: {out}")


if __name__ == "__main__":
    main()
