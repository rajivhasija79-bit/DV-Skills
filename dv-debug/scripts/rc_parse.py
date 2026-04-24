#!/usr/bin/env python3
"""
rc_parse.py — Parse Verdi .rc signal-list files into a structured form.

Handles the common dialects:
 - nWave wvAddSignal / wvOpenGroup / wvCloseGroup / wvSetRadix commands
 - Plain hierarchical signal lists (slash- or dot-separated)
 - Comment lines starting with '#'

Usage:
    rc_parse.py <rc> --format json
    rc_parse.py <rc> --group AXI_WR
    rc_parse.py <rc> --flatten        # one hierarchical signal per line

Output JSON:
{
  "groups": {
    "<group>": {
      "signals": [ { "hier": "tb.u_dut...", "radix": "hex|dec|bin|None" } ]
    }
  }
}
"""

from __future__ import annotations
import argparse, json, os, re, sys

# A "signal-looking" token has a '/' or '.' and no shell-option leading dash.
_SIG_TOK_RE = re.compile(r'(?:\{([^{}]+)\}|"([^"]+)"|(?<!\S)(/[A-Za-z_0-9][^\s{}"]*|[A-Za-z_][A-Za-z0-9_./\[\]:]*\.[A-Za-z0-9_./\[\]:]+))')
WVOPEN_RE   = re.compile(r"wvOpenGroup\s+\"?([^\"\s]+)\"?", re.I)
WVCLOSE_RE  = re.compile(r"wvCloseGroup", re.I)
WVRADIX_RE  = re.compile(
    r"wvSetRadix\b[^\n]*?(?:-signal\s+\{([^}]+)\}|-signal\s+\"([^\"]+)\"|-signal\s+(\S+))[^\n]*?\s(hex|dec|bin|oct|ascii|sdec|udec|signed|unsigned)\b",
    re.I,
)
PLAIN_SIG_RE = re.compile(r"^([/.][A-Za-z0-9_]+(?:[./][A-Za-z0-9_\[\]:]+)+)\s*$")


def norm(sig: str) -> str:
    s = sig.strip().strip('"').strip("'").strip("{}")
    s = s.lstrip("/")
    s = s.replace("/", ".")
    return s


def parse(path: str) -> dict:
    groups: dict[str, dict] = {}
    cur = "default"
    radix_overrides: dict[str, str] = {}

    def ensure(g: str) -> dict:
        if g not in groups:
            groups[g] = {"signals": []}
        return groups[g]

    with open(path, "r", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s or s.startswith("#"):
                continue

            m = WVOPEN_RE.search(line)
            if m:
                cur = m.group(1)
                ensure(cur)
                continue
            if WVCLOSE_RE.search(line):
                cur = "default"
                continue
            m = WVRADIX_RE.search(line)
            if m:
                sig = norm(next(x for x in m.groups()[:3] if x))
                radix_overrides[sig] = m.group(4).lower()
                continue
            if re.search(r"\bwvAddSignal\b", line, re.I):
                # Find the LAST signal-looking token on the line (ignores -win, -colorIdx, ...)
                matches = list(_SIG_TOK_RE.finditer(line))
                if matches:
                    m = matches[-1]
                    sig = norm(next(x for x in m.groups() if x))
                    ensure(cur)["signals"].append({"hier": sig, "radix": None})
                continue
            m = PLAIN_SIG_RE.match(line)
            if m:
                ensure(cur)["signals"].append({"hier": norm(m.group(1)), "radix": None})
                continue

    # Apply radix overrides
    for g in groups.values():
        for entry in g["signals"]:
            r = radix_overrides.get(entry["hier"])
            if r:
                entry["radix"] = r

    # Remove empty default group if nothing landed in it
    if "default" in groups and not groups["default"]["signals"]:
        groups.pop("default")

    # Dedupe within each group
    for g in groups.values():
        seen = set()
        uniq = []
        for e in g["signals"]:
            key = (e["hier"], e["radix"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(e)
        g["signals"] = uniq

    return {"groups": groups}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Parse Verdi .rc")
    ap.add_argument("rc", help="Path to .rc file")
    ap.add_argument("--format", choices=["json"], default="json")
    ap.add_argument("--group", default=None, help="Return only this group")
    ap.add_argument("--flatten", action="store_true", help="Print one hierarchical signal per line")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.rc):
        print(f"rc not found: {args.rc}", file=sys.stderr)
        return 2

    parsed = parse(args.rc)
    if args.group:
        parsed = {"groups": {args.group: parsed["groups"].get(args.group, {"signals": []})}}

    if args.flatten:
        for g in parsed["groups"].values():
            for e in g["signals"]:
                print(e["hier"])
        return 0

    print(json.dumps(parsed, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
