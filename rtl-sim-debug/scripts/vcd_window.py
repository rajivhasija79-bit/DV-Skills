#!/usr/bin/env python3
"""
vcd_window.py — Streaming, signal-filtered, time-windowed VCD extractor.

Handles arbitrarily large .vcd files by streaming the value-change section.
Parses only the header into memory; between [t0, t1] emits a compact table
of (time_ns, signal_hier, old_value, new_value) plus an initial-state
snapshot at t0.

Usage:
    vcd_window.py <vcd> --signals signals.txt --t0 <ns> --t1 <ns> --out trace.json
    vcd_window.py <vcd> --signals -            # read signal list from stdin (one per line)

Signals file: one hierarchical name per line. Slash- and dot-separated
paths are both accepted; they are normalized to dot-separated internally.

Output JSON:
{
  "timescale_ps": 1,
  "t0_ns": 1000, "t1_ns": 2000,
  "initial_state": [ {"signal": "...", "value": "0"} ],
  "changes":       [ {"time_ns": 1001.2, "signal": "...", "old": "0", "new": "1"} ],
  "unresolved_signals": [ "..." ]
}
"""

from __future__ import annotations
import argparse, json, os, re, sys
from typing import Any

TIMESCALE_RE = re.compile(r"\$timescale\s+(\d+)\s*(fs|ps|ns|us|ms|s)\s*\$end", re.S)
UNIT_TO_PS = {"fs": 1e-3, "ps": 1.0, "ns": 1e3, "us": 1e6, "ms": 1e9, "s": 1e12}


def norm(sig: str) -> str:
    s = sig.strip()
    # Strip leading '/' or 'top/'
    s = s.lstrip("/")
    s = s.replace("/", ".")
    return s


def read_signal_list(path: str) -> list[str]:
    if path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        with open(path, "r") as f:
            lines = f.read().splitlines()
    return [norm(x) for x in lines if x.strip() and not x.lstrip().startswith("#")]


def parse_header(fh) -> tuple[dict[str, str], float, int]:
    """Parse VCD header up to $enddefinitions. Return:
        id_to_hier:  { vcd_id : dotted_hierarchical_name }
        timescale_ns: multiplier from VCD integer time → ns
        header_end_pos: byte offset in fh where header ended (for reset)
    """
    scope: list[str] = []
    id_to_hier: dict[str, str] = {}
    timescale_ps = 1.0
    buf = ""
    pos = 0
    # Read header in chunks until $enddefinitions
    while True:
        chunk = fh.read(65536)
        if not chunk:
            break
        buf += chunk
        if "$enddefinitions" in buf:
            # locate end-of-header position
            idx = buf.index("$enddefinitions")
            # find the matching $end after it
            end_idx = buf.index("$end", idx)
            header_chunk = buf[: end_idx + 4]
            # Now bytes consumed past header:
            header_end_pos = pos + len(header_chunk.encode("utf-8", errors="replace"))
            # Parse header_chunk
            _parse_header_body(header_chunk, scope, id_to_hier)
            m = TIMESCALE_RE.search(header_chunk)
            if m:
                timescale_ps = float(m.group(1)) * UNIT_TO_PS[m.group(2).lower()]
            # Seek past header
            fh.seek(header_end_pos)
            return id_to_hier, timescale_ps, header_end_pos
        pos += len(chunk.encode("utf-8", errors="replace"))
    # Malformed
    return id_to_hier, timescale_ps, pos


def _parse_header_body(text: str, scope: list[str], id_to_hier: dict[str, str]) -> None:
    # Tokenize on whitespace; walk through $scope / $upscope / $var commands
    tokens = text.split()
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t == "$scope":
            # $scope module|task|function|begin|fork <name> $end
            # scope_type is tokens[i+1], name tokens[i+2]
            if i + 2 < n:
                scope.append(tokens[i + 2])
            # Advance to $end
            while i < n and tokens[i] != "$end":
                i += 1
        elif t == "$upscope":
            if scope:
                scope.pop()
            while i < n and tokens[i] != "$end":
                i += 1
        elif t == "$var":
            # $var <type> <size> <id> <name> [bit-range] $end
            # id is tokens[i+3], name is tokens[i+4] (may have [msb:lsb] following)
            if i + 4 < n:
                vid = tokens[i + 3]
                vname = tokens[i + 4]
                # Ignore bit ranges for naming; they're part of the name if present at i+5
                # Build hierarchy: scope + vname
                full = ".".join(scope + [vname]) if scope else vname
                id_to_hier[vid] = full
            while i < n and tokens[i] != "$end":
                i += 1
        i += 1


def stream_changes(fh, hier_to_id: dict[str, str], id_to_hier: dict[str, str],
                   t0_ps: int, t1_ps: int):
    """Yield (time_ps, vcd_id, value) for changes of signals-of-interest
    within [t0_ps, t1_ps]. Also yield ('initial', id, value) for the
    most-recent pre-t0 value of each signal-of-interest.
    """
    interested_ids = set(hier_to_id.values())
    last_val: dict[str, str] = {}
    cur_t = 0

    # We want the last value before t0 per signal for the initial snapshot.
    # To get that, we iterate once through the whole VC section; it's a single
    # pass so cost is O(file). Fine because we read line-by-line.
    for raw in fh:
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("#"):
            try:
                cur_t = int(ln[1:])
            except ValueError:
                pass
            if cur_t > t1_ps:
                break
            continue
        # Value change
        val, vid = _parse_change(ln)
        if vid is None or vid not in interested_ids:
            continue
        old = last_val.get(vid)
        last_val[vid] = val
        if cur_t >= t0_ps and cur_t <= t1_ps:
            yield (cur_t, vid, old, val, "change")
    # Emit any not-yet-seen signals with their latest value (the initial state at t0)
    for hier, vid in hier_to_id.items():
        if vid in last_val:
            yield (t0_ps, vid, None, last_val[vid], "initial_if_never_changed_in_window")


def _parse_change(ln: str) -> tuple[str, str | None]:
    """Parse a VCD value-change line. Returns (value, vcd_id) or ('', None)."""
    c = ln[0]
    if c in "01xXzZ":
        # Scalar: single char + id, no space
        return ln[0], ln[1:]
    if c in "bB":
        # Vector: b<value> <id>
        parts = ln.split()
        if len(parts) == 2:
            return parts[0][1:], parts[1]
        return "", None
    if c in "rR":
        parts = ln.split()
        if len(parts) == 2:
            return parts[0][1:], parts[1]
        return "", None
    if c == "s":
        parts = ln.split()
        if len(parts) == 2:
            return parts[0][1:], parts[1]
        return "", None
    return "", None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Streaming VCD windowed extractor")
    ap.add_argument("vcd", help="Path to .vcd")
    ap.add_argument("--signals", required=True, help="File with signal hierarchy per line ('-' = stdin)")
    ap.add_argument("--t0", type=float, required=True, help="Window start (ns)")
    ap.add_argument("--t1", type=float, required=True, help="Window end (ns)")
    ap.add_argument("--out", default=None, help="Write JSON here; default stdout")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.vcd):
        print(f"vcd not found: {args.vcd}", file=sys.stderr)
        return 2

    want = read_signal_list(args.signals)

    # Parse header
    with open(args.vcd, "r", errors="replace") as fh:
        id_to_hier, timescale_ps, header_end = parse_header(fh)
        # Build reverse map restricted to signals of interest
        hier_to_id: dict[str, str] = {}
        unresolved: list[str] = []
        for h in want:
            # Allow exact match or suffix match (user may supply a shorter form)
            matches = [vid for vid, full in id_to_hier.items() if full == h or full.endswith("." + h)]
            if matches:
                for vid in matches:
                    hier_to_id[id_to_hier[vid]] = vid
            else:
                unresolved.append(h)

        t0_ps = int(args.t0 * 1000 / timescale_ps)
        t1_ps = int(args.t1 * 1000 / timescale_ps)
        interested_ids = set(hier_to_id.values())

        fh.seek(header_end)
        changes: list[dict[str, Any]] = []
        # last_value_before_t0[vid] holds the most-recent pre-t0 value (snapshot at t0)
        last_value_before_t0: dict[str, str] = {}
        # current_value[vid] tracks the running value during the window (for "old" in changes)
        current_value: dict[str, str] = {}
        cur_t = 0
        snapshotted = False

        for raw in fh:
            ln = raw.strip()
            if not ln:
                continue
            if ln.startswith("#"):
                try:
                    new_t = int(ln[1:])
                except ValueError:
                    continue
                # Before advancing time, if we're about to cross into the window
                # for the first time, snapshot the current_value as the t0 state.
                if not snapshotted and new_t >= t0_ps:
                    last_value_before_t0 = dict(current_value)
                    snapshotted = True
                cur_t = new_t
                if cur_t > t1_ps:
                    break
                continue
            val, vid = _parse_change(ln)
            if vid is None or vid not in interested_ids:
                continue
            old = current_value.get(vid)
            current_value[vid] = val
            if cur_t >= t0_ps:
                # Ensure snapshot was taken if we jumped straight into the window
                if not snapshotted:
                    last_value_before_t0 = {k: v for k, v in current_value.items() if k != vid}
                    # Include old of the signal being changed
                    if old is not None:
                        last_value_before_t0[vid] = old
                    snapshotted = True
                changes.append({
                    "time_ns": round(cur_t * timescale_ps / 1000.0, 4),
                    "signal":  hier_id_to_name(vid, id_to_hier),
                    "old":     old,
                    "new":     val,
                    "_id":     vid,
                })

        # If we never entered the window (all changes pre-t0), snapshot now
        if not snapshotted:
            last_value_before_t0 = dict(current_value)

    # Build initial state map per requested signal
    initial_state = []
    for hier, vid in hier_to_id.items():
        initial_state.append({
            "signal": hier,
            "value":  last_value_before_t0.get(vid, "?"),
        })

    # Clean changes (drop internal _id)
    for c in changes:
        c.pop("_id", None)

    out = {
        "timescale_ps":      timescale_ps,
        "t0_ns":             args.t0,
        "t1_ns":             args.t1,
        "initial_state":     initial_state,
        "changes":           [c for c in changes if args.t0 <= c["time_ns"] <= args.t1],
        "unresolved_signals": unresolved,
    }
    blob = json.dumps(out, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(blob)
    else:
        print(blob)
    return 0


def hier_id_to_name(vid: str, id_to_hier: dict[str, str]) -> str:
    return id_to_hier.get(vid, vid)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
