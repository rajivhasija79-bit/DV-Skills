#!/usr/bin/env python3
"""
rtl_trace.py — Scoped driver-finder for SystemVerilog/Verilog modules.

Given a module name and a signal, find the RTL assignments / drivers of
that signal inside the module's file. Uses the filelist(s) or a directory
walk to locate the module's source. Builds a module-name → file cache on
first run to make subsequent hops O(1).

Usage:
    rtl_trace.py --module <m> --signal <s> \
        [--filelist a.f] [--filelists a.f b.f ...] \
        [--rtl-root <dir>] [--dv-root <dir>] \
        [--cache-file <path>] [--json]

Output JSON:
{
  "module_file": "rtl/.../foo.sv",
  "drivers": [
    { "file": "...", "line": N,
      "kind": "always_ff|assign|submodule|port|constant|unknown",
      "rhs": "...", "rhs_signals": ["..."],
      "submodule_inst": "u_bar", "submodule_port": "q" }
  ]
}
"""

from __future__ import annotations
import argparse, json, os, re, sys

SV_EXTS = (".sv", ".v", ".svh", ".vh")

MODULE_RE = re.compile(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)


def expand_filelist(path: str) -> list[str]:
    if not os.path.isfile(path):
        return []
    base = os.path.dirname(path)
    out: list[str] = []
    with open(path, "r", errors="replace") as f:
        for ln in f:
            ln = ln.split("//")[0].strip()
            if not ln or ln.startswith("#") or ln.startswith("-"):
                continue
            # env vars
            ln = os.path.expandvars(os.path.expanduser(ln))
            if not os.path.isabs(ln):
                ln = os.path.normpath(os.path.join(base, ln))
            # glob?
            if any(ch in ln for ch in "*?["):
                import glob
                out.extend(sorted(glob.glob(ln)))
            else:
                out.append(ln)
    return [x for x in out if x.endswith(SV_EXTS)]


def build_cache(files: list[str]) -> dict[str, str]:
    cache: dict[str, str] = {}
    for path in files:
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for m in MODULE_RE.finditer(text):
            name = m.group(1)
            # First-seen wins
            cache.setdefault(name, path)
    return cache


def load_or_build_cache(filelists: list[str], rtl_root: str | None, dv_root: str | None,
                       cache_file: str | None) -> dict[str, str]:
    if cache_file and os.path.isfile(cache_file):
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception:
            pass

    all_files: list[str] = []
    for f in filelists or []:
        all_files.extend(expand_filelist(f))
    for root in [rtl_root, dv_root]:
        if root and os.path.isdir(root):
            for r, _, names in os.walk(root):
                for n in names:
                    if n.endswith(SV_EXTS):
                        all_files.append(os.path.join(r, n))
    all_files = sorted(set(all_files))
    cache = build_cache(all_files)

    if cache_file:
        try:
            with open(cache_file, "w") as f:
                json.dump(cache, f, indent=2, sort_keys=True)
        except OSError:
            pass
    return cache


def find_module_body(path: str, module_name: str) -> tuple[int, int, list[str]] | None:
    """Return (start_line, end_line, lines_within) for the given module definition."""
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None
    start = None
    for i, ln in enumerate(lines):
        m = re.match(rf"^\s*module\s+{re.escape(module_name)}\b", ln)
        if m:
            start = i
            break
    if start is None:
        return None
    end = None
    depth = 0
    for j in range(start, len(lines)):
        if re.search(r"\bmodule\b", lines[j]) and not lines[j].lstrip().startswith("//"):
            depth += 1
        if re.search(r"\bendmodule\b", lines[j]):
            depth -= 1
            if depth <= 0:
                end = j
                break
    if end is None:
        end = len(lines) - 1
    return start, end, lines[start:end + 1]


def find_drivers(module_file: str, module_name: str, signal: str) -> list[dict]:
    body = find_module_body(module_file, module_name)
    if body is None:
        return []
    start_line, end_line, lines = body

    drivers: list[dict] = []
    sig_re = re.compile(rf"\b{re.escape(signal)}\b")

    # 1) Continuous assign statements:  assign <lhs> = <rhs>;
    assign_re = re.compile(rf"^\s*assign\s+.*?\b{re.escape(signal)}\b\s*(?:\[[^\]]*\])?\s*=\s*(.+?);", re.S)
    # Walk line-by-line for simplicity (multi-line assigns handled by join below).
    joined = "".join(lines)
    # Offsets map (char → line)
    line_offsets = []
    off = 0
    for i, l in enumerate(lines):
        line_offsets.append(off)
        off += len(l)
    def line_of(char_pos: int) -> int:
        import bisect
        return start_line + bisect.bisect_right(line_offsets, char_pos) - 1 + 1  # 1-based

    for m in re.finditer(r"\bassign\s+([^;]+);", joined, re.S):
        stmt = m.group(1)
        lhs_match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_\.]*(?:\[[^\]]*\])?)\s*=\s*(.+)", stmt, re.S)
        if not lhs_match:
            continue
        lhs, rhs = lhs_match.group(1), lhs_match.group(2)
        if not sig_re.search(lhs):
            continue
        drivers.append({
            "file":            module_file,
            "line":            line_of(m.start()),
            "kind":            "assign",
            "rhs":             rhs.strip()[:400],
            "rhs_signals":     sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", rhs)) - _sv_keywords()),
            "submodule_inst":  None,
            "submodule_port":  None,
        })

    # 2) always_ff / always @(posedge clk) non-blocking:  <sig> <= <rhs>;
    for m in re.finditer(
        rf"\b{re.escape(signal)}\b\s*(?:\[[^\]]*\])?\s*<=\s*([^;]+);", joined
    ):
        rhs = m.group(1)
        drivers.append({
            "file":            module_file,
            "line":            line_of(m.start()),
            "kind":            "always_ff",
            "rhs":             rhs.strip()[:400],
            "rhs_signals":     sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", rhs)) - _sv_keywords()),
            "submodule_inst":  None,
            "submodule_port":  None,
        })

    # 3) Blocking assign inside always_comb:  <sig> = <rhs>;  (not "==", not "<=", not continuous "assign")
    for m in re.finditer(
        rf"(?<![=<!])\b{re.escape(signal)}\b\s*(?:\[[^\]]*\])?\s*=\s*(?![=])([^;]+);", joined
    ):
        # Skip if this match is within a continuous-assign statement
        # (line begins with `assign`).
        line_start = joined.rfind("\n", 0, m.start()) + 1
        line_prefix = joined[line_start: m.start()].lstrip()
        if line_prefix.startswith("assign"):
            continue
        rhs = m.group(1)
        drivers.append({
            "file":            module_file,
            "line":            line_of(m.start()),
            "kind":            "blocking_assign",
            "rhs":             rhs.strip()[:400],
            "rhs_signals":     sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", rhs)) - _sv_keywords()),
            "submodule_inst":  None,
            "submodule_port":  None,
        })

    # 4) Submodule instantiation where this signal is a port:  foo u_foo (.<port>(<sig>))
    #    We scan for named port connections where the connection expression contains the signal.
    for m in re.finditer(
        rf"\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([^)]*\b{re.escape(signal)}\b[^)]*)\)", joined
    ):
        port = m.group(1)
        conn = m.group(2).strip()
        # Look backwards to find the instance name — scan lookback for the
        # most recent "<modname> <instname> (" pattern that opens the port list.
        pre = joined[max(0, m.start() - 2000): m.start()]
        inst = None
        for inst_m in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:#\([^)]*\)\s*)?\(",
            pre,
        ):
            # The last match in the lookback is the closest instantiation
            mod_cand, inst_cand = inst_m.group(1), inst_m.group(2)
            if mod_cand in _sv_keywords() or inst_cand in _sv_keywords():
                continue
            inst = inst_cand
        drivers.append({
            "file":            module_file,
            "line":            line_of(m.start()),
            "kind":            "submodule",
            "rhs":             conn[:200],
            "rhs_signals":     sorted(set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", conn)) - _sv_keywords()),
            "submodule_inst":  inst,
            "submodule_port":  port,
        })

    # 5) Port declaration:  input|output|inout ... <signal> [,;)]
    # For SV, declarations can span multiple lines within the module header.
    # We detect by checking that, walking backwards from the signal occurrence,
    # the most recent direction keyword on a non-empty earlier line or inline is a port direction.
    for m in re.finditer(rf"\b{re.escape(signal)}\b\s*(?:\[[^\]]*\])?\s*(?:,|;|\))", joined):
        # Check backward up to 300 chars for `input|output|inout` as the nearest keyword
        pre = joined[max(0, m.start() - 300): m.start()]
        keyword_m = None
        for km in re.finditer(r"\b(input|output|inout)\b", pre):
            keyword_m = km
        if not keyword_m:
            continue
        # Ensure there's no intervening ';' between keyword and signal (would end the decl)
        between = pre[keyword_m.end():]
        if ";" in between:
            continue
        sig_line_no = line_of(m.start())
        # Dedupe against existing port entries
        if any(d["kind"] == "port" and d["line"] == sig_line_no for d in drivers):
            continue
        drivers.append({
            "file":            module_file,
            "line":            sig_line_no,
            "kind":            "port",
            "rhs":             f"{keyword_m.group(1)} ... {signal}",
            "rhs_signals":     [],
            "submodule_inst":  None,
            "submodule_port":  None,
        })

    return drivers


_SV_KEYWORDS_CACHE: set[str] | None = None


def _sv_keywords() -> set[str]:
    global _SV_KEYWORDS_CACHE
    if _SV_KEYWORDS_CACHE is None:
        _SV_KEYWORDS_CACHE = set("""
            always always_comb always_ff always_latch and assign assume automatic before begin
            bind bins binsof bit break buf bufif0 bufif1 byte case casex casez cell chandle
            checker class clocking cmos config const constraint context continue cover
            covergroup coverpoint cross deassign default defparam design disable dist do edge
            else end endcase endchecker endclass endclocking endconfig endfunction endgenerate
            endgroup endinterface endmodule endpackage endpoint endprimitive endprogram
            endproperty endspecify endsequence endtable endtask enum event expect export
            extends extern final first_match for force foreach forever fork forkjoin function
            generate genvar global highz0 highz1 if iff ifnone ignore_bins illegal_bins
            implements implies import incdir include initial inout input inside instance int
            integer interface intersect join join_any join_none large let liblist library
            local localparam logic longint macromodule matches medium modport module nand
            negedge new nexttime nmos nor noshowcancelled not notif0 notif1 null or output
            package packed parameter pmos posedge primitive priority program property
            protected pull0 pull1 pulldown pullup pulsestyle_ondetect pulsestyle_onevent pure
            rand randc randcase randsequence rcmos real realtime ref reg reject_on release
            repeat restrict return rnmos rpmos rtran rtranif0 rtranif1 s_always s_eventually
            s_nexttime s_until s_until_with scalared sequence shortint shortreal showcancelled
            signed small soft solve specify specparam static string strong strong0 strong1
            struct super supply0 supply1 sync_accept_on sync_reject_on table tagged task this
            throughout time timeprecision timeunit tran tranif0 tranif1 tri tri0 tri1 triand
            trior trireg type typedef union unique unique0 unsigned until until_with untyped
            use uwire var vectored virtual void wait wait_order wand weak weak0 weak1 while
            wildcard wire with within wor xnor xor
        """.split())
    return _SV_KEYWORDS_CACHE


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True)
    ap.add_argument("--signal", required=True)
    ap.add_argument("--filelist", default=None)
    ap.add_argument("--filelists", nargs="+", default=None)
    ap.add_argument("--rtl-root", default=None)
    ap.add_argument("--dv-root", default=None)
    ap.add_argument("--cache-file", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    filelists = args.filelists or ([args.filelist] if args.filelist else [])
    if not filelists and not args.rtl_root and not args.dv_root:
        print("need --filelist/--filelists or --rtl-root/--dv-root", file=sys.stderr)
        return 2

    cache_file = args.cache_file
    if cache_file is None and filelists:
        cache_file = filelists[0] + ".rtl-sim-debug.mod.cache.json"

    cache = load_or_build_cache(filelists, args.rtl_root, args.dv_root, cache_file)
    module_file = cache.get(args.module)
    if not module_file or not os.path.isfile(module_file):
        out = {"module_file": None, "drivers": [],
               "error": f"module {args.module!r} not found in filelist/roots"}
        print(json.dumps(out, indent=2))
        return 0

    drivers = find_drivers(module_file, args.module, args.signal)
    out = {"module_file": module_file, "drivers": drivers}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
