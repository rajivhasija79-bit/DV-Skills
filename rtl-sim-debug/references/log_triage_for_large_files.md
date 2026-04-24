# Log Triage for Large Files (500 MB+)

## Goal
Extract a compact **Failure Digest** from a simulation log without ever loading the whole file into memory or into the agent's context.

## Strategy

### Single-pass streaming scan
Read the log line-by-line (or in fixed-size byte chunks). For each line, test against a prioritized list of regex patterns; record `(byte_offset, line_number, sim_time_if_present)` for hits. Discard the line body. Memory stays O(hits), not O(log size).

### Pattern priority (high → low)
1. `UVM_FATAL` — fatal, always wins.
2. `UVM_ERROR` — most common real failure.
3. `Error-[` — VCS errors (often pre-UVM or tool-level).
4. `Assertion failed|\$error|\$fatal` — SVA / $error.
5. `Objection` (when combined with stop/quit/drain) — hang signal.
6. `TIMEOUT|Simulation complete after .* reached`.
7. `Stopping at` — common run-end marker.
8. X-prop markers: ` X ` on known control signals, `X-propagation`.

### First-real-failure selection
1. Pick the earliest `UVM_FATAL`. If none, the earliest `UVM_ERROR` that is **not** in `benign_messages.yaml`.
2. A message matches a benign entry if its normalized form (strip sim-time prefix, file:line, address literals) matches the entry's regex.
3. If all `UVM_ERROR`s are benign, fall back to tool errors, then assertion failures.

### Structural extraction from the chosen line
From the first-real-failure line, extract:
- `sim_time` — parse the UVM time-stamp prefix `[@ <ns> ns]` or `[<time>]`.
- `uvm_phase` — next phase name mentioned in the surrounding 10 lines (`main_phase`, `run_phase`, etc.).
- `component_hierarchy` — full path in parentheses after the message id.
- `message_id` — the `[TAG_NAME]` immediately after UVM_ERROR/UVM_FATAL.
- `source_file:line` — usually right after the component path.

### Context window
Pull ±N lines around the chosen offset (default 200). This is the only part of the log that goes into the Failure Digest's `raw_excerpt`. Truncate individual lines at 1000 chars to protect against mega-lines.

### Hang detection (no fatal/error exists)
If no fatal/error hit, treat the run as hung:
1. Scan the tail 2000 lines for the last `phase_started` / `phase_ended`.
2. Look for an objection trace dump (`phase_dump_state`, `uvm_objection`).
3. Record the last simulation time seen in the tail.
4. If objections are held by specific components, record their hierarchies.

## Tooling

- `scripts/log_extract.py <log> --window 200 --out digest.json`
  - `--benign <path>` optional override of `references/benign_messages.yaml`.
  - `--signatures ...` optional override of pattern priority.
  - Prints a JSON Failure Digest (see SKILL.md Phase 2 for schema).
  - Single streaming pass; memory is bounded regardless of log size.

## Manual equivalent (if scripts are unavailable)

Use shell:

```
awk '/UVM_FATAL|UVM_ERROR|Error-\[|Assertion failed|Objection.*drain|TIMEOUT/ { print NR":"$0 }' big.log | head -200
```

Then:

```
sed -n '<N-200>,<N+200>p' big.log > window.txt
```

Read `window.txt` (always < 2 MB) into context.

## Noise (benign) list growth mechanism

Start from `references/benign_messages.yaml` (empty initially). The file has this shape:

```yaml
benign:
  - regex: "UVM_ERROR.*CFGNTS.*uvm_test_top\\.env\\.debug_agent.*"
    why: "Debug agent prints cfg warning on every build; harmless."
    added_by: "<user>"
    date: "2026-04-24"
```

When the user dismisses a message as noise during a debug session, propose adding it. Never add entries without user confirmation.
