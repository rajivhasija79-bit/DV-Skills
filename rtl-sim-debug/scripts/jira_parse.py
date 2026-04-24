#!/usr/bin/env python3
"""
jira_parse.py — Incremental JIRA bug-report corpus indexer + query.

The corpus is append-only and may grow indefinitely. Never re-parse it all.
Maintain a JSON index next to the corpus; each run only parses files whose
sha1 differs from the index.

Usage:
    # Build or refresh index
    jira_parse.py --corpus <dir>          [--index-file <path>]
    jira_parse.py --corpus file1 file2... [--index-file <path>]

    # Query
    jira_parse.py --query --index-file <path> \
                  --signature '{"message_id":"...","component_tail":"...","file_line":"...","assertion_name":"..."}' \
                  [--top 5]

Supported input formats:
    - JSON: single object (Jira REST) with "fields" OR list of such objects
    - XML:  Jira XML export with <item><key>.../<summary>... etc.
    - Text/markdown: per-ticket file; id extracted from filename or first line
"""

from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, sys, time
from typing import Any
import xml.etree.ElementTree as ET


CONTRACT_VERSION = 1

TICKET_ID_RE   = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
UVM_TAG_RE     = re.compile(r"\b(UVM_(?:ERROR|FATAL|WARNING|INFO)|Error-\[[A-Za-z0-9_\-]+\])")
ASSERT_RE      = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*_(?:a|sva))\b")
MODULE_PREFIX_RE = re.compile(r"\b(u_[a-z0-9_]+|[a-z]+_ctrl|[a-z]+_phy|[a-z]+_dec)\b")
FILE_BASENAME_RE = re.compile(r"\b([A-Za-z0-9_]+\.(?:sv|v|svh|vh))\b")


def sha1_of(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_corpus(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for name in files:
                    if name.startswith("."):
                        continue
                    if name.endswith((".json", ".xml", ".txt", ".md")):
                        out.append(os.path.join(root, name))
        elif os.path.isfile(p):
            out.append(p)
    return sorted(out)


def parse_json_file(path: str) -> list[dict]:
    with open(path, "r", errors="replace") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    items = data if isinstance(data, list) else [data]
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        fields = it.get("fields", it)
        rec = {
            "id":          it.get("key") or fields.get("key") or fields.get("id") or "",
            "summary":     fields.get("summary", "") or "",
            "description": fields.get("description", "") or "",
            "components":  _extract_components(fields.get("components")),
            "resolution":  _extract_resolution(fields.get("resolution")),
        }
        if not rec["id"]:
            # Try to derive from filename
            m = TICKET_ID_RE.search(os.path.basename(path))
            rec["id"] = m.group(1) if m else os.path.basename(path)
        out.append(rec)
    return out


def _extract_components(v) -> list[str]:
    if not v:
        return []
    if isinstance(v, list):
        return [str(x.get("name") if isinstance(x, dict) else x) for x in v]
    return [str(v)]


def _extract_resolution(v) -> str:
    if not v:
        return ""
    if isinstance(v, dict):
        return v.get("name", "") or v.get("description", "") or ""
    return str(v)


def parse_xml_file(path: str) -> list[dict]:
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []
    root = tree.getroot()
    out = []
    # Jira RSS export: channel/item
    for item in root.iter("item"):
        rec = {
            "id":          _xml_text(item, "key") or _xml_text(item, "title"),
            "summary":     _xml_text(item, "summary") or _xml_text(item, "title"),
            "description": _xml_text(item, "description"),
            "components":  [c.text or "" for c in item.findall(".//component")],
            "resolution":  _xml_text(item, "resolution"),
        }
        if rec["id"]:
            m = TICKET_ID_RE.search(rec["id"])
            if m:
                rec["id"] = m.group(1)
            out.append(rec)
    return out


def _xml_text(el, tag) -> str:
    c = el.find(tag)
    return (c.text or "").strip() if c is not None and c.text else ""


def parse_text_file(path: str) -> list[dict]:
    with open(path, "r", errors="replace") as f:
        body = f.read()
    base = os.path.basename(path)
    m = TICKET_ID_RE.search(base) or TICKET_ID_RE.search(body[:200])
    ticket_id = m.group(1) if m else base

    lines = body.splitlines()
    first_non_empty = next((l for l in lines if l.strip()), "")
    summary = first_non_empty[:200]

    # Extract sectioned fields if present
    def grab_section(name: str) -> str:
        pat = re.compile(rf"^\s*{name}\s*:\s*(.*)$", re.I | re.M)
        m = pat.search(body)
        if not m:
            return ""
        # Grab until next ALL-CAPS header or blank gap
        start = m.end()
        tail = body[start:]
        # crude: cut at next "^<Word>:" line
        n = re.search(r"\n[A-Z][A-Za-z]+:\s", tail)
        return (m.group(1) + (tail[: n.start()] if n else tail)).strip()

    return [{
        "id":          ticket_id,
        "summary":     grab_section("Summary") or summary,
        "description": grab_section("Description") or body[:2000],
        "components":  [c.strip() for c in (grab_section("Components") or "").split(",") if c.strip()],
        "resolution":  grab_section("Resolution"),
    }]


def parse_file(path: str) -> list[dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return parse_json_file(path)
    if ext == ".xml":
        return parse_xml_file(path)
    # .txt / .md / other → text
    return parse_text_file(path)


def build_signature_hints(rec: dict) -> list[str]:
    blob = " ".join([rec.get("summary", ""), rec.get("description", ""),
                     " ".join(rec.get("components", [])), rec.get("resolution", "")])
    hints = set()
    for rx in (UVM_TAG_RE, ASSERT_RE, MODULE_PREFIX_RE, FILE_BASENAME_RE):
        for m in rx.finditer(blob):
            hints.add(m.group(1))
    # Add component names as hints too
    for c in rec.get("components", []):
        if c:
            hints.add(c.lower())
    return sorted(hints)


def load_index(index_file: str) -> dict:
    if os.path.isfile(index_file):
        try:
            with open(index_file, "r") as f:
                idx = json.load(f)
                if idx.get("contract_version") == CONTRACT_VERSION:
                    return idx
        except Exception:
            pass
    return {
        "contract_version":   CONTRACT_VERSION,
        "last_indexed_mtime": None,
        "file_digests":       {},
        "records":            [],
    }


def save_index(index_file: str, idx: dict) -> None:
    tmp = index_file + ".tmp"
    with open(tmp, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
        except OSError:
            pass
        json.dump(idx, f, indent=2, sort_keys=True)
    os.replace(tmp, index_file)


def index(corpus_paths: list[str], index_file: str) -> dict:
    idx = load_index(index_file)
    existing_digests: dict[str, str] = idx["file_digests"]
    records_by_key: dict[tuple[str, str], dict] = {
        (r.get("source_file", ""), r.get("id", "")): r for r in idx["records"]
    }

    files = walk_corpus(corpus_paths)
    parsed_files = 0
    skipped = 0
    for path in files:
        try:
            sha = sha1_of(path)
        except OSError:
            continue
        if existing_digests.get(path) == sha:
            skipped += 1
            continue
        try:
            recs = parse_file(path)
        except Exception as e:
            print(f"[jira_parse] failed to parse {path}: {e}", file=sys.stderr)
            continue
        parsed_files += 1
        # Remove old records sourced from this file before re-adding
        records_by_key = {k: v for k, v in records_by_key.items() if k[0] != path}
        for r in recs:
            r["source_file"]      = path
            r["description_excerpt"] = (r.get("description") or "")[:500]
            r["signature_hints"]  = build_signature_hints(r)
            records_by_key[(path, r["id"])] = {
                "id":                  r["id"],
                "source_file":         path,
                "summary":             r.get("summary", ""),
                "components":          r.get("components", []),
                "description_excerpt": r["description_excerpt"],
                "resolution":          r.get("resolution", ""),
                "signature_hints":     r["signature_hints"],
            }
        existing_digests[path] = sha

    idx["file_digests"]       = existing_digests
    idx["records"]            = list(records_by_key.values())
    idx["last_indexed_mtime"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_index(index_file, idx)
    print(f"indexed: parsed={parsed_files}, skipped_unchanged={skipped}, total_records={len(idx['records'])}",
          file=sys.stderr)
    return idx


def query(index_file: str, signature: dict, top: int = 5) -> list[dict]:
    idx = load_index(index_file)
    msg_id   = (signature.get("message_id") or "").strip()
    comp     = (signature.get("component_tail") or "").strip().lower()
    file_ln  = (signature.get("file_line") or "").strip()
    assert_  = (signature.get("assertion_name") or "").strip()
    file_base = os.path.basename(file_ln.split(":")[0]) if file_ln else ""

    scored: list[tuple[float, dict]] = []
    for r in idx["records"]:
        hints = [h.lower() for h in r["signature_hints"]]
        score = 0.0
        if msg_id:
            if msg_id.lower() in hints: score += 2.0
            elif any(msg_id.lower() in h for h in hints): score += 1.0
        if assert_:
            if assert_.lower() in hints: score += 2.0
        if file_base:
            if file_base.lower() in hints: score += 1.0
        if comp:
            if any(comp in h for h in hints): score += 1.0
        # Exact bonuses on summary/components
        blob = " ".join([r["summary"].lower(), " ".join(c.lower() for c in r["components"])])
        if msg_id and msg_id.lower() in blob: score += 1.0
        if comp and comp in blob: score += 0.5
        if score > 0:
            # Normalize loosely by hint count
            norm = max(1, len(hints))
            scored.append((score / (1 + 0.05 * norm), r))
    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for sim, r in scored[: max(1, top)]:
        out.append({
            "id":          r["id"],
            "similarity":  round(sim, 3),
            "summary":     r["summary"],
            "components":  r["components"],
            "resolution":  r["resolution"],
            "root_cause":  _first_sentence(r.get("description_excerpt", "") or r.get("resolution", "")),
            "fix":         _find_fix_phrase(r.get("resolution", "") + " " + r.get("description_excerpt", "")),
            "source_file": r["source_file"],
        })
    return out


def _first_sentence(text: str) -> str:
    s = text.strip().split(". ")
    return (s[0][:200] + ".") if s and s[0] else ""


def _find_fix_phrase(blob: str) -> str:
    m = re.search(r"(fix(?:ed)?|resolution|workaround)\s*[:\-]\s*(.+?)(?:\.|$)", blob, re.I)
    return (m.group(2)[:200] + ".") if m else ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Incremental JIRA corpus indexer + query")
    ap.add_argument("--corpus", nargs="+", default=None, help="Corpus dir(s) or files")
    ap.add_argument("--index-file", default=None, help="Path to index JSON")
    ap.add_argument("--query", action="store_true", help="Run a query against the index")
    ap.add_argument("--signature", default=None, help="JSON signature for --query")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args(argv)

    # Default index location
    index_file = args.index_file
    if not index_file and args.corpus:
        first = args.corpus[0]
        base = first if os.path.isdir(first) else os.path.dirname(first) or "."
        index_file = os.path.join(base, ".rtl-sim-debug.jira.idx.json")

    if args.query:
        if not index_file or not os.path.isfile(index_file):
            print("query requires an existing --index-file", file=sys.stderr)
            return 2
        sig = json.loads(args.signature or "{}")
        hits = query(index_file, sig, args.top)
        print(json.dumps(hits, indent=2, sort_keys=True))
        return 0

    if args.corpus:
        if not index_file:
            print("need --index-file or --corpus to derive default", file=sys.stderr)
            return 2
        index(args.corpus, index_file)
        print(f"index: {index_file}")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
