#!/usr/bin/env python3
"""
parse_coverage_report.py — DV Skills VCS urg coverage report parser
Parses urg text reports (hier.txt, groups.txt) for both code and functional coverage.

Usage:
    # Code coverage from hier.txt
    python3 parse_coverage_report.py --mode code --hier urgReport/hier.txt --out gaps/code_gaps.json

    # Functional coverage from groups.txt
    python3 parse_coverage_report.py --mode functional --groups urgReport/groups.txt --out gaps/func_gaps.json

    # Parse dashboard.txt for summary numbers
    python3 parse_coverage_report.py --mode dashboard --dashboard urgReport/dashboard.txt --out cov_summary.json

    # Library import
    from parse_coverage_report import parse_code_coverage, parse_functional_coverage, parse_dashboard
"""

import re
import json
import sys
import os
import argparse
from pathlib import Path


# ── Thresholds for gap identification (overridden by coverage_config.yaml) ──────
DEFAULT_THRESHOLDS = {
    "line":       99.0,
    "toggle":     95.0,
    "branch":     99.0,
    "expression": 99.0,
    "fsm":        99.0,
    "functional": 99.0,
}

# ── urg hier.txt section headers ────────────────────────────────────────────────
_COV_SECTIONS = {
    "line coverage":          "line",
    "toggle coverage":        "toggle",
    "branch coverage":        "branch",
    "expression coverage":    "expression",
    "condition coverage":     "expression",   # alias
    "fsm state coverage":     "fsm_state",
    "fsm transition coverage":"fsm_trans",
    "fsm coverage":           "fsm_state",
}


# ══════════════════════════════════════════════════════════════════════════════
# CODE COVERAGE — hier.txt parser
# ══════════════════════════════════════════════════════════════════════════════

def parse_code_coverage(hier_path: str, thresholds: dict = None) -> dict:
    """
    Parse urg hier.txt and return a structured code coverage dict.

    Returns:
    {
        "summary": {
            "line":       {"covered": int, "total": int, "pct": float},
            "toggle":     {...},
            "branch":     {...},
            "expression": {...},
            "fsm":        {...},
        },
        "instances": [
            {
                "path": str,
                "module": str,
                "type": str,       # "line"|"toggle"|"branch"|"expression"|"fsm"
                "covered": int,
                "total": int,
                "pct": float,
                "uncovered_items": [
                    {
                        "id": str,
                        "description": str,
                        "file": str,
                        "line": int,
                        "detail": str,
                        "decision": "pending",
                        "assertion_backed": False,
                        "related_chk_ids": [],
                    }
                ]
            }
        ],
        "gaps": [...]   # flat list of all uncovered items
    }
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    result = {
        "summary":   {k: {"covered": 0, "total": 0, "pct": 0.0} for k in ("line","toggle","branch","expression","fsm")},
        "instances": [],
        "gaps":      [],
    }

    if not os.path.isfile(hier_path):
        return result

    try:
        content = Path(hier_path).read_text(errors="replace")
    except OSError:
        return result

    lines = content.splitlines()
    current_section = None
    gap_counter = {"n": 0}

    def next_gap_id(cov_type: str) -> str:
        gap_counter["n"] += 1
        return f"CODE_{cov_type.upper()[:3]}_{gap_counter['n']:04d}"

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip().lower()

        # ── Section header detection ────────────────────────────────────────
        for header, section_name in _COV_SECTIONS.items():
            if header in stripped and ("==" in raw or raw.strip() == header.title() + " Coverage"
                                        or stripped.endswith(header)):
                current_section = section_name
                break

        # ── Skip separator and header rows ──────────────────────────────────
        if re.match(r"^\s*[-=]+\s*$", raw) or not raw.strip():
            i += 1
            continue
        if re.match(r"^\s*(Enabled Coverage|Bins|Coverage|Scope|File|Groups)\b", raw, re.IGNORECASE):
            i += 1
            continue

        # ── Parse data rows ─────────────────────────────────────────────────
        if current_section and raw.strip() and not raw.strip().lower().endswith("coverage"):
            record = _parse_hier_data_line(raw, current_section, lines, i, next_gap_id)
            if record:
                result["instances"].append(record)
                result["gaps"].extend(record.get("uncovered_items", []))

                # Accumulate summary
                base_type = _base_type(current_section)
                if base_type in result["summary"]:
                    result["summary"][base_type]["covered"] += record["covered"]
                    result["summary"][base_type]["total"]   += record["total"]

        i += 1

    # Compute summary percentages
    for cov_type, s in result["summary"].items():
        if s["total"] > 0:
            s["pct"] = round(100.0 * s["covered"] / s["total"], 2)

    return result


def _base_type(section: str) -> str:
    if "fsm" in section:    return "fsm"
    if "toggle" in section: return "toggle"
    if "branch" in section: return "branch"
    if "expression" in section or "condition" in section: return "expression"
    return "line"


def _parse_hier_data_line(raw: str, section: str, lines: list, idx: int, next_gap_id) -> dict | None:
    """
    Parse a single data line from hier.txt.
    urg format: <path>    <covered>/<total>    <pct>%
    """
    # Match: path  covered/total  pct%
    m = re.match(r"^(\S.*?)\s{2,}(\d+)/(\d+)\s+([\d.]+)%", raw)
    if not m:
        return None

    path     = m.group(1).strip()
    covered  = int(m.group(2))
    total    = int(m.group(3))
    pct      = float(m.group(4))

    # Skip summary/total rows
    if path.lower() in ("total", "overall", "summary"):
        return None

    base_type = _base_type(section)

    record = {
        "path":           path,
        "module":         path.split(".")[-1],
        "type":           base_type,
        "covered":        covered,
        "total":          total,
        "pct":            pct,
        "uncovered_items": [],
    }

    # If below 100% (or threshold), look ahead for uncovered item details
    if covered < total:
        uncovered_items = _extract_uncovered_items(lines, idx + 1, section, path, next_gap_id)
        record["uncovered_items"] = uncovered_items

    return record


def _extract_uncovered_items(lines: list, start: int, section: str, scope: str, next_gap_id) -> list:
    """
    Look ahead past the instance line to find individual uncovered items.
    These are indented sub-lines showing file:line, signal names, etc.
    Returns list of gap dicts.
    """
    items = []
    base_type = _base_type(section)
    i = start

    # Read up to 20 continuation lines
    for _ in range(20):
        if i >= len(lines):
            break
        line = lines[i]

        # Stop if we hit a new top-level instance (non-indented non-empty)
        if line and not line[0].isspace() and re.match(r"^\S", line):
            break

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # File:line format  — "rtl/ctrl.sv:142"
        fm = re.search(r"(\S+\.(?:sv|v|vhd|vhdl)):(\d+)", stripped)
        # Toggle signal  — "signal_name  NOT_COVERED"
        tm = re.match(r"^(\w+)\s+(NOT_COVERED|0->1|1->0|not toggled)", stripped, re.IGNORECASE)
        # FSM state/transition
        fsm_state = re.match(r"^(\w+)\s+\(state\)", stripped, re.IGNORECASE)
        fsm_trans = re.match(r"^(\w+)\s*->\s*(\w+)", stripped)

        gap = {
            "id":              next_gap_id(base_type),
            "description":     stripped[:120],
            "file":            fm.group(1) if fm else "",
            "line":            int(fm.group(2)) if fm else 0,
            "detail":          stripped,
            "scope":           scope,
            "decision":        "pending",
            "assertion_backed": False,
            "related_chk_ids": [],
        }

        if base_type == "toggle" and tm:
            gap["signal"] = tm.group(1)
            gap["direction"] = tm.group(2)
        elif base_type in ("fsm_state", "fsm") and fsm_state:
            gap["state"] = fsm_state.group(1)
        elif base_type == "fsm" and fsm_trans:
            gap["from_state"] = fsm_trans.group(1)
            gap["to_state"]   = fsm_trans.group(2)

        items.append(gap)
        i += 1

    return items


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTIONAL COVERAGE — groups.txt parser
# ══════════════════════════════════════════════════════════════════════════════

def parse_functional_coverage(groups_path: str) -> dict:
    """
    Parse urg groups.txt and return structured functional coverage data.

    Returns:
    {
        "summary": {"total_bins": int, "covered_bins": int, "pct": float},
        "covergroups": [
            {
                "name": str,         # covergroup type name
                "instance": str,     # instance path
                "scope": str,
                "covered_bins": int,
                "total_bins": int,
                "pct": float,
                "coverpoints": [
                    {
                        "name": str,
                        "type": "coverpoint"|"cross",
                        "covered_bins": int,
                        "total_bins": int,
                        "bins": [
                            {
                                "name": str,
                                "hit_count": int,
                                "at_least": int,
                                "weight": int,
                                "covered": bool,
                                "excluded": bool,
                                "bin_type": "normal"|"ignore"|"illegal"|"cross",
                            }
                        ]
                    }
                ]
            }
        ],
        "gaps": [...]   # flat list of uncovered bin gap dicts
    }
    """
    result = {
        "summary":     {"total_bins": 0, "covered_bins": 0, "pct": 0.0},
        "covergroups": [],
        "gaps":        [],
    }

    if not os.path.isfile(groups_path):
        return result

    try:
        content = Path(groups_path).read_text(errors="replace")
    except OSError:
        return result

    # Split into covergroup blocks on separator lines
    sep_pattern = re.compile(r"^={5,}", re.MULTILINE)
    raw_blocks = sep_pattern.split(content)

    gap_counter = {"n": 0}

    def next_func_gap_id() -> str:
        gap_counter["n"] += 1
        return f"FUNC_BIN_{gap_counter['n']:04d}"

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        cg = _parse_covergroup_block(block, next_func_gap_id)
        if cg:
            result["covergroups"].append(cg)
            result["summary"]["total_bins"]   += cg["total_bins"]
            result["summary"]["covered_bins"] += cg["covered_bins"]
            result["gaps"].extend(_collect_gaps_from_cg(cg))

    if result["summary"]["total_bins"] > 0:
        result["summary"]["pct"] = round(
            100.0 * result["summary"]["covered_bins"] / result["summary"]["total_bins"], 2
        )

    return result


def _parse_covergroup_block(block: str, next_func_gap_id) -> dict | None:
    """Parse a single covergroup block from groups.txt."""
    lines = block.splitlines()

    cg = {
        "name":        "",
        "instance":    "",
        "scope":       "",
        "covered_bins": 0,
        "total_bins":   0,
        "pct":          0.0,
        "coverpoints": [],
    }

    # Find group header fields
    for line in lines[:20]:
        m_grp  = re.match(r"^\s*Group\s*:\s*(.+)", line, re.IGNORECASE)
        m_inst = re.match(r"^\s*Instance\s*:\s*(.+)", line, re.IGNORECASE)
        m_from = re.match(r"^\s*(?:From|Scope|Hierarchy)\s*:\s*(.+)", line, re.IGNORECASE)
        if m_grp:  cg["name"]     = m_grp.group(1).strip()
        if m_inst: cg["instance"] = m_inst.group(1).strip()
        if m_from: cg["scope"]    = m_from.group(1).strip()

    if not cg["name"]:
        return None

    # Parse coverpoints within the block
    # Coverpoint sub-blocks separated by dashes or "Coverpoint:" / "Cross:" headers
    cp_split = re.split(r"(?=^\s*(?:Coverpoint|Cross)\s*:)", block, flags=re.MULTILINE)

    for cp_block in cp_split[1:]:  # skip header block
        cp = _parse_coverpoint_block(cp_block, cg["instance"], next_func_gap_id)
        if cp:
            cg["coverpoints"].append(cp)
            cg["covered_bins"] += cp["covered_bins"]
            cg["total_bins"]   += cp["total_bins"]

    if cg["total_bins"] > 0:
        cg["pct"] = round(100.0 * cg["covered_bins"] / cg["total_bins"], 2)

    return cg


def _parse_coverpoint_block(block: str, cg_instance: str, next_func_gap_id) -> dict | None:
    """Parse a single coverpoint or cross block."""
    lines = block.strip().splitlines()
    if not lines:
        return None

    # First line: "  Coverpoint: name" or "  Cross: name"
    header = lines[0].strip()
    m = re.match(r"(Coverpoint|Cross)\s*:\s*(\S+)", header, re.IGNORECASE)
    if not m:
        return None

    cp_type = "cross" if m.group(1).lower() == "cross" else "coverpoint"
    cp_name = m.group(2)

    cp = {
        "name":         cp_name,
        "type":         cp_type,
        "covered_bins": 0,
        "total_bins":   0,
        "bins":         [],
    }

    # Parse bin lines
    # urg format: "    bin <name>  @ <hits> / <at_least>  <weight>"
    # or:         "    <name>  <hits>  <at_least>  <weight>"
    for line in lines[1:]:
        bin_record = _parse_bin_line(line, cp_name, cg_instance, next_func_gap_id)
        if bin_record:
            cp["bins"].append(bin_record)
            if not bin_record["excluded"] and bin_record.get("at_least", 1) > 0:
                cp["total_bins"] += 1
                if bin_record["covered"]:
                    cp["covered_bins"] += 1

    return cp


def _parse_bin_line(line: str, cp_name: str, cg_instance: str, next_func_gap_id) -> dict | None:
    """Parse a single bin line from a coverpoint block."""
    stripped = line.strip()
    if not stripped:
        return None

    # Detect bin type
    bin_type = "normal"
    if re.match(r"ignore_bin\b", stripped, re.IGNORECASE):
        bin_type = "ignore"
    elif re.match(r"illegal_bin\b", stripped, re.IGNORECASE):
        bin_type = "illegal"

    # Remove type prefix for parsing
    stripped_clean = re.sub(r"^(?:ignore_bin|illegal_bin|bin)\s*", "", stripped, flags=re.IGNORECASE)

    # Format 1: "bin_name  @ hits / at_least  [weight]"
    m1 = re.match(r"(\S+)\s+@\s+(\d+)\s*/\s*(\d+)(?:\s+(\d+))?", stripped_clean)
    # Format 2: "bin_name  hits  at_least  [weight]"
    m2 = re.match(r"(\S+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?", stripped_clean)

    m = m1 or m2
    if not m:
        return None

    bin_name  = m.group(1)
    hit_count = int(m.group(2))
    at_least  = int(m.group(3))
    weight    = int(m.group(4)) if m.group(4) else 1

    excluded = bin_type in ("ignore", "illegal")
    covered  = hit_count >= at_least if at_least > 0 else True

    record = {
        "name":      bin_name,
        "hit_count": hit_count,
        "at_least":  at_least,
        "weight":    weight,
        "covered":   covered,
        "excluded":  excluded,
        "bin_type":  bin_type,
        "cp_name":   cp_name,
        "cg_instance": cg_instance,
        "decision":  "pending",
    }

    # Assign gap ID to uncovered non-excluded bins
    if not covered and not excluded and at_least > 0:
        record["gap_id"] = next_func_gap_id()
        record["full_path"] = f"{cg_instance}::{cp_name}::{bin_name}"

    return record


def _collect_gaps_from_cg(cg: dict) -> list:
    """Collect all uncovered bin gap dicts from a covergroup."""
    gaps = []
    for cp in cg.get("coverpoints", []):
        for b in cp.get("bins", []):
            if b.get("gap_id"):
                gaps.append({
                    "id":          b["gap_id"],
                    "type":        "functional",
                    "cg_name":     cg["name"],
                    "cg_instance": cg["instance"],
                    "cp_name":     b["cp_name"],
                    "bin_name":    b["name"],
                    "full_path":   b.get("full_path", ""),
                    "hit_count":   b["hit_count"],
                    "at_least":    b["at_least"],
                    "decision":    "pending",
                    "assertion_backed": False,
                    "related_chk_ids":  [],
                    "suggested_test":   _suggest_test_name(cg["name"], b["cp_name"], b["name"]),
                })
    return gaps


def _suggest_test_name(cg_name: str, cp_name: str, bin_name: str) -> str:
    """Generate a snake_case test name suggestion from coverage path."""
    parts = [cg_name, cp_name, bin_name]
    name = "_".join(re.sub(r"[^a-zA-Z0-9]", "_", p).lower() for p in parts if p)
    name = re.sub(r"_+", "_", name).strip("_")
    return f"{name}_coverage_test"


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — dashboard.txt summary parser
# ══════════════════════════════════════════════════════════════════════════════

def parse_dashboard(dashboard_path: str) -> dict:
    """
    Parse urg dashboard.txt for top-level per-type coverage percentages.

    Returns:
    {
        "line":       {"covered": int, "total": int, "pct": float} | None,
        "toggle":     ...,
        "branch":     ...,
        "expression": ...,
        "fsm":        ...,
        "functional": ...,
        "overall":    float | None,
    }
    """
    result = {k: None for k in ("line","toggle","branch","expression","fsm","functional","overall")}

    if not os.path.isfile(dashboard_path):
        return result

    try:
        content = Path(dashboard_path).read_text(errors="replace")
    except OSError:
        return result

    # Patterns for per-type rows in dashboard.txt
    # Line:   "Line    Coverage    1240/1250    99.20%"
    # or:     "Line Coverage                  99.20%"
    patterns = {
        "line":       r"[Ll]ine\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
        "toggle":     r"[Tt]oggle\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
        "branch":     r"[Bb]ranch\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
        "expression": r"(?:[Ee]xpression|[Cc]ondition)\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
        "fsm":        r"[Ff][Ss][Mm]\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
        "functional": r"[Ff]unctional\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
        "overall":    r"[Oo]verall\s+(?:[Cc]overage)?\s+(?:(\d+)/(\d+)\s+)?([\d.]+)%",
    }

    for key, pat in patterns.items():
        m = re.search(pat, content)
        if m:
            pct = float(m.group(3))
            if key == "overall":
                result["overall"] = pct
            else:
                entry = {"pct": pct}
                if m.group(1) and m.group(2):
                    entry["covered"] = int(m.group(1))
                    entry["total"]   = int(m.group(2))
                result[key] = entry

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Classify gaps
# ══════════════════════════════════════════════════════════════════════════════

def classify_gaps(gaps: list, config: dict = None) -> list:
    """
    Classify each gap as 'excludable', 'coverable', or 'requires_analysis'.
    Adds a 'classification' field and 'exclusion_reason'/'suggested_test' fields.
    """
    if config is None:
        config = {}

    auto_patterns = [re.compile(p) for p in config.get("auto_exclude_patterns", [
        r".*_dft_.*", r".*_tb_.*", r".*vendor_ip.*",
        r".*_unused.*", r".*_tie.*", r".*_dummy.*",
    ])]

    # Signal name patterns that suggest unused/tied signals
    trivial_signals = re.compile(r"(tie_|unused_|one_|zero_|nc_|dummy_)", re.IGNORECASE)

    for gap in gaps:
        path   = gap.get("full_path", "") or gap.get("scope", "") or ""
        detail = gap.get("detail", "")
        signal = gap.get("signal", "")

        # Auto-exclude by path pattern
        if any(p.match(path) for p in auto_patterns):
            gap["classification"]   = "excludable"
            gap["exclusion_reason"] = "Matches auto-exclude pattern"
            continue

        # Toggle of trivially-named signals
        if gap.get("type") == "toggle" and trivial_signals.search(signal or detail):
            gap["classification"]   = "excludable"
            gap["exclusion_reason"] = "Signal name suggests tie/unused signal"
            continue

        # Assertion-backed gaps are exclusion candidates
        if gap.get("assertion_backed"):
            gap["classification"]   = "excludable"
            gap["exclusion_reason"] = "Assertion-backed: correctness verified via SVA"
            continue

        # Cross coverage is hard to reason about automatically
        if gap.get("bin_type") == "cross" or "cross" in gap.get("cp_name", "").lower():
            gap["classification"] = "requires_analysis"
            continue

        # Default: coverable
        gap["classification"] = "coverable"
        if not gap.get("suggested_test"):
            gap["suggested_test"] = _suggest_test_name(
                gap.get("cg_name", gap.get("type", "cov")),
                gap.get("cp_name", ""),
                gap.get("bin_name", gap.get("detail", "gap")),
            )

    return gaps


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def _print_code_summary(data: dict):
    """Print code coverage summary table to stdout."""
    print(f"\n  Code Coverage Summary")
    print(f"  {'─'*66}")
    print(f"  {'Type':<14} {'Covered':>8} {'Total':>8} {'Pct':>8}  {'Gaps':>6}")
    print(f"  {'─'*66}")
    for ctype, s in data["summary"].items():
        gaps = sum(1 for g in data["gaps"] if g.get("type") == ctype or
                   _base_type(g.get("type","")) == ctype)
        indicator = "✓" if s["pct"] >= DEFAULT_THRESHOLDS.get(ctype, 99.0) else "✗"
        print(f"  {ctype:<14} {s['covered']:>8} {s['total']:>8} {s['pct']:>7.1f}%  {gaps:>6}  {indicator}")
    print(f"  {'─'*66}")
    print(f"  Total gaps : {len(data['gaps'])}\n")


def _print_func_summary(data: dict):
    """Print functional coverage summary table to stdout."""
    s = data["summary"]
    print(f"\n  Functional Coverage Summary")
    print(f"  {'─'*66}")
    print(f"  {'Covergroup':<30} {'Bins':>6} {'Hit':>6} {'Missed':>8} {'Pct':>8}")
    print(f"  {'─'*66}")
    for cg in data["covergroups"]:
        missed = cg["total_bins"] - cg["covered_bins"]
        print(f"  {cg['name']:<30} {cg['total_bins']:>6} {cg['covered_bins']:>6} {missed:>8} {cg['pct']:>7.1f}%")
    print(f"  {'─'*66}")
    print(f"  Total: {s['total_bins']} bins, {s['covered_bins']} covered, "
          f"{s['total_bins']-s['covered_bins']} uncovered ({s['pct']}%)\n")


def main():
    parser = argparse.ArgumentParser(description="Parse urg coverage reports")
    parser.add_argument("--mode", required=True,
                        choices=["code", "functional", "dashboard", "all"],
                        help="Parsing mode")
    parser.add_argument("--hier",      help="Path to urgReport/hier.txt")
    parser.add_argument("--groups",    help="Path to urgReport/groups.txt")
    parser.add_argument("--dashboard", help="Path to urgReport/dashboard.txt")
    parser.add_argument("--out",       help="Output JSON path")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Gap threshold override (default: 99.0%)")
    args = parser.parse_args()

    output = {}

    if args.mode in ("code", "all"):
        if not args.hier:
            print("  --hier required for code mode"); sys.exit(1)
        data = parse_code_coverage(args.hier)
        _print_code_summary(data)
        if args.mode == "code":
            output = data

    if args.mode in ("functional", "all"):
        if not args.groups:
            print("  --groups required for functional mode"); sys.exit(1)
        data = parse_functional_coverage(args.groups)
        _print_func_summary(data)
        if args.mode == "functional":
            output = data

    if args.mode == "dashboard":
        if not args.dashboard:
            print("  --dashboard required for dashboard mode"); sys.exit(1)
        output = parse_dashboard(args.dashboard)
        print(json.dumps(output, indent=2))
        return

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2))
        print(f"  Written: {args.out}")


if __name__ == "__main__":
    main()
