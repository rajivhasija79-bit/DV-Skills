#!/usr/bin/env python3
"""
log_extract.py — Streaming large-log triage for RTL sim debug.

Reads a simulation log (any size) in a single streaming pass and emits a
compact Failure Digest as JSON. Memory is O(hits), not O(file).

Patterns are matched in priority order. The first-real-failure is the
earliest UVM_FATAL, else the earliest non-benign UVM_ERROR, else the
earliest tool error or assertion. Benign patterns come from a YAML-ish
file (see references/benign_messages.yaml); parsing is tolerant of
missing PyYAML.

Usage:
    log_extract.py <log> --out digest.json [--window 200]
                   [--benign path/to/benign_messages.yaml]
                   [--max-line-chars 1000]

Output JSON schema (top-level):
{
  "first_failure": {
    "line": int, "byte": int, "time_ns": float|null,
    "phase": str|null, "hierarchy": str|null,
    "message_id": str|null, "source_file_line": str|null,
    "raw_excerpt": str
  },
  "all_fatal_error_offsets": [ {"line":int,"byte":int,"kind":str,"snippet":str} ],
  "hang_indicators": {
    "last_phase": str|null, "objection_trace_present": bool,
    "last_activity_time_ns": float|null
  },
  "stats": { "size_bytes": int, "lines": int, "scan_duration_s": float }
}
"""

from __future__ import annotations
import argparse, json, os, re, sys, time
from typing import Any

# Pattern priority (higher index = lower priority).
PATTERNS = [
    ("UVM_FATAL",      re.compile(r"\bUVM_FATAL\b")),
    ("UVM_ERROR",      re.compile(r"\bUVM_ERROR\b")),
    ("VCS_ERROR",      re.compile(r"\bError-\[")),
    ("ASSERT",         re.compile(r"\b(Assertion failed|\$error|\$fatal)\b")),
    ("OBJECTION_STOP", re.compile(r"\bObjection\b.*\b(drain|stop|quit)\b", re.I)),
    ("TIMEOUT",        re.compile(r"\b(TIMEOUT|Simulation complete after .* reached)\b", re.I)),
    ("STOPPING",       re.compile(r"\bStopping at\b")),
    ("X_PROP",         re.compile(r"\bX-propagation\b", re.I)),
]

# UVM time stamp prefix: "UVM_ERROR @ 12345 ns" or "[@ 12345 ns]" or "UVM_ERROR [@12345 ns]"
TIME_RE       = re.compile(r"@\s*([0-9]+(?:\.[0-9]+)?)\s*(ps|ns|us|ms|s)\b", re.I)
MSG_ID_RE     = re.compile(r"UVM_(?:ERROR|FATAL|WARNING|INFO)\b.*?\[(?!@)([A-Za-z0-9_\-/.]+)\]")
HIERARCHY_RE  = re.compile(r"\(([A-Za-z_][A-Za-z0-9_\.\[\]]*(?:\.[A-Za-z_][A-Za-z0-9_\.\[\]]*)+)\)")
FILELINE_RE   = re.compile(r"([A-Za-z0-9_./\-]+\.(?:sv|v|svh|vh)):(\d+)")
PHASE_RE      = re.compile(r"\b([a-z_]+_phase)\b")
OBJECTION_RE  = re.compile(r"uvm_objection|phase_dump_state", re.I)

TIME_UNIT_TO_NS = {"ps": 1e-3, "ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9}


def load_benign(path: str | None) -> list[re.Pattern]:
    """Best-effort YAML load (stdlib only). Returns list of compiled regexes.

    Accepts the minimal subset of YAML we write ourselves (see
    references/benign_messages.yaml). If the file is missing or unparseable,
    returns an empty list — logged to stderr.
    """
    if not path or not os.path.isfile(path):
        return []
    patterns: list[re.Pattern] = []
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
        # Very small YAML-ish parser: find lines like `  - regex: "..."`
        regex_line = re.compile(r"^\s*-\s*regex\s*:\s*(.+?)\s*$")
        for ln in content.splitlines():
            m = regex_line.match(ln)
            if m:
                val = m.group(1)
                # Strip quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                try:
                    patterns.append(re.compile(val))
                except re.error as e:
                    print(f"[log_extract] bad benign regex {val!r}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[log_extract] couldn't load benign file {path}: {e}", file=sys.stderr)
    return patterns


def parse_time_ns(line: str) -> float | None:
    m = TIME_RE.search(line)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    return val * TIME_UNIT_TO_NS[unit]


def extract_fields(line: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "time_ns":          parse_time_ns(line),
        "message_id":       None,
        "hierarchy":        None,
        "source_file_line": None,
        "phase":            None,
    }
    m = MSG_ID_RE.search(line)
    if m:
        out["message_id"] = m.group(1)
    m = HIERARCHY_RE.search(line)
    if m:
        out["hierarchy"] = m.group(1)
    m = FILELINE_RE.search(line)
    if m:
        out["source_file_line"] = f"{m.group(1)}:{m.group(2)}"
    m = PHASE_RE.search(line)
    if m:
        out["phase"] = m.group(1)
    return out


def extract_window(path: str, center_line_no: int, window: int, max_line_chars: int) -> str:
    """Extract ±window lines around a 1-based line number. Second small pass."""
    lo = max(1, center_line_no - window)
    hi = center_line_no + window
    out_lines: list[str] = []
    with open(path, "r", errors="replace") as f:
        for i, ln in enumerate(f, start=1):
            if i < lo:
                continue
            if i > hi:
                break
            if len(ln) > max_line_chars:
                ln = ln[:max_line_chars] + "...<truncated>\n"
            out_lines.append(ln)
    return "".join(out_lines)


def is_benign(line: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(line) for p in patterns)


def scan(path: str, benign_patterns: list[re.Pattern]) -> dict[str, Any]:
    t0 = time.time()
    size = os.path.getsize(path)

    # Hits per pattern name
    hits: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in PATTERNS}
    objection_seen = False
    last_phase: str | None = None
    last_time_ns: float | None = None
    all_fatal_error_offsets: list[dict[str, Any]] = []
    line_count = 0
    byte_offset = 0

    with open(path, "rb") as fb:
        for raw in fb:
            byte_offset_line_start = byte_offset
            byte_offset += len(raw)
            line_count += 1
            try:
                ln = raw.decode("utf-8", errors="replace")
            except Exception:
                continue

            # Track phase + last activity time on every line (cheap)
            mph = PHASE_RE.search(ln)
            if mph:
                last_phase = mph.group(1)
            t_ns = parse_time_ns(ln)
            if t_ns is not None:
                last_time_ns = t_ns
            if not objection_seen and OBJECTION_RE.search(ln):
                objection_seen = True

            # Priority scan
            for name, pat in PATTERNS:
                if pat.search(ln):
                    rec = {
                        "line": line_count,
                        "byte": byte_offset_line_start,
                        "snippet": ln.strip()[:500],
                    }
                    hits[name].append(rec)
                    if name in ("UVM_FATAL", "UVM_ERROR", "VCS_ERROR", "ASSERT"):
                        all_fatal_error_offsets.append({**rec, "kind": name})
                    break  # first matching pattern wins for this line

    # First-real-failure selection
    first_failure = None
    ordered_classes = ["UVM_FATAL", "UVM_ERROR", "VCS_ERROR", "ASSERT"]
    for cls in ordered_classes:
        for rec in hits[cls]:
            # Re-read the single line to apply benign filter (avoid storing all line bodies above)
            if is_benign(rec["snippet"], benign_patterns):
                continue
            first_failure = dict(rec)
            first_failure["kind"] = cls
            break
        if first_failure:
            break

    # Is this a hang? no fatal/error found
    hang = first_failure is None

    scan_s = time.time() - t0
    return {
        "hits": hits,
        "first_failure": first_failure,
        "hang": hang,
        "objection_seen": objection_seen,
        "last_phase": last_phase,
        "last_time_ns": last_time_ns,
        "line_count": line_count,
        "size": size,
        "scan_s": scan_s,
        "all_fatal_error_offsets": all_fatal_error_offsets,
    }


def build_digest(path: str, scan_res: dict[str, Any], window: int, max_line_chars: int) -> dict[str, Any]:
    ff = scan_res["first_failure"]
    if ff is not None:
        fields = extract_fields(ff["snippet"])
        raw_excerpt = extract_window(path, ff["line"], window, max_line_chars)
        first_failure_out = {
            "line":             ff["line"],
            "byte":             ff["byte"],
            "kind":             ff["kind"],
            "time_ns":          fields["time_ns"],
            "phase":            fields["phase"],
            "hierarchy":        fields["hierarchy"],
            "message_id":       fields["message_id"],
            "source_file_line": fields["source_file_line"],
            "raw_excerpt":      raw_excerpt,
        }
    else:
        first_failure_out = None

    hang_indicators = {
        "last_phase":             scan_res["last_phase"],
        "objection_trace_present": scan_res["objection_seen"],
        "last_activity_time_ns":   scan_res["last_time_ns"],
    }

    return {
        "first_failure":          first_failure_out,
        "all_fatal_error_offsets": scan_res["all_fatal_error_offsets"][:100],
        "hang_indicators":         hang_indicators if scan_res["hang"] or scan_res["last_phase"] else hang_indicators,
        "stats": {
            "size_bytes":       scan_res["size"],
            "lines":            scan_res["line_count"],
            "scan_duration_s":  round(scan_res["scan_s"], 3),
        },
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Streaming sim-log triage → Failure Digest JSON")
    ap.add_argument("log", help="Path to the simulation log file")
    ap.add_argument("--out", required=False, help="Write JSON here; default: stdout")
    ap.add_argument("--window", type=int, default=200, help="Lines of context around the first failure")
    ap.add_argument("--benign", default=None, help="Path to benign_messages.yaml")
    ap.add_argument("--max-line-chars", type=int, default=1000)
    args = ap.parse_args(argv)

    if not os.path.isfile(args.log):
        print(f"log not found: {args.log}", file=sys.stderr)
        return 2

    benign_patterns = load_benign(args.benign)
    scan_res = scan(args.log, benign_patterns)
    digest = build_digest(args.log, scan_res, args.window, args.max_line_chars)

    blob = json.dumps(digest, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(blob)
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
