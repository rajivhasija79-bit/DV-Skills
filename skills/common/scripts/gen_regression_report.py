#!/usr/bin/env python3
"""
gen_regression_report.py — DV Skills HTML Regression Report Generator
Generates a self-contained HTML regression report from parsed sim log results.

Usage:
    from gen_regression_report import gen_regression_report
    gen_regression_report(results, output_path, run_config)

    python3 gen_regression_report.py results.json -o report.html
"""

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path


# ── HTML template ────────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --green:  #2ecc71;
    --red:    #e74c3c;
    --yellow: #f39c12;
    --blue:   #3498db;
    --grey:   #95a5a6;
    --dark:   #2c3e50;
    --light:  #ecf0f1;
    --white:  #ffffff;
    --shadow: 0 2px 6px rgba(0,0,0,0.12);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Roboto, monospace; background: #f4f6f9; color: var(--dark); }}
  .header {{ background: var(--dark); color: var(--white); padding: 24px 32px; }}
  .header h1 {{ font-size: 1.6rem; font-weight: 600; }}
  .header .meta {{ font-size: 0.85rem; color: #aab; margin-top: 6px; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}

  /* Summary cards */
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }}
  .card {{ flex: 1; min-width: 120px; background: var(--white); border-radius: 8px;
            padding: 16px 20px; box-shadow: var(--shadow); text-align: center; }}
  .card .num {{ font-size: 2rem; font-weight: 700; }}
  .card .lbl {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: #888; margin-top: 4px; }}
  .card.pass .num  {{ color: var(--green); }}
  .card.fail .num  {{ color: var(--red); }}
  .card.skip .num  {{ color: var(--yellow); }}
  .card.total .num {{ color: var(--blue); }}

  /* Pass rate bar */
  .progress-wrap {{ background: #ddd; border-radius: 20px; height: 16px; margin-bottom: 28px; overflow: hidden; }}
  .progress-bar  {{ height: 100%; border-radius: 20px; transition: width 0.4s; }}
  .progress-bar.good   {{ background: var(--green); }}
  .progress-bar.medium {{ background: var(--yellow); }}
  .progress-bar.bad    {{ background: var(--red); }}

  /* Section headings */
  h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 12px; padding-bottom: 6px;
        border-bottom: 2px solid var(--light); }}

  /* Tables */
  .tbl-wrap {{ overflow-x: auto; margin-bottom: 32px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--white);
            border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); font-size: 0.88rem; }}
  th {{ background: var(--dark); color: var(--white); padding: 10px 14px; text-align: left;
        font-weight: 500; white-space: nowrap; }}
  td {{ padding: 9px 14px; border-bottom: 1px solid #eee; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8f9ff; }}
  .badge {{ display: inline-block; border-radius: 4px; padding: 2px 8px;
             font-size: 0.78rem; font-weight: 600; white-space: nowrap; }}
  .badge-pass     {{ background: #d5f5e3; color: #1a7340; }}
  .badge-fail     {{ background: #fde8e8; color: #922b21; }}
  .badge-timeout  {{ background: #fef9e7; color: #7d6608; }}
  .badge-killed   {{ background: #fde8e8; color: #922b21; }}
  .badge-inc      {{ background: #f2f3f4; color: #555; }}
  code {{ background: #f2f3f4; padding: 1px 5px; border-radius: 3px;
           font-family: monospace; font-size: 0.82rem; }}

  /* Failure details */
  .fail-section {{ margin-bottom: 32px; }}
  .fail-block  {{ background: var(--white); border-left: 4px solid var(--red);
                  border-radius: 0 8px 8px 0; padding: 14px 18px; margin-bottom: 12px;
                  box-shadow: var(--shadow); }}
  .fail-block h3 {{ font-size: 0.95rem; color: var(--red); margin-bottom: 8px; }}
  .fail-block ul {{ padding-left: 18px; font-size: 0.85rem; }}
  .fail-block li {{ margin-bottom: 4px; }}
  .rerun-cmd {{ font-family: monospace; font-size: 0.82rem; background: #1e2733;
                color: #a8d8a8; padding: 10px 14px; border-radius: 6px; margin-top: 10px;
                white-space: pre-wrap; word-break: break-all; }}

  /* CHK_ID summary */
  .chk-fail {{ background: #fde8e8; }}
  .chk-pass  {{ background: #d5f5e3; }}

  /* Filter bar */
  .filter-bar {{ display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }}
  .filter-bar input {{ padding: 6px 12px; border: 1px solid #ccd; border-radius: 6px;
                        font-size: 0.85rem; width: 260px; }}
  .filter-bar select {{ padding: 6px 10px; border: 1px solid #ccd; border-radius: 6px;
                          font-size: 0.85rem; }}

  /* Collapsible */
  details summary {{ cursor: pointer; user-select: none; }}
  details summary::-webkit-details-marker {{ display: none; }}
  details summary::before {{ content: "▶ "; font-size: 0.75rem; }}
  details[open] summary::before {{ content: "▼ "; }}

  /* Footer */
  .footer {{ text-align: center; color: #aaa; font-size: 0.78rem; padding: 20px 0 32px; }}
</style>
</head>
<body>

<div class="header">
  <h1>{title}</h1>
  <div class="meta">
    Generated: {timestamp} &nbsp;|&nbsp;
    Run dir: <code style="color:#cde">{run_dir}</code> &nbsp;|&nbsp;
    Testlist: <code style="color:#cde">{testlist}</code>
    {extra_meta}
  </div>
</div>

<div class="container">

  <!-- Summary Cards -->
  <div class="cards">
    <div class="card total"><div class="num">{total}</div><div class="lbl">Total</div></div>
    <div class="card pass"><div class="num">{n_pass}</div><div class="lbl">Pass</div></div>
    <div class="card fail"><div class="num">{n_fail}</div><div class="lbl">Fail</div></div>
    <div class="card skip"><div class="num">{n_other}</div><div class="lbl">Incomplete/Timeout</div></div>
    <div class="card total"><div class="num">{pass_rate}%</div><div class="lbl">Pass Rate</div></div>
  </div>

  <!-- Pass Rate Bar -->
  <div class="progress-wrap">
    <div class="progress-bar {bar_class}" style="width:{pass_rate}%"></div>
  </div>

  <!-- CHK_ID Failures Summary -->
  {chk_id_section}

  <!-- Per-Test Results Table -->
  <h2>Test Results</h2>
  <div class="filter-bar">
    <input type="text" id="filterInput" placeholder="Filter by test name or CHK_ID..."
           onkeyup="filterTable()">
    <select id="statusFilter" onchange="filterTable()">
      <option value="">All Status</option>
      <option value="PASS">PASS</option>
      <option value="FAIL">FAIL</option>
      <option value="TIMEOUT">TIMEOUT</option>
      <option value="INCOMPLETE">INCOMPLETE</option>
    </select>
  </div>
  <div class="tbl-wrap">
    <table id="resultsTable">
      <thead>
        <tr>
          <th>#</th>
          <th>Status</th>
          <th>Test Name</th>
          <th>Seed</th>
          <th>UVM Err</th>
          <th>UVM Fatal</th>
          <th>CHK Pass</th>
          <th>CHK Fail</th>
          <th>Log</th>
          <th>Rerun</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>

  <!-- Failure Details -->
  {fail_details}

  <!-- Configuration -->
  <details>
    <summary><h2 style="display:inline">Run Configuration</h2></summary>
    <div class="tbl-wrap" style="margin-top:12px">
      <table>
        <tbody>
          {config_rows}
        </tbody>
      </table>
    </div>
  </details>

</div>

<div class="footer">DV Skills Regression Report &mdash; {timestamp}</div>

<script>
function filterTable() {{
  var input  = document.getElementById('filterInput').value.toLowerCase();
  var status = document.getElementById('statusFilter').value.toUpperCase();
  var rows   = document.getElementById('resultsTable').getElementsByTagName('tr');
  for (var i = 1; i < rows.length; i++) {{
    var row    = rows[i];
    var text   = row.textContent.toLowerCase();
    var rowSt  = row.getAttribute('data-status') || '';
    var show   = (!input || text.indexOf(input) !== -1) &&
                 (!status || rowSt === status);
    row.style.display = show ? '' : 'none';
  }}
}}
// Highlight failing rows on load
document.querySelectorAll('tr[data-status="FAIL"]').forEach(function(r) {{
  r.style.background = '#fff8f8';
}});
</script>
</body>
</html>"""


# ── Badge helpers ────────────────────────────────────────────────────────────────

def _badge(status: str) -> str:
    cls = {
        "PASS": "pass", "FAIL": "fail",
        "TIMEOUT": "timeout", "KILLED": "killed",
    }.get(status.upper(), "inc")
    return f'<span class="badge badge-{cls}">{status}</span>'


def _log_link(path: str) -> str:
    if not path:
        return "—"
    name = os.path.basename(path)
    return f'<a href="file://{path}" title="{path}">{name}</a>'


def _rerun_cmd(result: dict, sim_dir: str = ".") -> str:
    test = result.get("test_name") or "unknown_test"
    seed = result.get("seed") or 1
    return (f"./simv +UVM_TESTNAME={test} +ntb_random_seed={seed} "
            f"+UVM_VERBOSITY=UVM_MEDIUM -l rerun_{test}_{seed}.log")


# ── CHK_ID Section ───────────────────────────────────────────────────────────────

def _build_chk_id_section(results: list) -> str:
    all_failed: dict = {}
    all_passed: set = set()
    for r in results:
        for chk_id, cnt in r.get("chk_fail", {}).items():
            all_failed[chk_id] = all_failed.get(chk_id, 0) + cnt
        all_passed.update(r.get("chk_pass", {}).keys())

    if not all_failed:
        return ""

    rows = ""
    for chk_id in sorted(all_failed.keys()):
        fail_cnt = all_failed[chk_id]
        pass_cnt = sum(r.get("chk_pass", {}).get(chk_id, 0) for r in results)
        rows += (f'<tr class="chk-fail"><td><code>{chk_id}</code></td>'
                 f'<td style="color:#922b21;font-weight:600">{fail_cnt}</td>'
                 f'<td>{pass_cnt}</td></tr>\n')

    return f"""
<h2>Failing CHK_IDs</h2>
<div class="tbl-wrap">
  <table>
    <thead><tr><th>CHK_ID</th><th>Fail Count</th><th>Pass Count</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""


# ── Failure details section ──────────────────────────────────────────────────────

def _build_fail_details(results: list) -> str:
    failed = [r for r in results if r.get("status") in ("FAIL", "TIMEOUT", "KILLED", "INCOMPLETE")]
    if not failed:
        return ""

    blocks = ""
    for r in failed:
        test  = r.get("test_name") or "unknown_test"
        seed  = r.get("seed") or "?"
        log   = r.get("log_path", "")
        status = r.get("status", "FAIL")
        msgs  = r.get("fail_messages", [])

        msg_html = ""
        if msgs:
            items = "".join(
                f'<li><code>{m["chk_id"]}</code> (line {m["line"]}): {m["message"][:120]}</li>'
                for m in msgs[:20]
            )
            if len(msgs) > 20:
                items += f"<li><em>...{len(msgs)-20} more failures</em></li>"
            msg_html = f"<ul>{items}</ul>"
        elif r.get("uvm_fatal", 0) > 0 or r.get("uvm_error", 0) > 0:
            msg_html = (f"<p>UVM_FATAL={r.get('uvm_fatal',0)}  "
                        f"UVM_ERROR={r.get('uvm_error',0)}</p>")

        rerun = _rerun_cmd(r)

        blocks += f"""
<div class="fail-block">
  <h3>{_badge(status)} {test} (seed={seed})</h3>
  {msg_html}
  <div class="rerun-cmd">{rerun}</div>
</div>"""

    return f"""
<div class="fail-section">
  <h2>Failure Details</h2>
  {blocks}
</div>"""


# ── Config rows ──────────────────────────────────────────────────────────────────

def _build_config_rows(config: dict) -> str:
    rows = ""
    for k, v in config.items():
        rows += f"<tr><td><b>{k}</b></td><td><code>{v}</code></td></tr>\n"
    return rows


# ── Main generator ───────────────────────────────────────────────────────────────

def gen_regression_report(results: list, output_path: str, run_config: dict = None) -> str:
    """
    Generate an HTML regression report.

    Args:
        results:     List of dicts from parse_sim_log.parse_log()
        output_path: Where to write the HTML file
        run_config:  Optional dict with run metadata (project, testlist, seeds, etc.)

    Returns:
        Absolute path of the written report.
    """
    if run_config is None:
        run_config = {}

    # ── Aggregate stats ────────────────────────────────────────────────────
    total   = len(results)
    n_pass  = sum(1 for r in results if r.get("status") == "PASS")
    n_fail  = sum(1 for r in results if r.get("status") == "FAIL")
    n_other = total - n_pass - n_fail
    pass_rate = round(100.0 * n_pass / total, 1) if total > 0 else 0.0

    if   pass_rate >= 90: bar_class = "good"
    elif pass_rate >= 60: bar_class = "medium"
    else:                 bar_class = "bad"

    project   = run_config.get("project", "regression")
    testlist  = run_config.get("testlist", "—")
    run_dir   = run_config.get("run_dir", os.getcwd())
    timestamp = run_config.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    title     = f"{project} Regression Report"

    # Extra meta
    extra_parts = []
    if run_config.get("grid"):
        extra_parts.append(f"Grid: <code style='color:#cde'>{run_config['grid']}</code>")
    if run_config.get("seeds"):
        extra_parts.append(f"Seeds: {run_config['seeds']}")
    extra_meta = ("&nbsp;|&nbsp;" + "&nbsp;|&nbsp;".join(extra_parts)) if extra_parts else ""

    # ── Build rows ────────────────────────────────────────────────────────
    row_html = ""
    for idx, r in enumerate(results, start=1):
        status   = r.get("status", "INCOMPLETE")
        test     = r.get("test_name") or "—"
        seed     = str(r.get("seed") or "—")
        uvm_err  = r.get("uvm_error", 0)
        uvm_fat  = r.get("uvm_fatal", 0)
        chk_p    = r.get("chk_pass_total", 0)
        chk_f    = r.get("chk_fail_total", 0)
        log_path = r.get("log_path", "")
        rerun    = _rerun_cmd(r)

        err_cell = f'<span style="color:var(--red);font-weight:600">{uvm_err}</span>' if uvm_err else str(uvm_err)
        fat_cell = f'<span style="color:var(--red);font-weight:600">{uvm_fat}</span>' if uvm_fat else str(uvm_fat)
        chk_f_cell = f'<span style="color:var(--red);font-weight:600">{chk_f}</span>' if chk_f else str(chk_f)

        row_html += (
            f'<tr data-status="{status}">'
            f'<td>{idx}</td>'
            f'<td>{_badge(status)}</td>'
            f'<td><code>{test}</code></td>'
            f'<td>{seed}</td>'
            f'<td>{err_cell}</td>'
            f'<td>{fat_cell}</td>'
            f'<td>{chk_p}</td>'
            f'<td>{chk_f_cell}</td>'
            f'<td>{_log_link(log_path)}</td>'
            f'<td><details><summary>rerun</summary>'
            f'<div class="rerun-cmd">{rerun}</div></details></td>'
            f'</tr>\n'
        )

    # ── Sections ──────────────────────────────────────────────────────────
    chk_id_section = _build_chk_id_section(results)
    fail_details   = _build_fail_details(results)
    config_rows    = _build_config_rows(run_config)

    # ── Render ────────────────────────────────────────────────────────────
    html = _HTML_TEMPLATE.format(
        title=title,
        timestamp=timestamp,
        run_dir=run_dir,
        testlist=testlist,
        extra_meta=extra_meta,
        total=total,
        n_pass=n_pass,
        n_fail=n_fail,
        n_other=n_other,
        pass_rate=pass_rate,
        bar_class=bar_class,
        chk_id_section=chk_id_section,
        rows=row_html,
        fail_details=fail_details,
        config_rows=config_rows,
    )

    # ── Write ─────────────────────────────────────────────────────────────
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out.resolve())


# ── CLI ──────────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate HTML regression report from parsed log results")
    parser.add_argument("results_json", help="JSON file with list of parse_log() results")
    parser.add_argument("-o", "--output", default="regression_report.html", help="Output HTML file")
    parser.add_argument("--project",  default="regression", help="Project name for report title")
    parser.add_argument("--testlist", default="—",          help="Test list file used")
    parser.add_argument("--run-dir",  default=os.getcwd(),  help="Regression run directory")
    args = parser.parse_args()

    with open(args.results_json) as fh:
        results = json.load(fh)

    config = {
        "project":   args.project,
        "testlist":  args.testlist,
        "run_dir":   args.run_dir,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    out = gen_regression_report(results, args.output, config)
    print(f"  Report written: {out}")


if __name__ == "__main__":
    main()
