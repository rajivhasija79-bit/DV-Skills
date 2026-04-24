---
name: rtl-sim-debug
description: Debug failing or hung VCS+UVM RTL simulations. Triggers on UVM_ERROR, UVM_FATAL, sim hang, testcase failure, waveform debug, assertion failure, X-propagation, .vcd/.fsdb inspection, or any request to root-cause an RTL simulation issue. Orchestrates log triage, classification (TB vs RTL vs config vs env), JIRA + regression-history correlation, waveform-driven driver tracing across large RTL hierarchies, and produces a JIRA-ready writeup (RTL bugs) or a concrete edit (TB/config bugs). Agent-agnostic — works on any skill-aware runtime. Auto-dispatches to domain sub-skills named rtl-sim-debug-<subsystem> when matching triggers are present.
contract_version: 1
---

# rtl-sim-debug — orchestration

You are assisting a design verification engineer on a VCS + UVM flow. Follow this workflow exactly when a sim failure, hang, UVM_ERROR/UVM_FATAL, assertion failure, X-prop, waveform inspection, or RTL-bug-triage request arrives. Do not skip phases; if evidence is missing, ask for it or note the gap before proceeding.

## Heavy-task directive (agent-agnostic)

For any step that must scan a >100 MB file, walk an RTL hierarchy of more than ~50 modules, or search a large JIRA/regression corpus: if your runtime supports launching a subagent, delegate that step to a subagent with a narrowly scoped prompt and return only the structured result (digest, driver line, ranked ticket list) to the main context. If the runtime does not support subagents, perform the step with streaming/chunked reads using the provided scripts under `scripts/`, never loading the whole artifact into context.

All helper scripts are Python 3 stdlib-only and invoked via shell. They are accelerators; the reference docs describe manual equivalents.

## Phase 1 — Intake

Confirm which artifacts are available. Ask for anything missing *and* clearly needed for the failure class. **RTL directory and DV directory are mandatory** — ask for them immediately if absent.

| Artifact | Required? | Notes |
|----------|-----------|-------|
| sim log | yes | path + size |
| RTL directory | yes | full DUT tree (SV-package `.f` alone is insufficient) |
| DV directory | yes | TB source |
| SV-package `.f` filelists | optional | scope compiled files |
| waveform dump (`.vcd` or `.fsdb`) | when waveform debug needed | format-agnostic; see §Phase 6 |
| Verdi `.rc` file | strongly preferred | curated interface signal sets |
| spec doc(s) | when RTL vs spec comparison needed | |
| testcase-understanding output | when available | expected stimulus/checkers |
| register-model output | when register access involved | address map + fields |
| JIRA corpus | yes (always provided per user) | append-only; indexed incrementally |
| regression-failure history | optional | can reclassify env vs RTL |
| failing command line / plusargs / seed | yes | for reproduction |

Do not proceed past Phase 1 if a required mandatory artifact is missing.

## Phase 2 — Large-log triage (500 MB+)

Never read the log end-to-end. See `references/log_triage_for_large_files.md`.

1. Run `scripts/log_extract.py <log> --window 200 --out <digest.json>` (or follow the manual streamed-scan steps in the reference).
2. The script emits a **Failure Digest**: `{ first_failure: { line, byte, time, phase, hierarchy, message_id, file_line, raw_excerpt }, all_fatal_error_offsets[], hang_indicators{ last_phase, objection_trace_present, last_activity_time }, stats{ size_mb, lines, scan_duration_s } }`.
3. Respect `references/benign_messages.yaml` when selecting the first *real* failure. If a candidate matches a benign pattern, skip to the next.
4. After the run, if the user calls out a message as "noise / ignore", offer to append it to `references/benign_messages.yaml`.

Output of this phase: the Failure Digest JSON (keep it in context — it is small).

## Phase 3 — Classify hypothesis

Using `references/failure_taxonomy.md`, place the failure in **one** of:
- **TB** — sequence, driver, monitor, `config_db`, factory override, phase ordering, objection leak.
- **RTL** — assertion, protocol violation, X-prop, reset/CDC, spec mismatch.
- **Config** — plusarg, build flag, compile order, seed sensitivity.
- **Env** — infrastructure, stale incremental build, tool version.

Record the hypothesis **and** the specific evidence from the digest that supports it. If ambiguous, list the top 2 and the smallest experiment that would disambiguate.

## Phase 4 — JIRA corpus correlation (always-on, incremental)

Per `references/jira_correlation.md`:
1. Build/refresh the index: `scripts/jira_parse.py --corpus <dir_or_files> --index-file <path>`.
   - Index defaults to `<corpus_dir>/.rtl-sim-debug.jira.idx.json` unless overridden.
   - Script is idempotent; only new/changed files are parsed.
2. Build the signature key from the digest: `{ message_id, component_tail, file:line, assertion_name }`.
3. Query: `scripts/jira_parse.py --query --index-file <path> --signature <json>` returns ranked hits.
4. Summarize the top 3 with ticket id, root cause, fix. Classify the current failure as **same**, **similar**, or **new** relative to the corpus.

## Phase 4b — Regression-history correlation (when provided, incremental)

Per `references/regression_history_correlation.md`:
1. Refresh index: `scripts/regression_parse.py --source <path> --index-file <path>`.
   - On first use for a given source, the script prompts to confirm column mappings, then caches them in `<source>.rtl-sim-debug.mapping.json`.
2. Query: `scripts/regression_parse.py --query <testcase> --index-file <path>`.
3. Answer:
   - Is this testcase **newly-failing**, **chronic**, or **flaky**?
   - Is the failure **isolated** or part of a **broader wave** (many tests failing today)?
4. If broader wave → strong push toward **Env/Config** classification; revisit Phase 3.

## Phase 5 — Source corroboration

- Open RTL/TB source around the Failure Digest's `file:line` before hypothesizing further. Read first, hypothesize second.
- If `testcase-understanding` output was provided, align the failure against the expected stimulus/checker flow.
- If `register-model` output was provided and the failure involves register access, verify address/field/reset-value expectations.

## Phase 6 — Waveform debug (`.vcd` or `.fsdb`)

See `references/waveform_debug_methodology.md` for the full playbook. Format-agnostic; only extraction differs.

### 6a. Log error → interface
- From the Failure Digest's hierarchy + message text, identify the interface (AXI slave port, APB, custom protocol, etc.).
- Parse the Verdi `.rc`: `scripts/rc_parse.py <rc_file> --format json`. Prefer `.rc` signals as the primary list. Augment only if gaps.

### 6b. Inspection window
- Default: `[fail_time - 2us, fail_time + 100ns]`.
- Hangs: `[last_transaction_success, fail_time]`.

### 6c. Windowed extraction

**If `.fsdb`:** instruct the runtime (or its fsdb-capable subagent) to open the dump and emit, for the resolved signal list within `[t0, t1]`:
- Initial-state snapshot at `t0` (signal → value)
- Value-change table: `time | signal | old → new`

**If `.vcd`:**
```
scripts/vcd_window.py <vcd> --signals <signal_list_file> --t0 <ns> --t1 <ns> --out <trace.json>
```
Emits the same shape.

Both paths produce identical output structure. Never read the whole dump.

### 6d. Error-to-signal mapping

For each resolved interface, answer this fixed checklist from the waveform trace:
1. Was the protocol handshake completed correctly around `fail_time`?
2. Any `X` or `Z` on control signals in the window?
3. Did `resp` go to SLVERR / DECERR? When? Which transaction id?
4. Do request/response IDs match?
5. Any back-pressure / timeout pattern (valid high, ready low for > threshold)?
6. Clock/reset integrity over the window?

Record answers with citations to waveform rows.

### 6e. Driver tracing — backward through hierarchy

When a suspect signal is identified, trace its driver back to its source per `references/rtl_hierarchy_traversal.md`:

1. **Scope the search.** Use the suspect signal's hierarchical path. Only search RTL files that belong to modules on that path. Use the filelist(s) when available; otherwise scope by the RTL/DV dirs plus the hierarchy path.
2. **One hop at a time.** For `a.b.c.sig`:
   - Find `sig`'s assignment inside module `c` using `scripts/rtl_trace.py --module c --signal sig --filelist <f> [--filelists a.f b.f] [--rtl-root <dir>]`.
   - If combinational from inputs → trace the driving input on `c`'s port upward to `b`.
   - If registered from internal → trace the `D` input within `c`.
   - If driven by a submodule instance → step down into that instance.
3. **Stop conditions.** Primary input, TB driver, constant, or a known-good source (clock/reset/PLL output).
4. **Re-extract waveform at each hop** for the newly traced signal; never re-read the whole dump.
5. **Offload big hops** to a subagent when the candidate module set is large.

### 6f. Evidence record

Produce a **causal chain**: `driver@time → intermediate signals → observable fault`. Each hop must cite `file:line` and a waveform row. This is the deliverable of Phase 6.

## Phase 7 — Root cause + next action

- State root cause in one sentence; attach the causal chain as evidence.
- **If cause is RTL:** produce a JIRA-ready writeup. Do **not** propose RTL edits.
  - Title · signature · environment (sim cmd, seed, plusargs) · reproduction · observed vs expected · waveform excerpt · suggested owner/IP.
- **If cause is TB/Config:** propose the minimal concrete edit as a diff (file:line + before/after) and a validation run plan.
- **If ambiguous:** propose the smallest disambiguating experiment (extra probe, new assertion, plusarg, seed sweep).

## Phase 8 — Exit summary

One compact block. Copy-pasteable into a ticket or review:

```
Classification:  <TB|RTL|Config|Env>
Root cause:      <one sentence>
Evidence chain:  <ordered list with file:line + waveform refs>
Action:          <fix diff | JIRA draft | next experiment>
Confidence:      <low|medium|high>
Residual risks:  <what remains uncertain>
JIRA similar:    <ticket ids, if any>
Regression context: <new|chronic|flaky|wave>
```

## Domain dispatch (seamless plug-in)

After Phases 3 and 6a, build the **Domain Signature**:

```
{
  "interface_keywords":  [ strings pulled from log message + digest ],
  "hierarchy_tokens":    [ tokens from the failure hierarchy path ],
  "rtl_module_prefixes": [ prefixes observed on the path ],
  "log_message_ids":     [ ids from the digest ]
}
```

Then:
1. Enumerate every installed sibling skill named `rtl-sim-debug-*` (any skill-aware runtime can list skills by directory prefix).
2. For each, read its frontmatter `domain_triggers`. A skill matches if **any** regex/prefix in any of its trigger groups matches the signature.
3. For every matching skill: assemble the **Debug Context Package** (schema below) and invoke that skill with it. Run matches in parallel if the runtime supports it.
4. Merge each matching skill's response into the exit summary, tagging each hypothesis with the domain it came from. No match → generic RCA only.
5. Refuse skills whose `contract_version` is greater than this skill's `contract_version`.

### Debug Context Package (parent → domain, JSON)

```json
{
  "contract_version": 1,
  "failure_digest": { "time": ..., "phase": ..., "hierarchy": ..., "message_id": ..., "file_line": ..., "raw_excerpt": "..." },
  "classification": { "class": "...", "confidence": "...", "evidence": "..." },
  "regression_context": { "newly_failing": false, "flakiness": 0.0, "broader_wave": false },
  "interface": { "name": "...", "type": "...", "signals": ["..."], "rc_file_entries": ["..."] },
  "waveform_window": { "format": "vcd|fsdb", "path": "...", "t0": 0, "t1": 0, "signals_extracted": ["..."] },
  "rtl_trace": [ { "file": "...", "line": 0, "assignment": "...", "time": 0 } ],
  "jira_hits":  [ { "id": "...", "similarity": 0.0, "root_cause": "...", "fix": "..." } ],
  "artifacts":  { "log": "...", "rtl_root": "...", "dv_root": "...", "filelists": ["..."], "spec_refs": ["..."], "tc_understanding": "...", "reg_model": "..." }
}
```

### Expected domain-skill response (JSON)

```json
{
  "contract_version": 1,
  "protocol_hypotheses": [ { "cause": "...", "evidence_refs": ["..."], "confidence": "..." } ],
  "extra_checks":        [ { "what": "...", "how": "...", "expected": "..." } ],
  "likely_fix_or_jira":  { "...": "..." },
  "additional_signals":  [ "..." ]
}
```

The `additional_signals` list can be fed back into Phase 6c for a refined waveform view if the domain skill needs more visibility.

## References

Load these only when relevant to the current phase:

- `references/log_triage_for_large_files.md` — Phase 2
- `references/failure_taxonomy.md` — Phase 3
- `references/jira_correlation.md` — Phase 4
- `references/regression_history_correlation.md` — Phase 4b
- `references/waveform_debug_methodology.md` — Phase 6
- `references/verdi_rc_parsing.md` — Phase 6a
- `references/rtl_hierarchy_traversal.md` — Phase 6e
- `references/uvm_error_patterns.md` — message id lookup
- `references/debug_playbooks.md` — per-scenario drill-downs
- `references/vcs_uvm_tips.md` — plusargs, flags, backtrace reading
- `references/domain_skill_contract.md` — template for new domain skills
- `references/benign_messages.yaml` — noise filter (starts empty; grows)
