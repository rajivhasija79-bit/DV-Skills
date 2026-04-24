# Failure Taxonomy

Classify every failure into **one** of four classes. Never claim a class without citing evidence from the Failure Digest or waveform.

## Classes

### TB — testbench bug
Signals the fault originates in the UVM verification environment, not the DUT.

**Evidence patterns:**
- Message originates from UVM components only (hierarchy under `uvm_test_top.*`), not RTL.
- `config_db::get` failure, missing factory override, NULL sequencer/driver handle.
- Phase-ordering error: a component accessed a resource before the phase it was set in.
- Objection leak / drain-time hang with a specific component holding the objection.
- Scoreboard mismatch where RTL transaction is correct (check via waveform) but TB predicted wrong.
- Virtual sequence issued a stimulus the DUT was not configured to accept.

**Common message ids:** `CFGNTS`, `NOMATCHC`, `OBJTN_CLEAR`, `OVRDFAIL`, `ILLBRDCST`, custom TB errors.

### RTL — DUT bug
The DUT's RTL violated its spec or protocol.

**Evidence patterns:**
- SVA / assertion fires inside the DUT hierarchy.
- Protocol checker (e.g., AXI VIP monitor, UVM checker) reports a DUT-side violation with waveform evidence.
- `X` / `Z` propagated into functional path (not just debug observers).
- Reset/CDC: signal glitch after reset release; metastability on a CDC boundary.
- Spec mismatch confirmed by comparing waveform to the provided spec doc.

**Common message ids:** assertion names ending in `_a`/`_sva`, VIP-specific ids like `AXI4_ERRS_AWVALID_STABLE`, `RCVPH`, `PROTVIO`.

### Config — environment configuration bug
Correct RTL + correct TB, wrong knobs.

**Evidence patterns:**
- A `+plusarg` is missing or has the wrong value; the failure stops happening when corrected.
- Wrong build flag (e.g., missing `-debug_access+all`, stale coverage exclusion).
- Seed-sensitive failure that masks an actual issue but the knob change is the real fix.
- Compile order wrong; a package's `typedef` resolved to an older definition.

### Env — environment / infrastructure
Tool, build, or infra issue; nothing wrong with RTL/TB/Config per se.

**Evidence patterns:**
- Same testcase used to pass; nothing in DUT changed; many unrelated tests failing today.
- Tool version mismatch, license server outage, corrupted simv.
- Stale incremental compile: the object matches neither old nor new source.
- File system / NFS errors in the log.

## Decision procedure

1. **Start with the source of the first-real-failure message.**
   - UVM component path only → TB bias.
   - Inside RTL hierarchy or DUT SVA → RTL bias.
   - Tool-level (`Error-[...]`) with no DUT/TB context → Env/Config.
2. **Check regression history.**
   - Newly failing today + many unrelated tests also failing today → flip to Env.
   - Chronic failure on the same testcase only → stays in original class.
   - Flaky across seeds → likely RTL (races / X-prop) or TB race.
3. **Look at waveform evidence (if already gathered).**
   - DUT port signals correct, checker flagged anyway → TB.
   - DUT port signals wrong → RTL.
4. **If still ambiguous**, list top-2 classes with an explicit disambiguation experiment:
   - Run same seed on yesterday's build → separates Env from DUT change.
   - Run with `+plusarg=known_good` → separates Config.
   - Rerun with `+UVM_MAX_QUIT_COUNT=1` and richer verbosity → narrows TB vs RTL.

## Output shape

```
{
  "class": "TB|RTL|Config|Env",
  "confidence": "low|medium|high",
  "evidence": "<one sentence citing digest line + waveform ref if any>",
  "alt_class": null | { "class": "...", "disambiguation_experiment": "..." }
}
```
