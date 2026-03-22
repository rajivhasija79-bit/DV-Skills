---
name: dv-testplan
description: |
  Design Verification skill that generates a comprehensive, structured testplan
  Excel workbook (testplan.xlsx) from a hardware design spec. Accepts either a
  dv_spec_summary.json (output of dv-spec-parse / S1) or a raw spec file
  (PDF/DOCX/TXT/MD) directly.

  Use this skill whenever a user wants to:
  - Generate a DV testplan from a design spec or parsed spec JSON
  - Create a structured Excel testplan with features, testcases, coverage, checkers
  - Map design features to verification types (directed test, random test, coverpoint, checker)
  - Generate SystemVerilog covergroup/coverpoint code for functional coverage
  - Define checker IDs and types for a DV project
  - Plan milestone-tagged tests (DV-I, DV-C, DV-F)
  - Run /dv-testplan or S2 in the DV end-to-end flow

  Trigger on: "generate testplan", "create testplan", "dv-testplan", "/dv-testplan",
  "testplan from spec", "write testplan", "S2", "map features to tests",
  "create coverage plan", "define checkers for", "testplan excel"
---

# DV Testplan Generator — S2

You are acting as a senior DV architect with 20+ years of experience generating
verification testplans. Your output is a professional Excel workbook used by the
entire DV team throughout the project lifecycle. Completeness, correctness, and
downstream compatibility (S3/S4/S5 skills) are critical.

---

## Step 0 — Check Environment (ALWAYS run first)

**This step is mandatory before any other work.**

Locate the common scripts directory relative to this skill:
- This skill lives at: `skills/dv-testplan/`
- Common scripts are at: `skills/common/scripts/`

Run the environment check immediately:
```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s2 --install
```

This checks that `openpyxl` is installed (required for Excel generation) and
auto-installs it if missing.

**If Bash is not available in this session:**
- Inform the user upfront: *"Note: Bash is not available. I will prepare the
  testplan data and write the Excel using a fallback method. For best results,
  please ensure Bash permission is granted."*
- Continue with all steps — use the Write tool to save the testplan data JSON,
  then use Python via Bash only for the final Excel generation step.
- If Bash remains unavailable at Step 7, provide the exact command for the user
  to run manually and save the data JSON so nothing is lost.

**Common scripts location for this skill:**
```
<REPO_ROOT>/skills/common/scripts/
  ├── check_environment.py      # dependency checker (run in Step 0)
  ├── generate_testplan_excel.py  # Excel generator (run in Step 7)
  └── write_spec_summary.py     # S1 output writer (used by dv-spec-parse)
```

---

## Step 1 — Gather Inputs

Check the conversation and confirm all required inputs. Ask for missing ones in a
**single message** — never one at a time.

| Input | Description | If Missing |
|---|---|---|
| `SPEC_SOURCE` | Either path to `dv_spec_summary.json` (S1 output) OR path to raw spec file (PDF/DOCX/TXT/MD) | Ask: *"Please provide either the dv_spec_summary.json from S1 or your raw spec file path."* |
| `PROJECT_NAME` | Block/IP name (e.g. `apb_uart`) | Ask user |
| `IP_NAME` | Short uppercase IP tag for checker IDs (e.g. `UART`, `DMA`) | Derive from PROJECT_NAME if obvious, else ask |
| `OUTPUT_DIR` | Where to save testplan.xlsx | Default to spec file's directory; confirm with user |

---

## Step 2 — Parse Spec Data

**If `dv_spec_summary.json` provided:**
- Read and parse it directly. Extract: features, sub-features, interfaces, parameters,
  clock domains, operating modes, compliance standards, known constraints.
- **Also extract these fields added by the updated S1:**
  - `register_map` — array of registers with per-field detail (name, offset, reset_value,
    fields[].name/bits/width/access/reset_value). Used in Step 3 to **auto-generate
    register access test rows** without manual input.
  - `proprietary_interfaces` — array of non-standard protocol interfaces with signal list,
    protocol phases, timing, and handshake description. Used in Step 4 to generate
    protocol-specific coverpoints with **actual signal names** from the spec.
  - If either field is absent or empty in the JSON, proceed without it (no error).

**If raw spec file provided:**
- Read the spec file. Extract the same fields using the same logic as dv-spec-parse (S1).
- Internally build a feature/sub-feature/interface structure before proceeding.
- Inform the user: *"Parsed spec directly (no S1 JSON provided). For best results,
  consider running /dv-spec-parse first."*

---

## Step 3 — Determine Verification Types

For each sub-feature, decide its primary verification approach using these rules:

### Directed Test criteria (most likely no coverage)
- Feature has a fixed sequence of steps hard to generate randomly
- Register/CSR access (read/write/reset value check)
- Reset sequence, power-up/down, clock switching
- Interrupt enable/disable/clear sequences
- Error injection with known trigger condition

### Random Test criteria (coverage-driven, name ends `_rand_test`)
- Feature has multiple enumerable values (command type, burst length, data width)
- Protocol fields that combine in many ways
- FIFO fill levels, arbitration scenarios
- Any feature where corner cases emerge from random stimulus

### Coverpoint-only rows
- Protocol state machine states and transitions (FSM coverage)
- Toggle coverage of key control signals
- Cross coverage rows (generated in Step 4)
- **Proprietary protocol coverpoints**: if `proprietary_interfaces` is present in S1 JSON,
  generate coverpoints using the **actual signal names** from the `signals[]` array.
  Example: if a proprietary interface has signal `req_type[2:0]`, generate
  `cp_req_type: coverpoint req_type { bins type_a = {3'b001}; ... }` rather than a
  generic placeholder.

### Negative / Error Injection rows (separate rows, linked to parent)
- Protocol violations
- Illegal register values
- Reset during active operation
- Buffer overflow / underflow
- Timeout conditions

### Auto-generate Register Access Rows (from register_map)

**If `register_map` is present and non-empty in S1 JSON**, auto-generate the following
testplan rows for each register — do NOT wait for user input, just generate them:

| Row type | Test name format | When | Milestone |
|---|---|---|---|
| Reset value check | `<reg_name>_reset_test` | Always | DV-I |
| Read-write | `<reg_name>_rw_test` | Register has ≥1 RW or WO field | DV-I |
| W1C clear | `<reg_name>_w1c_test` | Register has ≥1 W1C field | DV-I |
| RO protection | `<reg_name>_ro_protect_test` | Register has ≥1 RO field | DV-I |

- **Checker ID format:** `CHK_<IP>_<REG_NAME>_REGISTER_<NNN>` (e.g. `CHK_UART_CTRL_REGISTER_001`)
- **Checker type:** `Procedural` (UVM RAL `read()`/`write()` + mirror comparison)
- **Component:** `scoreboard` (via RAL predictor)
- **Verification type cell content:**
  ```
  Testcase(Directed): <reg_name>_reset_test
  Checker: CHK_<IP>_<REG_NAME>_REGISTER_<NNN>
  ```
- **Do not duplicate** register rows if the feature list already mentions the register.
  Merge if a feature row already covers the same register and test type.

### Corner / Stress test rows (dedicated rows)
- Boundary values (min/max burst, 0-length, max-length transfer)
- Back-to-back transactions with no gap
- Simultaneous multi-interface activity
- Maximum frequency / minimum timing margin

---

## Step 4 — Interactive Cross Coverage

**This step MUST be interactive.** Do not skip or auto-decide.

1. Analyse all extracted features and identify candidate cross coverages.
   Good cross coverage candidates:
   - Two features that can independently take multiple values and whose interaction
     is architecturally significant (e.g. `cmd_type × burst_len`, `data_width × parity`)
   - Protocol fields that the spec says must work in combination

2. Print the following to the terminal:

```
============================================================
  Cross Coverage Recommendations for <PROJECT_NAME>
============================================================
  Recommended crosses (based on spec analysis):

  [1] <coverpoint_A> × <coverpoint_B>
      Rationale: <why this combination matters>
      Bins estimate: <N> (⚠️ WARNING if > 64)

  [2] <coverpoint_A> × <coverpoint_C>
      Rationale: ...
      Bins estimate: <N>

  ... (list all candidates)

------------------------------------------------------------
  Enter numbers to INCLUDE (e.g. 1,3): ___
  Type NEW to define a custom cross not listed above.
  Type SKIP to skip all cross coverage.
============================================================
```

3. Wait for user input. Parse the response:
   - Numbers → include those crosses as coverpoint rows in the testplan
   - `NEW` → ask user: *"Describe the cross coverage you want (signal names and why)."*
     Then generate the SV code for it.
   - `SKIP` → no cross coverage rows added

4. **Combinatorial explosion warning:** If any recommended cross has > 64 bins,
   print the warning and suggest `binsof` filters or `ignore_bins` for illegal
   combinations. Include the filtered version in the generated SV code.

---

## Step 5 — Generate Testplan Rows

For each sub-feature (plus negative, stress, corner, cross-coverage rows), generate
a testplan row with all 11 columns:

### Column Rules

**Col 1 — Feature:** Top-level feature name from spec.

**Col 2 — Sub-feature:** Sub-feature name. For negative/stress/corner rows, prefix
with `[NEG]`, `[STRESS]`, or `[CORNER]`.

**Col 3 — Brief Description:** 1–2 sentence description.

**Col 4 — Verification Type:** Use this format in the cell (newline-separated):
```
Testcase(Directed): <test_name>
Testcase(Random): <test_name>_rand_test
Coverpoint: <covergroup_name>
Checker: <CHK_ID>
```
Include only the applicable lines. Directed tests typically do NOT have a Coverpoint line.

**Col 5 — Testcase Description:** Structured as:
```
DUT Config: <register settings, parameters, mode>
Stimulus: <step-by-step stimulus generation>
Expected Behavior: <what the DUT should do>
Checks: <what is verified>
Pass Criteria: <explicit pass/fail condition>
Notes: <edge cases, dependencies>
```

**Col 6 — Coverpoint Description:** Only for random tests and coverpoint rows.
Write actual syntactically correct SystemVerilog code:
```systemverilog
// Covergroup: <covergroup_name>
covergroup <covergroup_name> @(posedge clk);
  cp_<signal>: coverpoint <signal> {
    bins <bin_name> = {<value>};
    ...
  }
  // Cross (if applicable):
  cx_<a>_x_<b>: cross cp_<a>, cp_<b>;
endgroup
```
For directed tests: leave blank.

**Col 7 — Checker ID:** Format: `CHK_<IP>_<FEATURE>_<TYPE>_<NNN>`
- `<IP>`: uppercase IP name (e.g. `UART`, `DMA`)
- `<FEATURE>`: short feature tag (e.g. `TX`, `RX`, `APB`, `BAUD`)
- `<TYPE>`: one of `PROTOCOL`, `DATA_INTEGRITY`, `ERROR_HANDLING`, `TIMING`, `FUNCTIONAL`, `COVERAGE`
- `<NNN>`: 3-digit sequence number, unique across entire testplan

**Col 8 — Checker Type:** `Procedural` / `Assertion` / `Both`
- Protocol timing checks → prefer `Assertion`
- Data comparison checks → `Procedural`
- Both a scoreboard check AND an SVA → `Both`

**Col 9 — Assertion Code:** Populate only when Col 8 = `Assertion` or `Both`.
Write syntactically correct SVA:
```systemverilog
// <assertion description>
property p_<name>;
  @(posedge clk) disable iff (!rst_n)
  <antecedent> |-> <consequent>;
endproperty
assert property (p_<name>) else
  $error("[%s] CHK_ID violated at time %0t", "<CHK_ID>", $time);
```

**Col 10 — Milestone:**
- `DV-I`: Reset/clock/basic register R/W, block-level sanity smoke tests
- `DV-C`: All directed tests, random test infrastructure, protocol compliance,
  interrupt tests, basic error handling
- `DV-F`: All corner cases, stress tests, negative/error injection,
  cross-coverage-driven tests, performance tests

**Col 11 — Parent Feature:** Leave blank for normal rows.
For `[NEG]`, `[STRESS]`, `[CORNER]` rows: fill with the Feature + Sub-feature
of the parent row they are derived from.

---

## Step 6 — Generate Summary Sheet (Sheet 1)

Sheet 1 named `Summary`. Include:

```
DV Testplan Summary — <PROJECT_NAME>
Generated by: dv-testplan (S2)    Date: <date>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL TESTS           : N
  Directed            : N
  Random              : N
  Coverpoint-only     : N
  Negative/Error      : N
  Corner/Stress       : N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MILESTONE BREAKDOWN
  DV-I  : N tests
  DV-C  : N tests
  DV-F  : N tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COVERAGE
  Covergroups         : N
  Coverpoints         : N
  Cross Coverpoints   : N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHECKERS
  Total Checkers      : N
  Procedural          : N
  Assertion           : N
  Both                : N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURES COVERED      : N / N (total from spec)
```

---

## Step 7 — Build Excel File via Common Script

Write all testplan rows to `/tmp/<project>_testplan_data.json` with this structure:
```json
{
  "total_features_in_spec": <N>,
  "rows": [
    {
      "feature":              "APB Slave Interface",
      "subfeature":           "Register Write",
      "brief_description":    "...",
      "verification_type":    "Testcase(Directed): apb_reg_write_test\nChecker: CHK_UART_APB_PROTOCOL_001",
      "testcase_description": "DUT Config: ...\nStimulus: ...\nExpected Behavior: ...\nChecks: ...\nPass Criteria: ...",
      "coverpoint_desc":      "",
      "covergroup":           "",
      "checker_id":           "CHK_UART_APB_PROTOCOL_001",
      "checker_type":         "Assertion",
      "assertion_code":       "property p_apb_no_wait;\n  ...\nendproperty\nassert property(...)",
      "milestone":            "DV-I",
      "parent_feature":       ""
    }
  ]
}
```

Then run the shared Excel generation script from the common scripts directory:

```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_testplan_excel.py \
  --data    /tmp/<project>_testplan_data.json \
  --output  <OUTPUT_DIR>/testplan.xlsx \
  --project <PROJECT_NAME>
```

**If Bash is unavailable:** Tell the user:
> "The testplan data has been saved to `/tmp/<project>_testplan_data.json`.
> Please run the following command to generate the Excel file:
> ```
> python3 <REPO_ROOT>/skills/common/scripts/generate_testplan_excel.py \
>   --data /tmp/<project>_testplan_data.json \
>   --output <OUTPUT_DIR>/testplan.xlsx \
>   --project <PROJECT_NAME>
> ```"

---

## Step 8 — Print Terminal Summary

```
============================================================
  DV Testplan — Complete
  Project  : <PROJECT_NAME>
  Output   : <OUTPUT_DIR>/testplan.xlsx
------------------------------------------------------------
  Total rows     : N
  Directed tests : N
  Random tests   : N  (coverage-driven)
  Neg/Stress/Corner: N
  Covergroups    : N
  Checkers       : N  (Procedural: N | Assertion: N | Both: N)
------------------------------------------------------------
  Milestone: DV-I=N  DV-C=N  DV-F=N
------------------------------------------------------------
  ⚠️  Items needing review: N
  Output: <OUTPUT_DIR>/testplan.xlsx
------------------------------------------------------------
  Next step: run /dv-verif-plan to generate Verification Plan
============================================================
```

---

## Important Notes

- Every sub-feature from the spec must appear as at least one testplan row
- Do not invent features not in the spec; do flag gaps with `⚠️ NEEDS_REVIEW`
- Checker IDs must be globally unique across the entire testplan (no duplicates)
- SV code in cols 6 and 9 must be syntactically correct — think carefully before writing
- Random tests must have coverage (col 6 populated); directed tests typically do not
- The `_rand_test` suffix on random test names is mandatory
- Cross coverage rows are standalone rows with col 4 = `Coverpoint: <cg_name>` only
- FSM transition coverpoints must be generated if the spec implies state machines
- Negative test rows must have col 11 (Parent Feature) populated
