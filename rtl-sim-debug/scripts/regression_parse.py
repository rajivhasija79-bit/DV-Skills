#!/usr/bin/env python3
"""
regression_parse.py — Incremental regression-failure-history indexer + query.

Sniffs the source format (CSV / JSON / NDJSON). Caches the column-to-schema
mapping in a sidecar (<source>.rtl-sim-debug.mapping.json) so the user is
only prompted once per source. Maintains an append-only index.

Usage:
    # Index (or refresh) a source
    regression_parse.py --source <path> [--index-file <path>] [--mapping-file <path>]

    # Query one testcase
    regression_parse.py --query <testcase> --index-file <path>

Canonical schema:
    { testcase, seed, result, commit, timestamp, duration, log_path }
"""

from __future__ import annotations
import argparse, csv, datetime as _dt, fcntl, io, json, os, re, sys
from typing import Any

CONTRACT_VERSION = 1
CANONICAL_FIELDS = ["testcase", "seed", "result", "commit", "timestamp", "duration", "log_path"]

RESULT_DEFAULT_NORMALIZE = {
    "PASS": "pass", "PASSED": "pass", "OK": "pass", "0": "pass",
    "FAIL": "fail", "FAILED": "fail", "FAILURE": "fail", "1": "fail",
    "TIMEOUT": "timeout", "TIMED_OUT": "timeout",
    "ERROR": "error", "ERR": "error",
}


# ---------- format sniffing ----------

def sniff_format(path: str) -> str:
    with open(path, "r", errors="replace") as f:
        head = f.read(4096)
    s = head.lstrip()
    if not s:
        return "unknown"
    if s[0] == "[" or s[0] == "{":
        return "json"
    first_line = s.splitlines()[0] if s.splitlines() else ""
    # NDJSON: each line is a json object
    try:
        json.loads(first_line)
        return "ndjson"
    except Exception:
        pass
    if "\t" in first_line and "," not in first_line:
        return "tsv"
    if "," in first_line:
        return "csv"
    return "unknown"


# ---------- mapping ----------

def load_mapping(path: str) -> dict | None:
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_mapping(path: str, mapping: dict) -> None:
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)


def infer_mapping(columns: list[str]) -> dict:
    """Heuristic mapping of detected columns to canonical names."""
    lower = {c.lower(): c for c in columns}
    def find(*keys):
        for k in keys:
            for col_l, col in lower.items():
                if k == col_l or k in col_l:
                    return col
        return None
    return {
        "testcase":  find("testcase", "tc_name", "test", "name"),
        "seed":      find("seed"),
        "result":    find("result", "status", "pass_fail", "outcome"),
        "commit":    find("commit", "build_hash", "rev", "sha"),
        "timestamp": find("timestamp", "time", "started_at", "date", "when"),
        "duration":  find("duration", "elapsed", "runtime", "elapsed_s"),
        "log_path":  find("log", "logfile", "log_path"),
    }


def confirm_mapping_interactively(columns: list[str], inferred: dict) -> dict:
    """If run in a TTY, ask user to confirm/correct; otherwise accept inferred."""
    print(f"detected columns: {columns}", file=sys.stderr)
    print(f"inferred mapping: {inferred}", file=sys.stderr)
    if not sys.stdin.isatty():
        # Non-interactive: accept inferred (the caller will cache it)
        return inferred
    resp = input("mapping OK? [Y/n]: ").strip().lower()
    if resp in ("", "y", "yes"):
        return inferred
    out = dict(inferred)
    for field in CANONICAL_FIELDS:
        cur = out.get(field) or ""
        new = input(f"  {field} -> column name [{cur}]: ").strip()
        if new:
            out[field] = new
    return out


# ---------- parsing ----------

def iter_rows(path: str, fmt: str):
    """Yield dicts of raw row data."""
    if fmt == "csv":
        with open(path, "r", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row
    elif fmt == "tsv":
        with open(path, "r", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                yield row
    elif fmt == "json":
        with open(path, "r", errors="replace") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        for row in items:
            if isinstance(row, dict):
                yield row
    elif fmt == "ndjson":
        with open(path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    else:
        return


def apply_mapping(row: dict, mapping: dict, result_norm: dict) -> dict:
    out = {}
    for field in CANONICAL_FIELDS:
        col = mapping.get(field)
        val = row.get(col) if col else None
        if val is None and col:
            # Try case-insensitive lookup
            for k, v in row.items():
                if k and k.lower() == col.lower():
                    val = v
                    break
        out[field] = val
    # Normalize result
    r = str(out.get("result") or "").strip()
    out["result"] = result_norm.get(r.upper(), r.lower() or "unknown")
    # Canonicalize timestamp to ISO-ish if possible
    if out.get("timestamp"):
        out["timestamp"] = _iso(out["timestamp"])
    # Duration as float seconds if numeric
    if out.get("duration") is not None and out["duration"] != "":
        try:
            out["duration"] = float(out["duration"])
        except Exception:
            out["duration"] = None
    else:
        out["duration"] = None
    return out


def _iso(t: Any) -> str:
    s = str(t).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return _dt.datetime.strptime(s[: len(fmt) + 6], fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return s


# ---------- index ----------

def load_index(path: str) -> dict:
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                idx = json.load(f)
            if idx.get("contract_version") == CONTRACT_VERSION:
                return idx
        except Exception:
            pass
    return {
        "contract_version":      CONTRACT_VERSION,
        "last_ingested_row_key": None,
        "testcases":             {},
        "daily_totals":          {},
    }


def save_index(path: str, idx: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
        except OSError:
            pass
        json.dump(idx, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def row_key(row: dict) -> str:
    # Timestamp-first so append-only sources (which are timestamp-sorted)
    # have monotonically increasing keys across the whole stream.
    return f"{row.get('timestamp','') or ''}|{row.get('testcase','') or ''}|{row.get('seed','') or ''}"


def ingest(source: str, index_file: str, mapping_file: str) -> dict:
    fmt = sniff_format(source)
    if fmt == "unknown":
        print(f"[regression_parse] cannot detect format of {source}", file=sys.stderr)
        sys.exit(2)

    rows_iter = iter_rows(source, fmt)
    # Peek first row to get column names (for CSV)
    first_row = next(rows_iter, None)
    if first_row is None:
        print("no rows found", file=sys.stderr)
        return load_index(index_file)
    columns = list(first_row.keys())

    mapping = load_mapping(mapping_file)
    if mapping is None:
        inferred = infer_mapping(columns)
        mapping = {
            "format":            fmt,
            "column_map":        inferred,
            "result_normalize":  RESULT_DEFAULT_NORMALIZE,
        }
        mapping["column_map"] = confirm_mapping_interactively(columns, inferred)
        save_mapping(mapping_file, mapping)

    col_map = mapping["column_map"]
    result_norm = {**RESULT_DEFAULT_NORMALIZE, **mapping.get("result_normalize", {})}

    idx = load_index(index_file)
    last_key = idx.get("last_ingested_row_key")

    # Process rows (starting with first_row)
    ingested = 0
    def _process(rr: dict):
        nonlocal ingested, last_key
        r = apply_mapping(rr, col_map, result_norm)
        key = row_key(r)
        if last_key and key <= last_key:
            return
        _upsert(idx, r)
        last_key = key if (last_key is None or key > last_key) else last_key
        ingested += 1

    _process(first_row)
    for rr in rows_iter:
        _process(rr)

    idx["last_ingested_row_key"] = last_key
    save_index(index_file, idx)
    print(f"ingested rows: {ingested}, total testcases: {len(idx['testcases'])}", file=sys.stderr)
    return idx


def _upsert(idx: dict, r: dict) -> None:
    tc = r.get("testcase") or ""
    if not tc:
        return
    tcs = idx["testcases"].setdefault(tc, {
        "runs":                    [],
        "rolling_fail_rate_30d":   0.0,
        "first_seen_fail":         None,
        "last_pass_commit":        None,
        "last_fail_commit":        None,
    })
    entry = {
        "seed":     r.get("seed"),
        "result":   r.get("result"),
        "commit":   r.get("commit"),
        "timestamp": r.get("timestamp"),
        "duration": r.get("duration"),
    }
    tcs["runs"].append(entry)
    # Cap runs per testcase to most recent 500 to bound memory
    if len(tcs["runs"]) > 500:
        tcs["runs"] = tcs["runs"][-500:]

    if r.get("result") == "pass":
        tcs["last_pass_commit"] = r.get("commit") or tcs["last_pass_commit"]
    elif r.get("result") == "fail":
        tcs["last_fail_commit"] = r.get("commit") or tcs["last_fail_commit"]
        if not tcs["first_seen_fail"] and r.get("timestamp"):
            tcs["first_seen_fail"] = r["timestamp"]

    # Rolling 30d fail rate (approx): look at last 100 runs, count fails
    last = tcs["runs"][-100:]
    total = sum(1 for x in last if x["result"] in ("pass", "fail"))
    fails = sum(1 for x in last if x["result"] == "fail")
    tcs["rolling_fail_rate_30d"] = round(fails / total, 4) if total else 0.0

    # Daily totals
    day = (r.get("timestamp") or "")[:10]
    if day:
        dt = idx["daily_totals"].setdefault(day, {"runs": 0, "fails": 0, "new_fails": 0})
        dt["runs"] += 1
        if r.get("result") == "fail":
            dt["fails"] += 1
            # "new_fails" heuristic: first fail seen for this testcase on this day
            if tcs["first_seen_fail"] and tcs["first_seen_fail"].startswith(day):
                dt["new_fails"] += 1


def query(tc: str, idx: dict) -> dict:
    tcs = idx["testcases"].get(tc)
    today = _dt.date.today().strftime("%Y-%m-%d")
    dt_today = idx["daily_totals"].get(today, {"runs": 0, "fails": 0, "new_fails": 0})

    # baseline: average fails across last 7 days excluding today
    days = sorted([d for d in idx["daily_totals"] if d < today])[-7:]
    if days:
        avg = sum(idx["daily_totals"][d]["fails"] for d in days) / len(days)
    else:
        avg = 0.0
    broader_wave = dt_today["fails"] > 3 * avg and dt_today["fails"] >= 5

    if not tcs:
        return {
            "testcase": tc,
            "classification": "unknown",
            "flakiness": 0.0,
            "rolling_fail_rate_30d": 0.0,
            "last_pass_commit": None,
            "first_seen_fail": None,
            "daily_context": {"broader_wave_today": broader_wave,
                              "today_fails": dt_today["fails"],
                              "today_avg_fails_7d": round(avg, 1)},
        }

    # Classification
    runs = tcs["runs"][-50:]
    pass_count = sum(1 for r in runs if r["result"] == "pass")
    fail_count = sum(1 for r in runs if r["result"] == "fail")
    cls = "passing"
    if fail_count == 0 and pass_count > 0:
        cls = "passing"
    elif fail_count > 0 and pass_count == 0:
        cls = "chronic"
    elif fail_count > 0 and pass_count > 0:
        # Check if pass/fail on same commit with different seeds → flaky
        by_commit: dict[str, set] = {}
        for r in runs:
            by_commit.setdefault(r.get("commit") or "", set()).add(r["result"])
        flaky = any("pass" in v and "fail" in v for v in by_commit.values())
        cls = "flaky" if flaky else "newly_failing"
    if tcs["first_seen_fail"] and tcs["first_seen_fail"].startswith(today) and cls not in ("flaky",):
        cls = "newly_failing"

    flakiness = (pass_count * fail_count) / (pass_count + fail_count) ** 2 if (pass_count + fail_count) else 0.0
    return {
        "testcase":              tc,
        "classification":        cls,
        "flakiness":             round(flakiness, 3),
        "rolling_fail_rate_30d": tcs["rolling_fail_rate_30d"],
        "last_pass_commit":      tcs["last_pass_commit"],
        "first_seen_fail":       tcs["first_seen_fail"],
        "daily_context": {
            "broader_wave_today": broader_wave,
            "today_fails":        dt_today["fails"],
            "today_avg_fails_7d": round(avg, 1),
        },
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None)
    ap.add_argument("--index-file", default=None)
    ap.add_argument("--mapping-file", default=None)
    ap.add_argument("--query", default=None, help="Testcase name to query")
    args = ap.parse_args(argv)

    if args.query:
        if not args.index_file:
            print("--query requires --index-file", file=sys.stderr)
            return 2
        idx = load_index(args.index_file)
        print(json.dumps(query(args.query, idx), indent=2, sort_keys=True))
        return 0

    if not args.source:
        ap.print_help()
        return 2

    index_file = args.index_file or (args.source + ".rtl-sim-debug.reg.idx.json")
    mapping_file = args.mapping_file or (args.source + ".rtl-sim-debug.mapping.json")
    ingest(args.source, index_file, mapping_file)
    print(f"index: {index_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
