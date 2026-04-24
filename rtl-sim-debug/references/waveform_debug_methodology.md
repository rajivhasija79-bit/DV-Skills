# Waveform Debug Methodology — `.vcd` and `.fsdb`

Format-agnostic procedure. Only the extraction step differs between `.vcd` (use `scripts/vcd_window.py`) and `.fsdb` (delegate to the runtime agent's fsdb capability).

## Step 0 — Preconditions
- Failure Digest exists with `fail_time`, `hierarchy`, `message_id`.
- Classification (possibly provisional) exists.
- Interface has been named (from message + hierarchy).

## Step 1 — Resolve the signal set

1. Parse the Verdi `.rc` with `scripts/rc_parse.py <rc> --format json`.
   Output shape:
   ```json
   {
     "groups": {
       "<group_name>": {
         "signals": [ { "hier": "tb.u_dut.u_axi.awvalid", "radix": "hex" }, ... ],
         "radix": "hex"
       }, ...
     }
   }
   ```
2. Pick the group whose name or signals match the interface (case-insensitive substring match: `axi`, `ddr`, `apb`, …).
3. If none match, use the full union of signals from the `.rc` as a first pass.
4. If the `.rc` has gaps (e.g., missing a critical control signal), augment by searching the RTL for the interface's port declaration and adding its signals. Limit the augmentation to ≤ 50 additional signals per pass.

## Step 2 — Define the inspection window

| Scenario | `t0` | `t1` |
|----------|------|------|
| Fatal/error at `T` | `T - 2 us` | `T + 100 ns` |
| Assertion at `T` | `T - 500 ns` | `T + 20 ns` |
| Hang (last activity at `T_last`) | `T_last - 5 us` | `T_last` |
| X-prop (first `X` at `T`) | `T - 100 ns` | `T + 10 ns` |

Widen later if the evidence points before `t0`. Never widen the *first* pass beyond the table — keep the initial view small.

## Step 3 — Windowed extraction

### VCD
```
scripts/vcd_window.py <vcd> \
    --signals <signal_list_file> \
    --t0 <ns> --t1 <ns> \
    --out trace.json
```

Output `trace.json`:
```json
{
  "timescale": "1ps",
  "t0_ns": 1000, "t1_ns": 2000,
  "initial_state": [
    { "signal": "tb.u_dut.u_axi.awvalid", "value": "0" }, ...
  ],
  "changes": [
    { "time_ns": 1001.2, "signal": "tb.u_dut.u_axi.awvalid", "old": "0", "new": "1" }, ...
  ],
  "unresolved_signals": [ "..." ]
}
```

### FSDB
Delegate to the runtime. The extraction MUST return the same JSON shape as above. A typical Verdi-capable runtime produces this natively; if not, a conservative fallback is `fsdb2vcd` (if available on the host) followed by `vcd_window.py`.

## Step 4 — Error-to-signal checklist

Walk the `changes` list and the `initial_state`. For the interface type, answer:

### AXI (AR/R/AW/W/B)
- Valid/Ready handshake complete for each transaction in-window?
- Any `x`/`z` on any `*valid`, `*ready`, id, addr, resp, strb?
- `resp` = SLVERR (2) or DECERR (3) on any beat?
- IDs returned match IDs issued?
- `*len` consistent with number of data beats?
- Back-pressure: any `valid=1` with `ready=0` for > N cycles?

### APB
- `psel`/`penable`/`pready` handshake correct?
- `pslverr` asserted?
- `paddr` stable through access?

### DDR / DFI
- Refresh / activate / read / write sequencing to JEDEC timing (tRC, tRCD, tRP, tRAS)?
- DFI command/address signals integrity?

### Generic control
- Clocks alive and at expected frequency through window?
- Resets deasserted before first observed transaction?
- Any `X`/`Z` on single-bit control signals?

Record answers as a bulleted list with citations to `changes[]` rows.

## Step 5 — Identify the suspect signal(s)

Rank signals that anomalously changed (or failed to change) near `fail_time`:
1. Directly flagged by the checklist.
2. Control signals whose value at `fail_time` differs from the expected value derived from spec/protocol.
3. Data signals that went `X` or to a known-invalid encoding.

Typically 1–3 signals carry the root signal. Pick the *earliest-diverging* one.

## Step 6 — Handoff to driver tracing

Feed the suspect signal into `references/rtl_hierarchy_traversal.md`. The evidence accumulated so far — the waveform trace, the anomaly row, the `file:line` of the interface declaration — is the starting point of the causal chain.

## Output of Phase 6

Return to the orchestrator a **Waveform Evidence Record**:

```json
{
  "interface":           "<name>",
  "window_ns":           [t0, t1],
  "signal_set":          ["..."],
  "checklist_answers":   [ { "q": "...", "a": "...", "row_ref": <idx> } ],
  "suspect_signal":      "tb.u_dut.u_axi.u_decoder.awaddr_dec",
  "anomaly_time_ns":     1234.5,
  "anomaly_description": "awaddr_dec became X at 1234.5ns, 3ns after awvalid rise"
}
```
