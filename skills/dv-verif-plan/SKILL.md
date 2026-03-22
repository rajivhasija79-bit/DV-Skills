---
name: dv-verif-plan
description: >
  Generates a complete, professional DV Verification Plan PDF document for a hardware IP block.
  Use this skill whenever the user wants to create a verification plan, DV plan, VP document, or
  signoff plan for a hardware block or IP. Triggers on: "create verification plan", "generate DV plan",
  "write verif plan", "create VP document", "DV planning document", "signoff plan", or any request
  to document the verification strategy for an IP/DUT. Accepts S1 spec summary JSON and/or S2 testplan
  Excel as inputs, or a raw spec file. Produces a polished PDF with embedded PNG block diagrams
  (TB architecture, DUT diagram, Gantt schedule), interactive Q&A for all sections, and a
  machine-readable JSON for downstream DV skills (S4 onward). Always use this skill for verif plan
  creation — do NOT attempt to generate a verification plan without it.
---

# S3 — DV Verification Plan Generator

## What this skill produces

A multi-section professional PDF verification plan document with:
- Embedded PNG diagrams (TB architecture, DUT block diagram, Gantt schedule)
- Full coverage plan (covergroups, coverpoints, cross, illegal bins)
- Checker plan with component assignments
- Traceability matrix linking spec features → tests → checkers → coverage
- Interactive Q&A for all missing information — never assume, always ask

**Outputs:**
| File | Description |
|------|-------------|
| `dv_verif_plan.pdf` | Final professional PDF document |
| `dv_verif_plan_data.json` | Structured data (consumed by S4+) |
| `tb_architecture.png` | TB hierarchy block diagram (Graphviz) |
| `dut_block_diagram.png` | DUT internal block diagram (Graphviz) |
| `gantt_schedule.png` | Milestone Gantt chart (Matplotlib) |

---

## Step 0 — Environment Check (ALWAYS run first)

Before doing anything else, check whether Bash is available and run the environment checker.

**If Bash is available:**
```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s3 --install
```

**If Bash is NOT available** (tool denied/unavailable):
- Notify the user: "Bash is not available in this session. The skill will collect all data interactively and write output files directly. To generate PNG diagrams and PDF, you will need to run the generation scripts manually after this session."
- Continue with data collection steps — all data will be saved to `/tmp/<PROJECT>_verif_plan_data.json` for manual processing.

---

## Step 1 — Gather and Confirm Inputs

### 1a. Look for existing inputs (do NOT use without asking)

Search for these files in the working directory and common locations before asking the user:
- `dv_spec_summary.json` — S1 output (preferred spec input)
  - **Check for these updated S1 fields** (added in S1 v1.1):
    - `register_map[]` — per-register detail with per-field access types; used in
      Section 3 (Coverage) and Section 4 (Checker Plan)
    - `proprietary_interfaces[]` — non-standard protocol signal list + timing;
      used in Section 5 (TB Architecture) to describe custom VIPs
  - If these fields are absent, the skill proceeds without them (no error)
- `dv_spec_summary.md` — S1 markdown output
- `testplan.xlsx` or `*testplan*.xlsx` — S2 output
- Any `*.pdf`, `*.docx`, `*.txt`, `*.md` that look like a spec or design document
- Any `*coding_guide*`, `*dv_guidelines*`, `*checklist*` files

**For each file found**, ask the user:
> "I found `<filename>`. Should I use this as [spec/testplan/coding guidelines]? (yes/no)"

Never use a found file without explicit user confirmation.

### 1b. Ask for inputs not found

If `dv_spec_summary.json` (S1 output) is not found or user declines:
> "Please provide the spec file path, or paste the spec content directly. I can parse: PDF, DOCX, TXT, Markdown, or plain text."

If S2 testplan is not found or user declines:
> "Do you have a testplan Excel file from the previous step? If yes, provide the path. If no, I'll build the coverage and checker sections from the spec directly."

Ask once at the start:
> "Are there any other resources I should be aware of? For example:
> - Coding guidelines document
> - DV methodology doc
> - Previous verification plan from a similar IP
> - Existing TB or UVM environment code
> (Provide file paths or URLs, or press Enter to skip)"

### 1c. Confirm PROJECT_NAME and OUTPUT_DIR

```
Project/IP name: ____________
Output directory for all generated files: ____________  (default: ./dv_verif_plan_out/)
```

Set:
- `PROJECT_NAME` = user-provided name (e.g., "APB_UART", "AXI_DMA")
- `OUTPUT_DIR` = resolved absolute path to output directory
- `REPO_ROOT` = path to the DV-Skills repo root (parent of `skills/`)

Create OUTPUT_DIR if it does not exist.

---

## Step 2 — DUT Description (Section 1)

Pull from `dv_spec_summary.json` if available. Use these fields:
- `block_overview`, `features`, `interfaces`, `clock_domains`, `reset_strategy` — as before
- `register_map[]` — use for "Register Map Summary" sub-section: list all registers with
  offset, reset value, and field count. Show total register count and flag any W1C/RO fields.
- `proprietary_interfaces[]` — list any non-standard interfaces separately with their
  protocol phase descriptions (prose from S1). This informs the VIP design in Section 5.

If spec JSON is not available, extract from raw spec:
- Full name and version of the DUT
- List of supported protocols/interfaces
- Key features and modes of operation
- Register map summary (count + key registers)
- Clock domains and reset scheme
- Parameterization (configurable options)
- Known limitations or exclusions from verification scope

Ask the user to confirm or augment:
> "Here is the DUT description I extracted. Does this look complete? Is there anything I should add or correct?"

Store as `data["dut"]` in the plan data.

---

## Step 3 — Testplan Summary (Section 2)

If S2 testplan Excel is available (and user confirmed use):
- Extract: test names, checker IDs, verification types, milestones, feature coverage
- Summarize: total test count by type (DV-I/DV-C/DV-F/NEG/STRESS/CORNER), total checker count

If no testplan is available:
- Derive a preliminary test list from spec features (one row per feature × type)
- Mark all tests as `PRELIMINARY` and note: "Testplan not yet generated — run S2 dv-testplan skill to produce final testplan"

Tell the user:
> "Section 2 (Testplan) will embed a summary table showing test counts by milestone and type. The full testplan is in the attached Excel. Should I embed the full test list or just the summary? (full / summary-only)"

Store as `data["testplan_summary"]`.

---

## Step 4 — Coverage Plan (Section 3)

This section EXPANDS on the coverpoints from the testplan into a full coverage specification.

For each feature from the spec (or from S2 testplan covergroups):

### 4a. Derive covergroups

For each functional feature, create a covergroup entry:
```
covergroup cg_<feature_name> @(posedge clk);
  cp_<point>: coverpoint <signal_name> {
    bins <bin_name> = {<values>};
    illegal_bins <illegal> = {<illegal_values>};
  }
  cross cp_<a>, cp_<b>;
endgroup
```

If S2 testplan is available, pull coverpoints from the `Coverpoint / Assertion Code` column and expand them.

**If `register_map` is available from S1 JSON**, auto-generate register-level covergroups:

```systemverilog
// Register access coverage — auto-generated from register_map
covergroup cg_reg_access @(posedge clk);
  cp_reg_addr: coverpoint reg_addr {
    // one bin per register offset
    bins <REG_NAME> = {<OFFSET>};
    // ... one per register
  }
  cp_reg_op: coverpoint reg_write { bins write = {1}; bins read = {0}; }
  cx_reg_op: cross cp_reg_addr, cp_reg_op;  // every register exercised as both R and W
endgroup

// W1C field coverage — one covergroup per register containing W1C fields
// covergroup cg_<REG_NAME>_w1c @(posedge clk);
//   cp_<FIELD>_set:   coverpoint <FIELD> { bins set = {1}; bins clear = {0}; }
// endgroup
```

Add one register access covergroup entry per register block. Tag with `DV-I` milestone.

### 4b. Coverage targets per milestone

Ask the user to confirm or modify:
> "I recommend the following functional coverage targets. Please confirm or adjust:
> - DV-I: 70% functional coverage (initial integration)
> - DV-C: 90% functional coverage (RTL coding complete)
> - DV-F: 100% functional coverage (final RTL)
> Adjust any target? (Enter to accept)"

### 4c. Coverage categories

Ask:
> "Which coverage categories should be included in the signoff criteria?
> (Suggested defaults — confirm or adjust):
> - [ x ] Functional coverage (covergroups)
> - [ x ] Line coverage
> - [ x ] Branch coverage
> - [ x ] Toggle coverage
> - [ x ] FSM state/transition coverage
> - [ ] Expression coverage (optional)
> Any modifications?"

Store as `data["coverage_plan"]`.

---

## Step 5 — Checker Plan (Section 4)

Pull all checker IDs from the S2 testplan (column: `Checker ID`, `Checker Type`, `Assertion Code` if available).

**If `register_map` is available from S1 JSON** and no S2 testplan exists (or S2 testplan
does not include register checkers), auto-populate register checkers:

| Checker ID pattern | Description | Component | When generated |
|---|---|---|---|
| `CHK_<IP>_<REG>_REGISTER_RST` | Reset value correct at power-up | scoreboard (RAL) | Always |
| `CHK_<IP>_<REG>_REGISTER_RW` | Write-readback matches | scoreboard (RAL) | If RW/WO fields exist |
| `CHK_<IP>_<REG>_REGISTER_W1C` | W1C field clears correctly | scoreboard (RAL) | If W1C field exists |
| `CHK_<IP>_<REG>_REGISTER_RO` | RO field not writable | scoreboard (RAL) | If RO field exists |

Generate one row per register per applicable access type. Do not duplicate checkers
already present in S2 testplan.

For each checker:

```
| Checker ID | Description | Type | Component | Assertion Code Snippet |
```

**Component options:**
| Component | Description | When to use |
|-----------|-------------|-------------|
| `scoreboard` | Reference model comparison, data integrity | Most functional checks |
| `testcase` | Simple pass/fail checks in test body | One-off or test-specific checks |
| `interface` | SVA assertions, protocol compliance | Timing, protocol rules, glitch checks |
| `coverage` | Illegal bins acting as implicit checks | Unreachable states, illegal combos |
| `monitor` | Passive protocol observers | Bus snooping, ordering checks |

For each checker, ask:
> "Checker `<CHK_ID>`: `<description>`
> Recommended component: `<auto-recommendation>`
> Confirm or override? (scoreboard / testcase / interface / coverage / monitor)"

Auto-recommendation rules:
- Type=`ASSERTION` → interface
- Type=`PROTOCOL` → monitor or interface
- Type=`DATA_INTEGRITY` → scoreboard
- Type=`FUNCTIONAL` → scoreboard
- Type=`CORNER_CASE` → testcase

Group checkers by component in the document for clarity.

Store as `data["checker_plan"]`.

---

## Step 6 — TB Architecture (Section 5)

### 6a. Component inventory

**If `proprietary_interfaces` is available from S1 JSON**, add a sub-section before the
component inventory describing each custom VIP:

> "The spec defines **<N> proprietary interface(s)** that require custom VIP development:
>
> **`<if_name>`** — `<description from S1>`
> - Signals: `<signal_list from S1 proprietary_interfaces[].signals>`
> - Protocol phases: `<phases from S1>`
> - Handshake: `<handshake from S1>`
> - Clock: `<clock from S1>`
>
> For each proprietary VIP, the TB Architecture section will describe:
> the custom driver state machine, monitor sampling strategy, and any
> protocol-specific sequence items needed."

Ask the user:
> "For the TB architecture diagram, I need the complete list of DV components.
> Based on the spec, I suggest the following UVM testbench components — confirm or modify:
>
> **Top-level:**
> - `tb_top` — DUT instantiation + clock/reset generation
> - `dv_env` — UVM environment
>
> **Per interface agent (one set per protocol interface):**
> - `<if_name>_agent` — UVM agent (active/passive)
> - `<if_name>_sequencer` — Sequence execution
> - `<if_name>_driver` — Drives DUT pins
> - `<if_name>_monitor` — Observes bus transactions
>
> **Shared infrastructure:**
> - `scoreboard` — Reference model + checkers
> - `coverage_collector` — Functional coverage sampling
> - `reg_model` — UVM RAL register model
> - `virtual_sequencer` — Coordinates multi-agent sequences
>
> Add/remove any components? Provide additional agents if DUT has multiple interfaces."

### 6b. Generate TB architecture PNG

After confirming components, run:
```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_tb_diagram.py \
  --data /tmp/<PROJECT>_verif_plan_data.json \
  --output <OUTPUT_DIR> \
  --project <PROJECT_NAME>
```

This produces:
- `<OUTPUT_DIR>/tb_architecture.png` — UVM hierarchy block diagram
- `<OUTPUT_DIR>/dut_block_diagram.png` — DUT internal structure (if interfaces list is available)

If Bash is unavailable, save component list to JSON and provide manual command.

### 6c. Ask for DUT internal diagram detail

> "For the DUT block diagram, should I show:
> (A) Interface ports only (simpler, suitable for black-box DV)
> (B) Internal sub-blocks from the spec (more detailed)
> Which do you prefer?"

Store as `data["tb_architecture"]`.

---

## Step 7 — Compilation & Simulation Flow (Section 6)

Ask these questions to populate this section:

```
Q1: Which simulator are you using? (VCS / Xcelium / Questa / Riviera / ModelSim / other)
Q2: What is the full compile command? (or describe the Makefile targets if using Make)
Q3: What is the simulation run command? (include any +UVM_TESTNAME, +SEED, or other plusargs)
Q4: How do you open the waveform? (DVE / Verdi / GTKWave / other) — provide the open command
Q5: How do you analyze coverage? (URG / IMC / Incisive / other) — provide the merge + report command
Q6: Are there any standard +define+ options users should know about?
    (e.g., +define+DEBUG, +define+GATE_SIM, etc.)
Q7: Are there any standard +UVM_VERBOSITY or +UVM_CONFIG options?
Q8: How do you run a full regression? (LSF/bsub, make regression, custom script?)
Q9: Where is the log file written? How do you spot a pass/fail quickly?
```

Format this section as a step-by-step how-to with numbered steps and code blocks.

Store as `data["compilation_flow"]`.

---

## Step 8 — Directory Structure (Section 7)

Ask:
> "What is the top-level DV directory structure? I can generate a standard UVM layout:
>
> ```
> <ip_name>_dv/
> ├── tb/              # Testbench files (env, agents, sequences)
> ├── tests/           # Test files
> ├── sim/             # Simulation run directory
> ├── scripts/         # Compile/run scripts, Makefile
> ├── cov/             # Coverage reports
> ├── waves/           # Waveform databases
> ├── docs/            # Verification plan, testplan docs
> └── rtl_ref/         # RTL reference (read-only link)
> ```
>
> Is this the correct structure for your project? Provide the actual directory tree or confirm this template."

Store as `data["directory_structure"]`.

---

## Step 9 — DV Resources (Section 8)

Ask the user to provide each of these (required for the document):

```
1. Verification Plan URL/path (this document once finalized): ___________
2. Testplan document URL/path: ___________
3. DV Git repo URL: ___________
4. RTL Git repo URL: ___________
5. JIRA/bug tracking project URL or key: ___________
6. Confluence/wiki page URL: ___________
7. Simulator license server: ___________
8. Any other relevant links (add as many as needed): ___________
```

For any the user cannot provide, insert placeholder `<TBD — INSERT LINK>`.

Store as `data["dv_resources"]`.

---

## Step 10 — Debug Guidelines (Section 9)

This section is **interactive** — recommend industry-standard debug practices and ask the user to confirm, add, or remove.

Present the following recommended guidelines and ask for feedback:

**Recommended Debug Workflow:**
1. Check simulation log for first UVM_ERROR or UVM_FATAL — `grep -n "UVM_ERROR\|UVM_FATAL" sim.log`
2. Open waveform and navigate to the timestep of the first error
3. Check scoreboard mismatches: compare `exp_pkt` vs `act_pkt` in scoreboard log
4. Enable verbose logging: `+UVM_VERBOSITY=UVM_HIGH` and re-run
5. Use `+UVM_MAX_QUIT_COUNT=1` to stop at first error
6. Check register model: run `uvm_reg_block::check_mirror_values()` if register access errors
7. Isolate the failing test with a fixed seed: `+ntb_random_seed=<SEED>`

Ask:
> "I've drafted the above debug guidelines. Would you like to:
> (A) Accept as-is
> (B) Add project-specific debug tips (e.g., specific signals to watch, known false-positive errors, simulator-specific flags)
> (C) Both — accept defaults and add more
>
> If B or C, please provide your additional debug tips:"

Store as `data["debug_guidelines"]`.

---

## Step 11 — Sign-off Criteria (Section 10)

Present recommended defaults and ask for confirmation:

> "I recommend the following DV sign-off criteria — please confirm or adjust each:
>
> **Coverage:**
> - Functional coverage: 100% (all covergroups at 100%)
> - Line coverage: 100%
> - Branch coverage: 100%
> - Toggle coverage: 100% (excluding output-only/unused signals)
> - FSM coverage: 100% (all reachable states and transitions)
>
> **Testplan:**
> - 100% of planned tests passing
> - Zero tests in SKIP/BLOCKED state at DV-F
>
> **Bug Quality:**
> - Zero open P1/P2 JIRAs at DV-F
> - Zero open P3 JIRAs that are DV-blocking
>
> **Waivers:**
> - All coverage waivers documented and reviewed by design owner
>
> Adjust any criteria? (Enter to accept all)"

Store as `data["signoff_criteria"]`.

---

## Step 12 — Schedule (Section 11)

Ask for milestone dates:

```
DV-I (Initial — RTL with register access ready):
  Planned start date: ___________
  Planned completion date: ___________
  Key deliverables at DV-I:
    - [ ] TB compiles and basic sanity passes
    - [ ] Register access test passes (all registers R/W)
    - [ ] Testplan reviewed and approved
    - [ ] Any others? ___________

DV-C (Coding Complete — full RTL feature-complete):
  Planned start date: ___________
  Planned completion date: ___________
  Key deliverables at DV-C:
    - [ ] All directed tests passing
    - [ ] Regression pass rate ≥ 95%
    - [ ] Functional coverage ≥ 90%
    - [ ] Any others? ___________

DV-F (Final — signed-off on final RTL):
  Planned start date: ___________
  Planned completion date: ___________
  Key deliverables at DV-F:
    - [ ] 100% testplan passing
    - [ ] 100% code + functional coverage
    - [ ] Zero open blocking bugs
    - [ ] Verification plan signed off
    - [ ] Any others? ___________
```

After collecting dates, generate Gantt chart PNG:
```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_gantt_chart.py \
  --data /tmp/<PROJECT>_verif_plan_data.json \
  --output <OUTPUT_DIR> \
  --project <PROJECT_NAME>
```

Store as `data["schedule"]`.

---

## Step 13 — Team Info & Roles (Section 12)

Ask the user to provide team information:

```
DV Lead:          Name: ___________  Email: ___________
DV Engineers:     (add as many as needed)
  - Name: ___________  Email: ___________  Responsibility: ___________
Design Owner:     Name: ___________  Email: ___________
RTL Owner:        Name: ___________  Email: ___________
Verification Mgr: Name: ___________  Email: ___________
Project Manager:  Name: ___________  Email: ___________
```

For each DV Engineer, ask:
> "What is `<name>`'s primary responsibility area? (e.g., TB infrastructure, specific agent, regression, coverage closure)"

Insert placeholders `<TBD>` for any fields the user skips.

Store as `data["team_info"]`.

---

## Step 14 — Assumptions, Risks & Mitigation (Section 13)

### Assumptions

Present recommended assumptions and ask for additions/removals:
1. RTL is delivered per the agreed milestone schedule
2. DV environment uses UVM 1.2 or later
3. Simulator version is `<ask user>` or later
4. Register model is generated from IP-XACT or equivalent
5. Formal verification is out of scope (DV only)

Ask: "Are these assumptions correct? Any to add or remove?"

### Risks & Mitigation

Present recommended risks:

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| RTL delivery slippage | Medium | High | TB development proceeds against golden model; schedule floats with RTL |
| Coverage closure difficulty | Medium | High | Start coverage analysis at DV-I; waiver process in place |
| Simulator license shortage | Low | Medium | Reserve licenses early; stagger regression runs |
| Protocol spec ambiguity | Medium | High | Raise spec questions early; DV team owns RTL vs spec discrepancy tracking |

Ask: "Any project-specific risks to add? Any of these to remove?"

Store as `data["risks"]`.

---

## Step 15 — Collateral List (Section 14)

### Receivables (what DV team needs to receive)

Present recommended list and ask for additions:
1. RTL source files + integration guide
2. Architectural specification (final version)
3. Register specification (IP-XACT or Excel)
4. Interface timing diagrams / waveforms
5. Any existing UVM agents for the interfaces used
6. Power intent (UPF/CPF) if power-aware verification is in scope

### Deliverables (what DV team will deliver)

Present recommended list and ask for additions:
1. Verification Plan (this document)
2. Testplan (S2 output — Excel)
3. UVM Testbench (TB source code)
4. Simulation regression scripts
5. Coverage database and closure report
6. Bug report (exported from JIRA)
7. Verification sign-off report

Ask: "Are these lists complete? Any items to add or remove from either list?"

Store as `data["collateral"]`.

---

## Step 16 — Traceability Matrix

Build a traceability table linking every spec feature to its verification artifacts.

For each feature in the spec:

```
| Feature | Spec Section | Checker ID(s) | Test Name(s) | Coverage Bin | Status |
```

**Status logic** (auto-derived if S2 testplan is available):
- `COVERED` — has ≥1 test + ≥1 checker + ≥1 coverage bin
- `PARTIAL` — has test but missing checker or coverage
- `NOT_COVERED` — no test, no checker, no coverage
- `WAIVED` — explicitly excluded from scope

Flag any `NOT_COVERED` or `PARTIAL` features with ⚠️ and ask:
> "Feature `<name>` appears NOT_COVERED. Should I:
> (A) Add a placeholder test/checker row
> (B) Mark as WAIVED with a reason
> (C) Leave as NOT_COVERED (to be addressed later)"

Store as `data["traceability_matrix"]`.

---

## Step 17 — Assemble Data JSON

Write all collected data to `/tmp/<PROJECT>_verif_plan_data.json`:

```json
{
  "project": "<PROJECT_NAME>",
  "generated_at": "<ISO timestamp>",
  "dut": { ... },
  "testplan_summary": { ... },
  "coverage_plan": [ ... ],
  "checker_plan": [ ... ],
  "tb_architecture": { ... },
  "compilation_flow": { ... },
  "directory_structure": "...",
  "dv_resources": { ... },
  "debug_guidelines": [ ... ],
  "signoff_criteria": { ... },
  "schedule": { ... },
  "team_info": { ... },
  "risks": [ ... ],
  "collateral": { ... },
  "traceability_matrix": [ ... ]
}
```

---

## Step 18 — Generate PDF

Run the PDF generator:

```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_verif_plan_pdf.py \
  --data /tmp/<PROJECT>_verif_plan_data.json \
  --output <OUTPUT_DIR> \
  --project <PROJECT_NAME> \
  --tb-diagram <OUTPUT_DIR>/tb_architecture.png \
  --dut-diagram <OUTPUT_DIR>/dut_block_diagram.png \
  --gantt <OUTPUT_DIR>/gantt_schedule.png
```

The script tries PDF engines in order:
1. **Pandoc** (+ LaTeX) — best typography
2. **WeasyPrint** — best layout fidelity, no LaTeX needed
3. **ReportLab** — pure Python fallback

Confirm output:
> "Verification plan generated successfully:
> - PDF: `<OUTPUT_DIR>/dv_verif_plan.pdf`
> - Data: `<OUTPUT_DIR>/dv_verif_plan_data.json`
> - Diagrams: `tb_architecture.png`, `dut_block_diagram.png`, `gantt_schedule.png`
>
> Would you like to review any section and make changes? (yes/no)"

If user says yes — ask which section and loop back to the relevant step.

---

## Fallback: If Bash is unavailable throughout

1. Complete all interactive Q&A steps (Steps 2–16)
2. Write the complete JSON to `/tmp/<PROJECT>_verif_plan_data.json` using the Write tool
3. Tell the user:
   > "All data collected. To generate diagrams and PDF, run these commands in your terminal:
   > ```bash
   > cd <REPO_ROOT>
   > python3 skills/common/scripts/generate_tb_diagram.py --data /tmp/<PROJECT>_verif_plan_data.json --output <OUTPUT_DIR> --project <PROJECT_NAME>
   > python3 skills/common/scripts/generate_gantt_chart.py --data /tmp/<PROJECT>_verif_plan_data.json --output <OUTPUT_DIR> --project <PROJECT_NAME>
   > python3 skills/common/scripts/generate_verif_plan_pdf.py --data /tmp/<PROJECT>_verif_plan_data.json --output <OUTPUT_DIR> --project <PROJECT_NAME> --tb-diagram <OUTPUT_DIR>/tb_architecture.png --dut-diagram <OUTPUT_DIR>/dut_block_diagram.png --gantt <OUTPUT_DIR>/gantt_schedule.png
   > ```"

---

## Key Principles

- **Never assume** — if information is missing, ask. A wrong assumption in a verification plan causes downstream bugs.
- **Always confirm found files** — never silently use a file found during search.
- **Confirm before using any external resource** — coding guidelines, existing VPs, etc.
- **UVM-based** — all TB architecture descriptions assume UVM methodology.
- **Industry-standard terminology** — use DV community standard terms throughout.
- **Exhaustive detail** — every section should be production-ready, not a template.
- **Interactive loops** — for Sections 9, 10, 13, 14, 15: always present a draft first, then ask the user to confirm, add, or remove content before finalizing.
