# RTL Hierarchy Traversal — Backward Driver Tracing

For designs with thousands of IPs, never grep the whole RTL tree. Walk the suspect signal back one hop at a time, always scoped to the modules that are actually on the signal's hierarchical path.

## Inputs to each hop
- `signal_hier`: full hierarchical path to the suspect signal, e.g., `tb.u_soc.u_ddr.u_ctrl.cmd_q_rd_en`.
- `rtl_root`, `dv_root`, optional `filelist(s)`.
- Waveform window (to re-extract the next signal's trace after the hop).

## Algorithm

```
while True:
    mod, sig = split_last(signal_hier)      # mod = "tb.u_soc.u_ddr.u_ctrl", sig = "cmd_q_rd_en"
    mod_file = resolve_module_file(mod, filelist, rtl_root)
    drivers = rtl_trace(mod_file, sig)       # list of (file:line, assignment_type, rhs)
    if len(drivers) == 0:
        # sig is an input port → step out one level
        parent_hier, port = split_last(signal_hier)  # parent_hier = "tb.u_soc.u_ddr"
        inst = last_segment(mod)                    # u_ctrl
        # Find the connection at the parent that drives u_ctrl's port `sig`
        signal_hier = find_instance_port_conn(parent_mod_file, inst, sig)
        continue
    if driver_is_register(drivers):
        signal_hier = replace_last(signal_hier, d_input_expr(drivers))
        continue
    if driver_is_submodule(drivers):
        # Step down into the submodule; the submodule output equals a submodule's internal
        sub_inst, sub_port = parse_submodule_driver(drivers)
        signal_hier = f"{mod}.{sub_inst}.{sub_port}"
        continue
    if driver_is_constant_or_primary(drivers):
        return drivers
    # Combinational from inputs: step to the driving expression's signals
    signal_hier = replace_last(signal_hier, rhs_of(drivers))
```

After each hop, re-extract the waveform for `signal_hier` over the same window (narrowing as you converge on the root).

## Scoping the file search

Use this precedence:
1. **Filelist(s)**: one or more `.f` files. `rtl_trace.py --filelist top.f` / `--filelists a.f b.f c.f`. The script unions their entries.
2. **Module cache**: on first run against a filelist, `rtl_trace.py` builds a `{module_name: file_path}` cache (`.rtl-sim-debug.mod.cache.json` next to the filelist). Subsequent hops are O(1).
3. **Directory walk fallback**: if no filelist, search `<rtl_root>` and `<dv_root>` with `find ... -name '*.sv' -o -name '*.v' -o -name '*.vh'`, but only **under directories that match tokens of the hierarchy path** (e.g., if the hierarchy contains `u_ddr`, prefer `rtl_root/**/ddr*`).

## Tool

```
scripts/rtl_trace.py \
    [--filelist one.f | --filelists a.f b.f | --rtl-root <dir> --dv-root <dir>] \
    --module <module_name> --signal <signal_name> \
    [--cache-file <path>] [--json]
```

Output (JSON):
```json
{
  "module_file": "rtl/ddr/ddr_ctrl.sv",
  "drivers": [
    {
      "file": "rtl/ddr/ddr_ctrl.sv",
      "line": 412,
      "kind": "always_ff|assign|submodule|port|constant",
      "rhs": "cmd_q_wptr != cmd_q_rptr",
      "rhs_signals": ["cmd_q_wptr", "cmd_q_rptr"],
      "submodule_inst": null,
      "submodule_port": null
    }
  ]
}
```

## Heuristics to stay sane

- **Cap hops per session** (default 12). If you haven't reached a root in 12 hops, you're probably tracing the wrong signal; restart from a different suspect.
- **Prefer the earliest-diverging signal** on every hop. If two signals diverge simultaneously, pick the one with fewer fan-in signals (narrower trace).
- **Don't follow `clk` or `rst`** past the first hop unless the root-cause hypothesis is clock/reset.
- **Mark primary inputs / constants / TB drivers as terminals** and stop.

## Offloading

If at a hop the candidate module set (filelist entries under the relevant hierarchy tokens) exceeds ~50 files, dispatch a subagent with this exact shape:

> Using `rtl_trace.py`, find the driver of `<signal>` in module `<module>` using `<filelist>`. Return only the JSON driver record.

Main context receives the 10-line JSON, not the grepped content.
