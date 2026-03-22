---
id: dv-coverage-closure
name: "S10 — DV Coverage Closure"
version: "1.0"
description: >
  Analyses VCS urg coverage reports (code + functional), identifies gaps,
  suggests test stubs or exclusions, generates .el exclusion files,
  evaluates per-milestone closure criteria, and produces a combined
  sign-off HTML report integrating S7 (assertions), S9 (regression),
  and S10 (coverage) data.
inputs:
  required:
    - merged.vdb (from S9 dv-regression)
    - dv_regression_data.json (from S9)
    - dv_assertions_data.json (from S7)
  optional:
    - coverage_config.yaml (thresholds + exclusion patterns)
outputs:
  - dv_coverage_data.json
  - exclusions/combined.el (+ per-type .el files)
  - stubs/tests/*.sv, stubs/sequences/*.sv
  - signoff_report/index.html
  - milestone_results.json
scripts:
  - skills/common/scripts/parse_coverage_report.py
  - skills/common/scripts/generate_coverage_closure.py
  - skills/common/scripts/gen_coverage_signoff_report.py
  - skills/common/scripts/check_environment.py
tags: [coverage, urg, sign-off, closure, functional-coverage, code-coverage, exclusions]
---

# S10 — DV Coverage Closure

## Overview

S10 is the final DV skill. It consumes outputs from S7 (assertion CHK_IDs) and S9 (regression logs, merged coverage VDB) to analyse coverage gaps, guide the engineer through exclusion/stub decisions, and produce a formal sign-off report.

**Prerequisite skills:** S7 (dv-assertions) and S9 (dv-regression) must have run first.

---

## Step 1 — Validate Prerequisites and Environment

Check that all required inputs exist before proceeding.

### 1a Environment check
```
python3 skills/common/scripts/check_environment.py --skill s10
```
Required tools: `urg` (VCS coverage merge), `vcs` on PATH. No pip dependencies.

### 1b Locate required files
Search the project `dv/` directory for:

| File | Source Skill | Required |
|------|-------------|----------|
| `dv/sim/regression/*/merged.vdb` | S9 | YES |
| `dv/sim/results/dv_regression_data.json` | S9 | YES |
| `dv/dv_assertions_data.json` | S7 | YES |
| `dv/sim/regression/coverage_config.yaml` | Manual or auto-generated | NO (defaults used) |

If `merged.vdb` or `dv_regression_data.json` is missing, STOP and print:
```
  ✗ S10 requires S9 regression outputs.
  → Run S9 (dv-regression) first: it generates merged.vdb and dv_regression_data.json.
  → If you have an existing VDB, set the path manually in coverage_config.yaml.
```

If `dv_assertions_data.json` is missing, continue but note that assertion cross-reference will be skipped.

### 1c Write default coverage_config.yaml (if not present)
```yaml
# coverage_config.yaml — DV Coverage Closure thresholds and exclusion patterns
# Edit to adjust per-project needs.

thresholds:
  dv_i:
    line_pct:          80.0
    toggle_pct:        70.0
    branch_pct:        75.0
    expression_pct:    70.0
    functional_pct:    60.0
    regression_pass:   90.0
  dv_c:
    line_pct:          95.0
    toggle_pct:        90.0
    branch_pct:        95.0
    expression_pct:    90.0
    functional_pct:    85.0
    regression_pass:   98.0
  dv_f:
    line_pct:          99.0
    toggle_pct:        95.0
    branch_pct:        99.0
    expression_pct:    99.0
    fsm_pct:           99.0
    functional_pct:    99.0
    regression_pass:  100.0

# Patterns for auto-classifying gaps as excludable (regex on instance path)
auto_exclude_patterns:
  - ".*_dft_.*"          # DFT/scan logic
  - ".*_tb_.*"           # Testbench-internal code
  - ".*vendor_ip.*"      # Third-party/vendor IP
  - ".*_unused.*"        # Explicitly unused logic
  - ".*_tie.*"           # Tied-off signals
  - ".*_dummy.*"         # Placeholder modules
```

---

## Step 2 — Generate Fresh urg Text Reports

Re-run urg to produce machine-parseable text reports from `merged.vdb`.

```bash
# Text reports (for parsing)
urg -full64 -dir <merged.vdb> \
    -report <output_dir>/urgReport \
    -format text \
    -l <output_dir>/urg_run.log

# HTML reports (for browsing — linked from sign-off report)
urg -full64 -dir <merged.vdb> \
    -report <output_dir>/urgReport_html \
    -format html
```

Key output files parsed in subsequent steps:
- `urgReport/dashboard.txt` — top-level per-type summary
- `urgReport/hier.txt` — per-instance code coverage hierarchy
- `urgReport/groups.txt` — functional coverage covergroup bins

If `hier.txt` or `groups.txt` are missing after urg runs, print a warning and skip the affected parse step.

---

## Step 3 — Parse Code Coverage

Parse `urgReport/hier.txt` for line, toggle, branch, expression, and FSM coverage.

```bash
python3 skills/common/scripts/parse_coverage_report.py \
    --mode code \
    --hier   <output_dir>/urgReport/hier.txt \
    --out    <output_dir>/gaps/code_gaps.json
```

**What this produces:**

For each instance in the hierarchy, extract:
- Module name and instance path
- Per-type: covered count, total count, coverage percentage
- For gaps (< threshold): list of uncovered items with file path, line number, detail description

**Display a code coverage summary table after parsing:**

```
  Code Coverage Summary
  ─────────────────────────────────────────────────────────────
  Type          Covered   Total    Pct     DV-F Thr  Delta
  ─────────────────────────────────────────────────────────────
  Line          1240      1250     99.2%   99.0%     +0.2%  ✓
  Toggle         890       980     90.8%   95.0%     -4.2%  ✗
  Branch         430       440     97.7%   99.0%     -1.3%  ✗
  Expression     210       215     97.7%   99.0%     -1.3%  ✗
  FSM             48        50     96.0%   99.0%     -3.0%  ✗
  ─────────────────────────────────────────────────────────────
  Total code gaps requiring attention: 23
```

---

## Step 4 — Parse Functional Coverage

Parse `urgReport/groups.txt` for covergroup bins.

```bash
python3 skills/common/scripts/parse_coverage_report.py \
    --mode functional \
    --groups <output_dir>/urgReport/groups.txt \
    --out    <output_dir>/gaps/func_gaps.json
```

**What this produces:**

For each covergroup/coverpoint/bin:
- Hit count, at_least count, covered/uncovered status
- Full bin path: `scope::covergroup::coverpoint::bin_name`

Ignore: `ignore_bins`, `illegal_bins`, bins with `at_least 0` (weight-zero).

**Display a functional coverage summary:**

```
  Functional Coverage Summary
  ─────────────────────────────────────────────────────────────
  Covergroup              Bins    Hit    Missed  Coverage
  ─────────────────────────────────────────────────────────────
  cg_apb_register         12      10     2       83.3%
  cg_uart_tx              20      15     5       75.0%
  cg_uart_rx               8       8     0      100.0%   ✓
  ─────────────────────────────────────────────────────────────
  Total: 40 bins, 33 covered, 7 uncovered (82.5%)
```

---

## Step 5 — Cross-reference with Assertions (S7 data)

If `dv_assertions_data.json` is present, annotate each gap:
- Check if the gap's instance path matches any assertion module
- Check if the gap's signal/line is exercised by a `cover property` statement
- Tag `assertion_backed: true` for gaps already proven via formal or SVA coverage

Assertion-backed gaps are **strong exclusion candidates** — they have functional correctness verified by another mechanism even if code coverage is not driven.

---

## Step 6 — Classify Gaps

Classify each gap as:

| Class | Meaning | Default Action |
|-------|---------|---------------|
| `excludable` | Unreachable, tool-generated, DFT, vendor IP, assertion-backed | Offer exclusion |
| `coverable` | Reachable logic with no existing test stimulus | Offer test stub |
| `requires_analysis` | Cross-coverage, parameterised logic, complex FSM | Ask user |

Classification uses `auto_exclude_patterns` from `coverage_config.yaml` plus these rules:
- Toggle of `tie_*`, `unused_*`, `one_*`, `zero_*` signals → `excludable`
- FSM state reachable only during reset → `excludable` if `rst_n` in state condition
- Functional bin with value combination outside DUT spec → `excludable`
- Uncovered branch in `generate` block with fixed parameters → `excludable`

Print gap count by class before interactive step.

---

## Step 7 — Interactive Gap Resolution

Walk through each gap and ask the user to decide: **exclude**, **generate stub**, or **skip**.

```
  Gap Resolution (23 gaps total: 14 excludable, 7 coverable, 2 requires-analysis)
  ────────────────────────────────────────────────────────────────────────────────

  [GAP 1/23]  Type: Toggle  Class: EXCLUDABLE
  Instance  : tb_top.dut.u_ctrl.gen_dft_logic
  Signal    : scan_en  (0→1 direction)
  File      : rtl/ctrl.sv:142
  Reason    : Matches pattern '.*_dft_.*' — DFT-only logic

  Draft exclusion:
    EXCL_TOGGLE tb_top.dut.u_ctrl.gen_dft_logic scan_en 01 -comment "DFT scan enable, not driven in functional mode"

  Accept? [Y=exclude / s=stub / n=skip] :
```

For `coverable` gaps:
```
  [GAP 8/23]  Type: Functional  Class: COVERABLE
  Bin       : cg_uart_tx::cp_data_value::bin_0xFF
  Scope     : tb_top.dut.u_uart_tx
  Hit count : 0 / 1
  Suggestion: Add a test that sends UART byte 0xFF

  Draft stub:
    stubs/sequences/seq_uart_tx_0xff_coverage.sv

  Generate stub? [Y=stub / e=exclude / n=skip] :
```

**Batch mode** (`--non-interactive`): accepts all suggested defaults automatically.

After all gaps resolved, print decision summary:
```
  Decisions: 14 excluded, 7 stubs queued, 2 skipped
```

---

## Step 8 — Generate Exclusion Files

Write `.el` files for all accepted exclusions.

```bash
python3 skills/common/scripts/generate_coverage_closure.py \
    --mode exclusions \
    --decisions <output_dir>/gaps/gap_decisions.json \
    --out       <output_dir>/exclusions/
```

**Output files:**

```
exclusions/
  line_exclusions.el
  toggle_exclusions.el
  branch_exclusions.el
  expression_exclusions.el
  fsm_exclusions.el
  functional_exclusions.el
  combined.el          ← concatenation of all above
```

**`.el` file format (urg Synopsys standard):**
```
// =============================================================================
// Exclusion File: toggle_exclusions.el
// Generated by: S10 dv-coverage-closure
// Date: 2026-03-22
// REVIEW REQUIRED before sign-off
// =============================================================================

EXCL_TOGGLE tb_top.dut.u_ctrl.gen_dft_logic scan_en 01
    -comment "DFT scan enable, not driven in functional mode"

EXCL_FSM_STATE tb_top.dut.u_arb.fsm RESET_STATE
    -comment "RESET_STATE only entered at power-on; excluded per design spec"

EXCL_COVBIN tb_top.dut.u_uart cg_uart_tx cp_parity bin_none
    -comment "Parity disabled by UART_CTRL.PAR_EN=0 in all test configs"
```

**Supported exclusion types:**
- `EXCL_LINE <scope> <file> <line> -comment "..."`
- `EXCL_TOGGLE <scope> <signal> [01|10] -comment "..."`
- `EXCL_BRANCH <scope> <file> <line> <branch_idx> -comment "..."`
- `EXCL_EXPRESSION <scope> <file> <line> <expr_idx> <term_idx> -comment "..."`
- `EXCL_FSM_STATE <scope> <fsm> <state> -comment "..."`
- `EXCL_FSM_TRANS <scope> <fsm> <from> <to> -comment "..."`
- `EXCL_COVGROUP <scope> <group> -comment "..."`
- `EXCL_COVPOINT <scope> <group> <point> -comment "..."`
- `EXCL_COVBIN <scope> <group> <point> <bin> -comment "..."`

**Re-run urg with exclusions applied:**
```bash
urg -full64 -dir <merged.vdb> \
    -elfile exclusions/combined.el \
    -report urgReport_excl \
    -format text
```
Parse `urgReport_excl/dashboard.txt` and write `coverage_after_exclusions.json`.

---

## Step 9 — Generate Test and Sequence Stubs

For each gap where the decision is "stub", generate a UVM `.sv` stub.

```bash
python3 skills/common/scripts/generate_coverage_closure.py \
    --mode stubs \
    --decisions <output_dir>/gaps/gap_decisions.json \
    --tb-data   dv/dv_tb_data.json \
    --out       <project_dv_dir>/
```

**Stub structure for functional coverage gap:**
```systemverilog
// COVERAGE STUB — Generated by S10 dv-coverage-closure
// Gap ID  : FUNC_GAP_003
// Target  : cg_uart_tx::cp_data_value::bin_0xFF
// Scope   : tb_top.dut.u_uart_tx
// Action  : Drive UART TX byte value = 0xFF to hit this bin
// Status  : NEEDS_ENGINEER_IMPLEMENTATION
// ─────────────────────────────────────────────────────────
class uart_tx_0xff_coverage_seq extends uart_vip_base_seq;
  `uvm_object_utils(uart_tx_0xff_coverage_seq)
  function new(string name = "uart_tx_0xff_coverage_seq");
    super.new(name);
  endfunction

  task body();
    uart_vip_seq_item txn;
    // TODO: drive UART byte 0xFF to hit cg_uart_tx::cp_data_value::bin_0xFF
    txn = uart_vip_seq_item::type_id::create("txn");
    start_item(txn);
    if (!txn.randomize() with { data == 8'hFF; })
      `uvm_fatal("RAND", "Randomization failed")
    finish_item(txn);
  endtask
endclass
```

**Stub structure for code coverage gap (FSM state / branch):**
```systemverilog
// COVERAGE STUB — Generated by S10 dv-coverage-closure
// Gap ID  : CODE_GAP_007
// Target  : tb_top.dut.u_arb.fsm — state STALL_STATE
// File    : rtl/arb.sv:88
// Action  : Drive stimulus that causes arbiter to enter STALL_STATE
// Status  : NEEDS_ENGINEER_IMPLEMENTATION
// ─────────────────────────────────────────────────────────
class arb_stall_state_test extends apb_uart_base_test;
  `uvm_component_utils(arb_stall_state_test)
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    // TODO: implement stimulus to reach arb FSM STALL_STATE
    // Hint: arb.sv:88 — condition for entering STALL_STATE:
    //   (request_count > MAX_PENDING && ~grant_valid)
    phase.raise_objection(this);
    // ... stimulus here ...
    phase.drop_objection(this);
  endtask
endclass
```

Write `stubs/stubs_manifest.json`:
```json
{
  "generated_at": "...",
  "stubs": [
    {
      "gap_id": "FUNC_GAP_003",
      "stub_type": "sequence",
      "file": "dv/sequences/uart/uart_tx_0xff_coverage_seq.sv",
      "class_name": "uart_tx_0xff_coverage_seq",
      "coverage_target": "cg_uart_tx::cp_data_value::bin_0xFF",
      "status": "generated"
    }
  ]
}
```

---

## Step 10 — Milestone Closure Check

Evaluate per-milestone gates using post-exclusion coverage numbers.

```bash
python3 skills/common/scripts/generate_coverage_closure.py \
    --mode milestone \
    --coverage    <output_dir>/coverage_after_exclusions.json \
    --regression  dv/sim/results/dv_regression_data.json \
    --assertions  dv/dv_assertions_data.json \
    --config      <output_dir>/coverage_config.yaml \
    --out         <output_dir>/milestone_results.json
```

**Milestone gates evaluated:**

| Metric | DV-I | DV-C | DV-F |
|--------|------|------|------|
| Line coverage | ≥ 80% | ≥ 95% | ≥ 99% |
| Toggle coverage | ≥ 70% | ≥ 90% | ≥ 95% |
| Branch coverage | ≥ 75% | ≥ 95% | ≥ 99% |
| Expression coverage | ≥ 70% | ≥ 90% | ≥ 99% |
| FSM coverage | — | — | ≥ 99% |
| Functional coverage | ≥ 60% | ≥ 85% | ≥ 99% |
| Regression pass rate | ≥ 90% | ≥ 98% | 100% |
| All CHK_IDs passing | — | ✓ | ✓ |
| Zero unresolved gaps | — | — | ✓ |

Thresholds are overridable via `coverage_config.yaml`.

**Print milestone table:**
```
  Milestone Closure Check
  ─────────────────────────────────────────────────────────────
  Gate   Status  Blocking Metric
  ─────────────────────────────────────────────────────────────
  DV-I   ✓ PASS  —
  DV-C   ✓ PASS  —
  DV-F   ✗ FAIL  Toggle coverage 90.8% < 95.0% required
                  FSM coverage 96.0% < 99.0% required
  ─────────────────────────────────────────────────────────────
```

---

## Step 11 — Write dv_coverage_data.json

Assemble the complete coverage data JSON from all intermediate outputs.

```bash
python3 skills/common/scripts/generate_coverage_closure.py \
    --mode write-data \
    --project  <project_name> \
    --out      dv/dv_coverage_data.json
```

**Schema highlights:**

```json
{
  "schema_version": "1.0",
  "generated_at": "<ISO8601>",
  "project_name": "<project>",
  "tool": "urg",
  "vdb_path": "<path>",
  "code_coverage": {
    "line":       { "covered": 1240, "total": 1250, "pct": 99.2, "excluded": 5 },
    "toggle":     { "covered": 890,  "total": 980,  "pct": 90.8, "excluded": 20 },
    "branch":     { "covered": 430,  "total": 440,  "pct": 97.7, "excluded": 3 },
    "expression": { "covered": 210,  "total": 215,  "pct": 97.7, "excluded": 2 },
    "fsm":        { "covered": 48,   "total": 50,   "pct": 96.0, "excluded": 1 },
    "instances": [ ... ]
  },
  "functional_coverage": {
    "total_bins": 40, "covered_bins": 33, "excluded_bins": 4, "pct": 82.5,
    "covergroups": [ ... ]
  },
  "gaps_summary": {
    "total_gaps": 23, "excludable": 14, "coverable": 7, "requires_analysis": 2,
    "excluded": 14, "stubs_generated": 7, "skipped": 2, "pending": 0
  },
  "exclusions": { ... },
  "stubs": { ... },
  "milestone_results": { ... },
  "sources": { ... }
}
```

---

## Step 12 — Generate Sign-off HTML Report

Produce the combined sign-off report integrating S7, S9, and S10 data.

```bash
python3 skills/common/scripts/gen_coverage_signoff_report.py \
    --coverage    dv/dv_coverage_data.json \
    --regression  dv/sim/results/dv_regression_data.json \
    --assertions  dv/dv_assertions_data.json \
    --milestone   <output_dir>/milestone_results.json \
    --project     <project_name> \
    --out         <output_dir>/signoff_report/index.html
```

**Report sections:**

1. **Header + Sign-off Banner** — GREEN/RED/YELLOW banner showing highest milestone achieved
2. **Milestone Gate Summary** — 3-column table (DV-I / DV-C / DV-F) with PASS/FAIL per metric
3. **Coverage Dashboard** — horizontal bars per metric with threshold markers
4. **Code Coverage Details** — per-instance hierarchy with gap list
5. **Functional Coverage Details** — per-covergroup/coverpoint/bin table
6. **Gap Analysis** — full gap list with decisions and stub references
7. **Assertions (S7)** — CHK_ID table with pass/fail status
8. **Regression Summary (S9)** — pass/fail counts, top failures, pass rate
9. **Exclusion Review** — all exclusions with justifications
10. **Recommended Actions** — auto-generated action items to close remaining gaps
11. **Audit Trail** — timestamps, urg version, VDB hash, git commit

The HTML is fully self-contained (no external dependencies) and can be emailed or checked in.

---

## Step 13 — Terminal Summary

Print the final summary to stdout and write `dv_coverage_closure_summary.txt`.

```
  ╔═══════════════════════════════════════════════════════════════╗
  ║              S10 DV Coverage Closure — Summary                ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  Project  : apb_uart                                          ║
  ║  Date     : 2026-03-22                                        ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  Milestone Status                                             ║
  ║  DV-I  ✓ PASS                                                 ║
  ║  DV-C  ✓ PASS                                                 ║
  ║  DV-F  ✗ FAIL  (2 metrics blocking)                          ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  Coverage (after exclusions)                                  ║
  ║  Line:        99.2%  Toggle: 90.8%  Branch: 97.7%            ║
  ║  Expression:  97.7%  FSM:    96.0%  Functional: 82.5%        ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  Gaps: 14 excluded | 7 stubs generated | 2 skipped           ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  Sign-off Report : sim/regression/signoff_report/index.html  ║
  ║  Coverage Data   : dv/dv_coverage_data.json                  ║
  ║  Exclusions      : sim/regression/exclusions/combined.el     ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║  Next Actions                                                 ║
  ║  → Implement 7 test stubs in stubs/                          ║
  ║  → Toggle coverage 90.8% needs +4.2% to reach DV-F          ║
  ║  → FSM coverage 96.0% needs +3.0% to reach DV-F             ║
  ╚═══════════════════════════════════════════════════════════════╝
```

Exit code: 0 if DV-F passes, 1 if DV-F fails (enables CI gating).

---

## Directory Layout

```
dv/
├── dv_coverage_data.json          ← main output
├── sim/
│   └── regression/
│       ├── merged.vdb             ← input from S9
│       ├── urgReport/             ← text reports (generated by Step 2)
│       ├── urgReport_html/        ← HTML reports
│       ├── urgReport_excl/        ← post-exclusion text reports
│       ├── gaps/
│       │   ├── code_gaps.json
│       │   ├── func_gaps.json
│       │   ├── annotated_gaps.json
│       │   ├── classified_gaps.json
│       │   └── gap_decisions.json
│       ├── exclusions/
│       │   ├── line_exclusions.el
│       │   ├── toggle_exclusions.el
│       │   ├── branch_exclusions.el
│       │   ├── expression_exclusions.el
│       │   ├── fsm_exclusions.el
│       │   ├── functional_exclusions.el
│       │   └── combined.el
│       ├── coverage_after_exclusions.json
│       ├── milestone_results.json
│       ├── coverage_config.yaml
│       └── signoff_report/
│           └── index.html
└── sequences/                     ← stubs placed alongside existing seqs
    └── <protocol>/
        └── *_coverage_seq.sv
```

---

## Integration Notes

### Makefile targets (added to `dv/sim/Makefile` by S9 but extended here)

```makefile
# S10 Coverage Closure
coverage_closure:
	python3 $(SCRIPTS)/generate_coverage_closure.py \
	    --project $(PROJECT) --vdb $(COV_DIR)/merged.vdb \
	    --reg-data $(COV_DIR)/dv_regression_data.json \
	    --assert-data dv/dv_assertions_data.json \
	    --out $(COV_DIR)

signoff_report:
	python3 $(SCRIPTS)/gen_coverage_signoff_report.py \
	    --coverage dv/dv_coverage_data.json \
	    --regression $(COV_DIR)/dv_regression_data.json \
	    --assertions dv/dv_assertions_data.json \
	    --milestone $(COV_DIR)/milestone_results.json \
	    --project $(PROJECT) \
	    --out $(COV_DIR)/signoff_report/index.html
	@echo "Sign-off report: $(COV_DIR)/signoff_report/index.html"

closure_full: cov_merge coverage_closure signoff_report
```
