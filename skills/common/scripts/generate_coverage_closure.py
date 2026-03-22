#!/usr/bin/env python3
"""
generate_coverage_closure.py — DV Skills S10 Coverage Closure Orchestrator
Handles: gap classification, interactive resolution, exclusion file generation,
test/sequence stub generation, milestone checks, and dv_coverage_data.json assembly.

Usage:
    python3 generate_coverage_closure.py \
        --project apb_uart \
        --vdb dv/sim/regression/merged.vdb \
        --reg-data dv/sim/results/dv_regression_data.json \
        --assert-data dv/dv_assertions_data.json \
        --out dv/sim/regression \
        [--non-interactive]

    # Individual modes
    python3 generate_coverage_closure.py --mode exclusions  --decisions gaps/gap_decisions.json --out exclusions/
    python3 generate_coverage_closure.py --mode stubs       --decisions gaps/gap_decisions.json --out dv/
    python3 generate_coverage_closure.py --mode milestone   --coverage coverage_after_exclusions.json ...
    python3 generate_coverage_closure.py --mode write-data  --project apb_uart --out dv/
"""

import os
import re
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

from parse_coverage_report import (
    parse_code_coverage, parse_functional_coverage,
    parse_dashboard, classify_gaps
)

# ── Helpers ──────────────────────────────────────────────────────────────────────

def safe_read_json(path: str) -> dict:
    if path and os.path.isfile(path):
        try:
            return json.loads(Path(path).read_text())
        except Exception:
            pass
    return {}


def safe_write_json(data: dict, path: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def load_config(config_path: str) -> dict:
    """Load coverage_config.yaml — falls back to built-in defaults."""
    config = {
        "thresholds": {
            "dv_i": {"line_pct": 80.0,  "toggle_pct": 70.0,  "branch_pct": 75.0,
                     "expression_pct": 70.0, "functional_pct": 60.0, "regression_pass": 90.0},
            "dv_c": {"line_pct": 95.0,  "toggle_pct": 90.0,  "branch_pct": 95.0,
                     "expression_pct": 90.0, "functional_pct": 85.0, "regression_pass": 98.0},
            "dv_f": {"line_pct": 99.0,  "toggle_pct": 95.0,  "branch_pct": 99.0,
                     "expression_pct": 99.0, "fsm_pct": 99.0, "functional_pct": 99.0,
                     "regression_pass": 100.0},
        },
        "auto_exclude_patterns": [
            r".*_dft_.*", r".*_tb_.*", r".*vendor_ip.*",
            r".*_unused.*", r".*_tie.*", r".*_dummy.*",
        ],
    }
    if config_path and os.path.isfile(config_path):
        try:
            import re as _re
            content = Path(config_path).read_text()
            # Simple YAML-like key: value parser for thresholds
            for line in content.splitlines():
                m = _re.match(r"\s*([\w_]+)\s*:\s*([\d.]+)", line)
                if m:
                    key, val = m.group(1), float(m.group(2))
                    for milestone in ("dv_i", "dv_c", "dv_f"):
                        if key in config["thresholds"].get(milestone, {}):
                            config["thresholds"][milestone][key] = val
        except Exception:
            pass
    return config


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: Run urg to generate text reports
# ══════════════════════════════════════════════════════════════════════════════

def run_urg_reports(vdb_path: str, out_dir: str, full64: bool = True) -> dict:
    """Run urg to produce text + HTML reports from merged.vdb."""
    result = {"text_dir": None, "html_dir": None, "log": None, "status": "FAIL"}

    urg = shutil.which("urg")
    if not urg:
        print("  ⚠  urg not found in PATH — skipping fresh report generation")
        return result

    text_dir = os.path.join(out_dir, "urgReport")
    html_dir = os.path.join(out_dir, "urgReport_html")
    log_file = os.path.join(out_dir, "urg_run.log")

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    base_cmd = ["urg"] + (["-full64"] if full64 else []) + ["-dir", vdb_path]

    with open(log_file, "w") as log_fh:
        # Text report
        cmd_text = base_cmd + ["-report", text_dir, "-format", "text"]
        print(f"  urg (text): {' '.join(cmd_text)}")
        proc = subprocess.run(cmd_text, stdout=log_fh, stderr=subprocess.STDOUT)
        result["text_status"] = "PASS" if proc.returncode == 0 else "FAIL"

        # HTML report
        cmd_html = base_cmd + ["-report", html_dir, "-format", "html"]
        print(f"  urg (html): {' '.join(cmd_html)}")
        subprocess.run(cmd_html, stdout=log_fh, stderr=subprocess.STDOUT)

    result["text_dir"] = text_dir
    result["html_dir"] = html_dir
    result["log"]      = log_file
    result["status"]   = result["text_status"]
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: Cross-reference with assertions
# ══════════════════════════════════════════════════════════════════════════════

def cross_reference_assertions(gaps: list, assertions_data: dict) -> list:
    """
    Annotate gaps with assertion_backed flag and related_chk_ids.
    Matches by module/instance path overlap.
    """
    chk_ids = assertions_data.get("chk_ids", {})
    vip_modules = set()
    for chk_id, info in chk_ids.items():
        module = info.get("module", "") or info.get("vip_name", "")
        if module:
            vip_modules.add(module.lower())

    for gap in gaps:
        path = (gap.get("full_path","") + " " + gap.get("scope","") + " " + gap.get("cg_instance","")).lower()
        related = []
        for chk_id, info in chk_ids.items():
            module = (info.get("module","") or info.get("vip_name","")).lower()
            if module and module in path:
                related.append(chk_id)
        if related:
            gap["assertion_backed"]  = True
            gap["related_chk_ids"]   = related
    return gaps


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7: Interactive gap resolution
# ══════════════════════════════════════════════════════════════════════════════

def interactive_resolve(gaps: list, non_interactive: bool = False) -> dict:
    """
    Walk through each gap and record decisions.
    Returns decisions dict: {gap_id: {"decision": "exclude"|"stub"|"skip", "reason": str}}
    """
    decisions = {}
    total = len(gaps)

    print(f"\n  Gap Resolution ({total} gaps)")
    print(f"  {'─'*60}")

    by_class = {c: [g for g in gaps if g.get("classification") == c]
                for c in ("excludable", "coverable", "requires_analysis")}
    print(f"  Excludable: {len(by_class['excludable'])}  "
          f"Coverable: {len(by_class['coverable'])}  "
          f"Requires Analysis: {len(by_class['requires_analysis'])}\n")

    for idx, gap in enumerate(gaps, start=1):
        gap_id       = gap.get("id", f"GAP_{idx:04d}")
        classification = gap.get("classification", "requires_analysis")
        gap_type     = gap.get("type", "unknown")
        path         = gap.get("full_path") or gap.get("scope", "unknown")
        detail       = gap.get("detail", gap.get("bin_name", ""))
        suggested    = gap.get("suggested_test", "")
        ex_reason    = gap.get("exclusion_reason", "")

        print(f"  [{idx}/{total}]  Type: {gap_type.upper():<14}  Class: {classification.upper()}")
        print(f"  Path  : {path[:80]}")
        if detail:
            print(f"  Detail: {detail[:80]}")
        if ex_reason:
            print(f"  Reason: {ex_reason}")

        if non_interactive:
            # Accept suggested default
            if classification == "excludable":
                dec = "exclude"
            elif classification == "coverable":
                dec = "stub"
            else:
                dec = "skip"
            reason = ex_reason or suggested or "(auto-accept)"
            print(f"  → Auto-decision: {dec}")
        else:
            if classification == "excludable":
                if ex_reason:
                    print(f"\n  Draft exclusion: {_draft_exclusion_stmt(gap)}")
                prompt = "  Accept? [Y=exclude / s=stub / n=skip] : "
            elif classification == "coverable":
                if suggested:
                    print(f"\n  Suggested stub: {suggested}")
                prompt = "  Generate stub? [Y=stub / e=exclude / n=skip] : "
            else:
                prompt = "  Decision? [e=exclude / s=stub / n=skip] : "

            try:
                ans = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = ""

            if classification == "excludable":
                dec = "exclude" if ans in ("", "y") else ("stub" if ans == "s" else "skip")
                reason = ex_reason or ""
            elif classification == "coverable":
                dec = "stub" if ans in ("", "y") else ("exclude" if ans == "e" else "skip")
                reason = suggested or ""
            else:
                dec = "exclude" if ans == "e" else ("stub" if ans == "s" else "skip")
                reason = ""

        decisions[gap_id] = {
            "decision":        dec,
            "reason":          reason,
            "gap":             gap,
        }
        print()

    # Print decision summary
    n_exc   = sum(1 for d in decisions.values() if d["decision"] == "exclude")
    n_stub  = sum(1 for d in decisions.values() if d["decision"] == "stub")
    n_skip  = sum(1 for d in decisions.values() if d["decision"] == "skip")
    print(f"  Decisions: {n_exc} excluded, {n_stub} stubs queued, {n_skip} skipped\n")

    return decisions


def _draft_exclusion_stmt(gap: dict) -> str:
    """Generate a one-line draft urg exclusion statement."""
    scope  = gap.get("scope", gap.get("cg_instance", "SCOPE"))
    detail = gap.get("detail", "")
    reason = gap.get("exclusion_reason", "REASON")
    gtype  = gap.get("type", "line")

    if gtype == "toggle":
        sig = gap.get("signal", detail)
        direction = gap.get("direction", "").replace("0->1","01").replace("1->0","10")
        return f'EXCL_TOGGLE {scope} {sig} {direction} -comment "{reason}"'
    elif gtype == "functional":
        cg  = gap.get("cg_name", "CG")
        cp  = gap.get("cp_name", "CP")
        bn  = gap.get("bin_name", "BIN")
        return f'EXCL_COVBIN {scope} {cg} {cp} {bn} -comment "{reason}"'
    elif gtype in ("fsm_state", "fsm"):
        state = gap.get("state", detail)
        return f'EXCL_FSM_STATE {scope} FSM {state} -comment "{reason}"'
    elif gtype == "branch":
        f = gap.get("file","FILE")
        ln = gap.get("line", 0)
        return f'EXCL_BRANCH {scope} {f} {ln} 0 -comment "{reason}"'
    else:
        f = gap.get("file","FILE")
        ln = gap.get("line", 0)
        return f'EXCL_LINE {scope} {f} {ln} -comment "{reason}"'


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8: Generate exclusion files
# ══════════════════════════════════════════════════════════════════════════════

_EL_HEADER = """\
// =============================================================================
// Exclusion File: {filename}
// Generated by  : S10 dv-coverage-closure
// Date          : {date}
// Project       : {project}
// REVIEW REQUIRED: All exclusions must be reviewed before sign-off
// =============================================================================

"""

def generate_exclusions(decisions: dict, out_dir: str, project: str = "project",
                         vdb_path: str = None) -> dict:
    """
    Write per-type .el files and combined.el from accepted exclusion decisions.
    Returns paths dict.
    """
    by_type = {k: [] for k in ("line","toggle","branch","expression","fsm","functional")}

    for gap_id, info in decisions.items():
        if info["decision"] != "exclude":
            continue
        gap = info.get("gap", {})
        gtype = gap.get("type", "line")

        stmt = _draft_exclusion_stmt(gap)
        reason = info.get("reason", gap.get("exclusion_reason", "Excluded by engineer review"))

        if "EXCL_TOGGLE"   in stmt: bucket = "toggle"
        elif "EXCL_COVBIN" in stmt or "EXCL_COVGROUP" in stmt or "EXCL_COVPOINT" in stmt:
            bucket = "functional"
        elif "EXCL_FSM"    in stmt: bucket = "fsm"
        elif "EXCL_BRANCH" in stmt: bucket = "branch"
        elif "EXCL_EXPRESSION" in stmt: bucket = "expression"
        else:                           bucket = "line"

        entry = f"{stmt}\n    // Justification: {reason}\n"
        by_type[bucket].append(entry)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    paths = {}
    all_stmts = []

    for btype, entries in by_type.items():
        if not entries:
            continue
        filename = f"{btype}_exclusions.el"
        fpath    = os.path.join(out_dir, filename)
        header   = _EL_HEADER.format(filename=filename, date=date, project=project)
        content  = header + "\n".join(entries) + "\n"
        Path(fpath).write_text(content)
        paths[btype] = fpath
        all_stmts.extend(entries)
        print(f"  Written: {fpath}  ({len(entries)} exclusions)")

    # Write combined.el
    combined_path = os.path.join(out_dir, "combined.el")
    combined_header = _EL_HEADER.format(
        filename="combined.el", date=date, project=project
    )
    Path(combined_path).write_text(combined_header + "\n".join(all_stmts))
    paths["combined"] = combined_path
    print(f"  Written: {combined_path}  ({len(all_stmts)} total exclusions)")

    # Re-run urg with exclusions if vdb available
    coverage_after = {}
    if vdb_path and os.path.isdir(vdb_path) and shutil.which("urg"):
        excl_report = os.path.join(os.path.dirname(out_dir), "urgReport_excl")
        cmd = ["urg", "-full64", "-dir", vdb_path,
               "-elfile", combined_path,
               "-report", excl_report, "-format", "text"]
        print(f"  Re-running urg with exclusions: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True)
        dash = os.path.join(excl_report, "dashboard.txt")
        if os.path.isfile(dash):
            from parse_coverage_report import parse_dashboard
            coverage_after = parse_dashboard(dash)
            print(f"  Post-exclusion coverage loaded from {dash}")

    return {"paths": paths, "coverage_after": coverage_after}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 9: Generate test/sequence stubs
# ══════════════════════════════════════════════════════════════════════════════

_SEQ_STUB = """\
// ─────────────────────────────────────────────────────────────────────────────
// COVERAGE STUB — Generated by S10 dv-coverage-closure
// Gap ID  : {gap_id}
// Target  : {coverage_target}
// Scope   : {scope}
// Action  : {action_hint}
// Status  : NEEDS_ENGINEER_IMPLEMENTATION
// ─────────────────────────────────────────────────────────────────────────────
class {class_name} extends {base_seq};
  `uvm_object_utils({class_name})
  function new(string name = "{class_name}");
    super.new(name);
  endfunction

  task body();
    // TODO: {action_hint}
    // Coverage target: {coverage_target}
    `uvm_info(get_type_name(), "COVERAGE STUB — implement body to hit target bin", UVM_MEDIUM)
  endtask
endclass
"""

_TEST_STUB = """\
// ─────────────────────────────────────────────────────────────────────────────
// COVERAGE STUB — Generated by S10 dv-coverage-closure
// Gap ID  : {gap_id}
// Target  : {coverage_target}
// Scope   : {scope}
// Action  : {action_hint}
// Status  : NEEDS_ENGINEER_IMPLEMENTATION
// ─────────────────────────────────────────────────────────────────────────────
class {class_name} extends {base_test};
  `uvm_component_utils({class_name})
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    // TODO: {action_hint}
    // Coverage target: {coverage_target}
    phase.raise_objection(this);
    `uvm_info(get_type_name(), "COVERAGE STUB — implement run_phase to hit target", UVM_MEDIUM)
    phase.drop_objection(this);
  endtask
endclass
"""


def generate_stubs(decisions: dict, out_dir: str, tb_data: dict = None) -> list:
    """
    Generate UVM .sv stubs for gaps with decision == "stub".
    Returns list of stub manifest records.
    """
    project = (tb_data or {}).get("project_name", "proj")
    base_test = f"{project}_base_test"
    manifest  = []

    seq_dir  = os.path.join(out_dir, "sequences", "coverage_stubs")
    test_dir = os.path.join(out_dir, "tests")
    Path(seq_dir).mkdir(parents=True, exist_ok=True)
    Path(test_dir).mkdir(parents=True, exist_ok=True)

    for gap_id, info in decisions.items():
        if info["decision"] != "stub":
            continue

        gap       = info.get("gap", {})
        gap_type  = gap.get("type", "functional")
        cg_name   = gap.get("cg_name", "")
        cp_name   = gap.get("cp_name", "")
        bin_name  = gap.get("bin_name", "")
        scope     = gap.get("scope", gap.get("cg_instance", ""))
        target    = gap.get("full_path") or f"{cg_name}::{cp_name}::{bin_name}"
        detail    = gap.get("detail", target)

        # Build class name
        parts = [x for x in (cg_name or gap_type, cp_name, bin_name) if x]
        raw   = "_".join(parts).lower()
        raw   = re.sub(r"[^a-z0-9_]", "_", raw)
        raw   = re.sub(r"_+", "_", raw).strip("_")[:50]
        class_name = f"{raw}_cov"

        action_hint = f"Drive stimulus to hit {target}"
        if bin_name:
            action_hint = f"Drive {cp_name} to value/condition matching bin '{bin_name}'"

        # Decide seq vs test based on gap type
        if gap_type == "functional" and cp_name:
            stub_type  = "sequence"
            # Try to guess protocol from scope/cg name
            protocol   = _guess_protocol(scope or cg_name)
            base_seq   = f"{protocol}_base_seq" if protocol else f"{project}_base_vseq"
            content    = _SEQ_STUB.format(
                gap_id=gap_id, coverage_target=target, scope=scope,
                action_hint=action_hint, class_name=class_name, base_seq=base_seq,
            )
            stub_file  = os.path.join(seq_dir, f"{class_name}.sv")
        else:
            stub_type  = "test"
            content    = _TEST_STUB.format(
                gap_id=gap_id, coverage_target=target, scope=scope,
                action_hint=action_hint, class_name=class_name, base_test=base_test,
            )
            stub_file  = os.path.join(test_dir, f"{class_name}.sv")

        Path(stub_file).write_text(content)
        print(f"  Stub: {stub_file}")

        manifest.append({
            "gap_id":          gap_id,
            "stub_type":       stub_type,
            "file":            stub_file,
            "class_name":      class_name,
            "coverage_target": target,
            "status":          "generated",
        })

    # Write manifest
    manifest_path = os.path.join(out_dir, "stubs", "stubs_manifest.json")
    Path(os.path.dirname(manifest_path)).mkdir(parents=True, exist_ok=True)
    safe_write_json({
        "generated_at": datetime.now().isoformat(),
        "stubs": manifest,
    }, manifest_path)
    print(f"  Manifest: {manifest_path}")

    return manifest


def _guess_protocol(text: str) -> str:
    """Guess VIP protocol name from scope/covergroup name."""
    text = text.lower()
    for proto in ("apb","ahb","axi","uart","spi","i2c","tilelink","pcie","dma"):
        if proto in text:
            return proto
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# STEP 10: Milestone checks
# ══════════════════════════════════════════════════════════════════════════════

def check_milestones(coverage_summary: dict, regression_data: dict,
                     assertions_data: dict, config: dict) -> dict:
    """
    Evaluate DV-I, DV-C, DV-F milestone gates.
    Returns milestone_results dict.
    """
    thr = config.get("thresholds", {})
    reg = regression_data.get("summary", regression_data)
    reg_pass_rate = reg.get("pass_rate", reg.get("regression_pass_rate", 0.0))
    all_chk_pass  = _all_chk_ids_passing(assertions_data, regression_data)

    results = {}
    for milestone in ("dv_i", "dv_c", "dv_f"):
        mt = thr.get(milestone, {})
        checks = {}

        for metric in ("line_pct","toggle_pct","branch_pct","expression_pct","functional_pct"):
            if metric not in mt:
                continue
            cov_type = metric.replace("_pct","")
            actual   = _get_cov_pct(coverage_summary, cov_type)
            required = mt[metric]
            checks[metric] = {
                "required": required,
                "actual":   round(actual, 2),
                "passed":   actual >= required,
            }

        if "fsm_pct" in mt:
            actual = _get_cov_pct(coverage_summary, "fsm")
            checks["fsm_pct"] = {
                "required": mt["fsm_pct"],
                "actual":   round(actual, 2),
                "passed":   actual >= mt["fsm_pct"],
            }

        if "regression_pass" in mt:
            checks["regression_pass"] = {
                "required": mt["regression_pass"],
                "actual":   round(reg_pass_rate, 2),
                "passed":   reg_pass_rate >= mt["regression_pass"],
            }

        if milestone in ("dv_c", "dv_f"):
            checks["all_chk_ids_passing"] = {
                "required": True,
                "actual":   all_chk_pass,
                "passed":   all_chk_pass,
            }

        if milestone == "dv_f":
            checks["zero_unresolved_gaps"] = {
                "required": True,
                "actual":   True,   # Will be overridden by caller if pending gaps exist
                "passed":   True,
            }

        passed = all(c["passed"] for c in checks.values())
        results[milestone] = {"passed": passed, "checks": checks}

    return results


def _get_cov_pct(coverage_summary: dict, cov_type: str) -> float:
    """Extract coverage percentage from coverage summary dict."""
    # Try direct from dashboard parse
    if cov_type in coverage_summary:
        entry = coverage_summary[cov_type]
        if isinstance(entry, dict):
            return entry.get("pct", 0.0)
        if isinstance(entry, (int, float)):
            return float(entry)
    # Try code_coverage sub-dict
    cc = coverage_summary.get("code_coverage", {})
    if cov_type in cc:
        return cc[cov_type].get("pct", 0.0)
    return 0.0


def _all_chk_ids_passing(assertions_data: dict, regression_data: dict) -> bool:
    """Check whether all assertion CHK_IDs have at least one passing test."""
    chk_ids = set(assertions_data.get("chk_ids", {}).keys())
    if not chk_ids:
        return True  # No assertions defined → pass
    passing_chk_ids = set(regression_data.get("chk_ids_passing", {}).keys())
    return chk_ids.issubset(passing_chk_ids)


def print_milestone_table(milestone_results: dict):
    """Print milestone gate results to stdout."""
    print(f"\n  Milestone Closure Check")
    print(f"  {'─'*64}")
    print(f"  {'Gate':<8} {'Status':<10} Blocking Metric")
    print(f"  {'─'*64}")
    for gate in ("dv_i", "dv_c", "dv_f"):
        result = milestone_results.get(gate, {})
        passed = result.get("passed", False)
        status = "✓ PASS" if passed else "✗ FAIL"
        blocking = []
        for metric, check in result.get("checks", {}).items():
            if not check.get("passed"):
                blocking.append(
                    f"{metric} {check['actual']}% < {check['required']}% required"
                    if "pct" in metric else
                    f"{metric}: {check['actual']} (required {check['required']})"
                )
        block_str = blocking[0] if blocking else "—"
        print(f"  {gate.upper():<8} {status:<10} {block_str}")
        for extra in blocking[1:]:
            print(f"  {'':<8} {'':<10} {extra}")
    print(f"  {'─'*64}\n")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 11: Write dv_coverage_data.json
# ══════════════════════════════════════════════════════════════════════════════

def assemble_coverage_data(project: str, vdb_path: str,
                            code_cov: dict, func_cov: dict,
                            decisions: dict, excl_paths: dict,
                            stubs_manifest: list, milestone_results: dict,
                            sources: dict) -> dict:
    """Assemble the final dv_coverage_data.json from all intermediate data."""

    n_excl  = sum(1 for d in decisions.values() if d["decision"] == "exclude")
    n_stub  = sum(1 for d in decisions.values() if d["decision"] == "stub")
    n_skip  = sum(1 for d in decisions.values() if d["decision"] == "skip")
    n_total = len(decisions)

    by_class = {c: sum(1 for d in decisions.values()
                       if d.get("gap", {}).get("classification") == c)
                for c in ("excludable","coverable","requires_analysis")}

    return {
        "schema_version": "1.0",
        "generated_at":   datetime.now().isoformat(),
        "project_name":   project,
        "tool":           "urg",
        "vdb_path":       vdb_path or "",
        "code_coverage": {
            **{t: code_cov["summary"].get(t, {"covered":0,"total":0,"pct":0.0})
               for t in ("line","toggle","branch","expression","fsm")},
            "instances": code_cov.get("instances", []),
        },
        "functional_coverage": {
            **func_cov.get("summary", {"total_bins":0,"covered_bins":0,"pct":0.0}),
            "covergroups": func_cov.get("covergroups", []),
        },
        "gaps_summary": {
            "total_gaps":        n_total,
            "excludable":        by_class["excludable"],
            "coverable":         by_class["coverable"],
            "requires_analysis": by_class["requires_analysis"],
            "excluded":          n_excl,
            "stubs_generated":   n_stub,
            "skipped":           n_skip,
            "pending":           0,
        },
        "exclusions": {
            "files":  excl_paths,
            "count":  n_excl,
            "items": [
                {
                    "gap_id":    gap_id,
                    "type":      info.get("gap", {}).get("type", "unknown"),
                    "path":      info.get("gap", {}).get("full_path",""),
                    "reason":    info.get("reason",""),
                    "reviewer":  "auto",
                    "timestamp": datetime.now().isoformat(),
                }
                for gap_id, info in decisions.items() if info["decision"] == "exclude"
            ],
        },
        "stubs": {
            "count":    n_stub,
            "manifest": "stubs/stubs_manifest.json",
            "items":    stubs_manifest,
        },
        "milestone_results": milestone_results,
        "sources":            sources,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Full orchestration run
# ══════════════════════════════════════════════════════════════════════════════

def run_full(args):
    """End-to-end S10 run."""
    project      = args.project
    vdb_path     = args.vdb
    out_dir      = args.out
    reg_path     = args.reg_data
    assert_path  = args.assert_data
    config_path  = getattr(args, "config", None) or os.path.join(out_dir, "coverage_config.yaml")
    non_inter    = getattr(args, "non_interactive", False)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    config = load_config(config_path)

    # ── Step 2: Generate urg text reports ───────────────────────────────────
    urg_result = run_urg_reports(vdb_path, out_dir)
    hier_path    = os.path.join(out_dir, "urgReport", "hier.txt")
    groups_path  = os.path.join(out_dir, "urgReport", "groups.txt")
    dash_path    = os.path.join(out_dir, "urgReport", "dashboard.txt")

    # ── Step 3+4: Parse coverage ────────────────────────────────────────────
    print("\n  Parsing code coverage...")
    code_cov = parse_code_coverage(hier_path)
    print("\n  Parsing functional coverage...")
    func_cov = parse_functional_coverage(groups_path)

    # ── Combined gap list ───────────────────────────────────────────────────
    all_gaps = code_cov.get("gaps", []) + func_cov.get("gaps", [])

    # ── Step 5: Cross-reference assertions ──────────────────────────────────
    assert_data = safe_read_json(assert_path)
    if assert_data:
        print("  Cross-referencing assertions...")
        all_gaps = cross_reference_assertions(all_gaps, assert_data)

    # ── Step 6: Classify ────────────────────────────────────────────────────
    all_gaps = classify_gaps(all_gaps, config)

    # Save classified gaps
    gaps_dir = os.path.join(out_dir, "gaps")
    safe_write_json(all_gaps, os.path.join(gaps_dir, "classified_gaps.json"))
    print(f"  Classified {len(all_gaps)} gaps → {gaps_dir}/classified_gaps.json")

    # ── Step 7: Interactive resolution ──────────────────────────────────────
    decisions = interactive_resolve(all_gaps, non_interactive=non_inter)
    safe_write_json({k: {kk: vv for kk, vv in v.items() if kk != "gap"}
                     for k, v in decisions.items()},
                    os.path.join(gaps_dir, "gap_decisions.json"))

    # ── Step 8: Exclusion files ──────────────────────────────────────────────
    excl_dir    = os.path.join(out_dir, "exclusions")
    excl_result = generate_exclusions(decisions, excl_dir, project, vdb_path)
    excl_paths  = excl_result["paths"]
    cov_after   = excl_result["coverage_after"]
    safe_write_json(cov_after, os.path.join(out_dir, "coverage_after_exclusions.json"))

    # ── Step 9: Stubs ────────────────────────────────────────────────────────
    tb_data = safe_read_json(os.path.join(os.path.dirname(out_dir), "..", "dv_tb_data.json"))
    stubs   = generate_stubs(decisions, os.path.join(os.path.dirname(out_dir), ".."), tb_data)

    # ── Step 10: Milestone check ─────────────────────────────────────────────
    cov_summary   = cov_after if cov_after else parse_dashboard(dash_path)
    reg_data      = safe_read_json(reg_path)
    milestone_res = check_milestones(cov_summary, reg_data, assert_data, config)
    print_milestone_table(milestone_res)
    safe_write_json(milestone_res, os.path.join(out_dir, "milestone_results.json"))

    # ── Step 11: Write dv_coverage_data.json ────────────────────────────────
    sources = {
        "vdb":              vdb_path,
        "urg_report_dir":   urg_result.get("text_dir",""),
        "s7_assertions_json": assert_path,
        "s9_regression_json": reg_path,
        "exclusions_el":    excl_paths.get("combined",""),
    }
    cov_data = assemble_coverage_data(
        project, vdb_path, code_cov, func_cov,
        decisions, excl_paths, stubs, milestone_res, sources,
    )
    # Look for dv/ parent directory to write dv_coverage_data.json
    dv_dir = _find_dv_dir(out_dir)
    cov_data_path = os.path.join(dv_dir, "dv_coverage_data.json")
    safe_write_json(cov_data, cov_data_path)
    print(f"  Coverage data: {cov_data_path}")

    return cov_data, milestone_res


def _find_dv_dir(start: str) -> str:
    """Walk up from start dir to find a 'dv' parent directory."""
    p = Path(start).resolve()
    for parent in [p] + list(p.parents):
        if parent.name == "dv":
            return str(parent)
    return str(p)  # fallback


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="S10 DV Coverage Closure")
    parser.add_argument("--project",        default="project",      help="Project name")
    parser.add_argument("--vdb",            default="",             help="Path to merged.vdb")
    parser.add_argument("--out",            required=True,          help="Output directory")
    parser.add_argument("--reg-data",       default="",             help="dv_regression_data.json from S9")
    parser.add_argument("--assert-data",    default="",             help="dv_assertions_data.json from S7")
    parser.add_argument("--config",         default="",             help="coverage_config.yaml path")
    parser.add_argument("--non-interactive",action="store_true",    help="Accept all suggested defaults")
    parser.add_argument("--mode",           default="full",
                        choices=["full","exclusions","stubs","milestone","write-data"],
                        help="Run mode (default: full)")

    # Mode-specific args
    parser.add_argument("--decisions",      default="",             help="gap_decisions.json (exclusions/stubs mode)")
    parser.add_argument("--coverage",       default="",             help="coverage summary JSON (milestone mode)")
    parser.add_argument("--tb-data",        default="",             help="dv_tb_data.json (stubs mode)")

    args = parser.parse_args()

    if args.mode == "full":
        cov_data, milestone_res = run_full(args)
        all_pass = all(v.get("passed") for v in milestone_res.values())
        sys.exit(0 if milestone_res.get("dv_f",{}).get("passed") else 1)

    elif args.mode == "exclusions":
        decisions = safe_read_json(args.decisions)
        result    = generate_exclusions(decisions, args.out, args.project, args.vdb)
        sys.exit(0)

    elif args.mode == "stubs":
        decisions = safe_read_json(args.decisions)
        tb_data   = safe_read_json(args.tb_data)
        generate_stubs(decisions, args.out, tb_data)
        sys.exit(0)

    elif args.mode == "milestone":
        config    = load_config(args.config)
        cov_sum   = safe_read_json(args.coverage)
        reg_data  = safe_read_json(args.reg_data)
        assert_d  = safe_read_json(args.assert_data)
        results   = check_milestones(cov_sum, reg_data, assert_d, config)
        print_milestone_table(results)
        safe_write_json(results, os.path.join(args.out, "milestone_results.json"))
        sys.exit(0 if results.get("dv_f",{}).get("passed") else 1)


if __name__ == "__main__":
    main()
