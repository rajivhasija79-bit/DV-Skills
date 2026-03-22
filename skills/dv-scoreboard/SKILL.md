---
name: dv-scoreboard
description: |
  Design Verification skill (S8) that generates a complete scoreboard and
  reference model implementation for a UVM testbench. Builds on top of the
  S5 skeletons, implements per-feature check tasks, CHK_ID-mapped pass/fail
  reporting, reference model with analysis port to scoreboard, and a
  functional coverage model that receives passing transactions from the
  scoreboard via analysis port.

  This skill is HIGHLY INTERACTIVE — it asks the user targeted questions
  after analyzing the design, testplan, and existing checker coverage before
  generating any code.

  Use this skill whenever a user wants to:
  - Implement the DV scoreboard for a UVM testbench
  - Implement a reference / prediction model
  - Generate functional coverage model fed from scoreboard pass events
  - Generate CHK_ID-mapped check tasks from testplan
  - Run /dv-scoreboard or S8 in the DV end-to-end flow

  Trigger on: "generate scoreboard", "implement scoreboard", "dv-scoreboard",
  "/dv-scoreboard", "S8", "reference model", "implement checker",
  "scoreboard implementation", "generate ref model"
---

# DV Scoreboard & Reference Model Generator — S8

You are acting as a senior DV architect. The scoreboard and reference model
are the most design-specific components in the testbench — you must
**understand the design before writing a single line of code**. This skill
is structured around a mandatory analysis + question phase before generation.

---

## Generated File Layout

```
dv/
  env/
    <proj>_scoreboard.sv           ← full scoreboard (replaces S5 skeleton)
    <proj>_ref_model.sv            ← full ref model  (replaces S5 skeleton)
    <proj>_sb_transaction.sv       ← shared sb↔coverage transaction class
    <proj>_functional_coverage.sv  ← project-level coverage (fed from SB)
```

---

## Step 0 — Check Environment (ALWAYS run first)

```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s8 --install
```

---

## Step 1 — Gather Inputs

Search for and load (confirm paths with user if ambiguous):

| Input | Location | Required? |
|---|---|---|
| `dv_tb_data.json` | `<PROJECT_ROOT>/dv/` | **Required** — STOP if missing |
| `testplan.xlsx` / `testplan_data.json` | `<PROJECT_ROOT>/dv/` | Required |
| `dv_assertions_data.json` | `<PROJECT_ROOT>/dv/` | Optional — used to skip checks already in SVA |
| `dv_sequences_data.json` | `<PROJECT_ROOT>/dv/` | Optional — used to skip checks already in sequences |
| Existing `<proj>_scoreboard.sv` | `<PROJECT_ROOT>/dv/env/` | Optional — S5 skeleton to replace |
| Existing `<proj>_ref_model.sv` | `<PROJECT_ROOT>/dv/env/` | Optional — S5 skeleton to replace |

If `dv_tb_data.json` missing — STOP:
```
⛔  S8 STOPPED — dv_tb_data.json not found.
    Run /dv-tb-scaffold (S5) first or provide the path manually.
```

---

## Step 2 — Design Analysis (ALWAYS before asking questions)

Before asking the user anything, perform a thorough analysis of all inputs.
Build an internal design model covering:

### 2a — Data flow analysis

From `dv_tb_data.json`:
- List every unique VIP and its role (master/slave)
- Identify which VIPs produce data that needs checking (output/response side)
- Identify which VIPs carry stimulus (input side)
- Identify register bus VIP (RAL) — register reads/writes checked via RAL mirror
- Map: `<stimulus_vip> → DUT → <response_vip>` for each data path

Example data flow table to build internally:
```
Interface        Role     Direction    Needs check?   Mechanism
ahb_reg_if       slave    inbound      register R/W   RAL mirror
axi4s_in_if      slave    inbound      stimulus only  N/A
spi_out_if       master   outbound     data check     SB comparison
```

### 2b — Check analysis from testplan

For each testplan row that has a `checker_id` and `checker_type = Procedural` or `Both`:
- Extract the "Checks" and "Pass Criteria" sections from `testcase_description`
- Determine what is being compared (register value / data payload / protocol field / timing)
- Flag any checks that are already covered by SVA (cross-ref `dv_assertions_data.json`)
- Flag any checks that are already in sequence stubs (cross-ref `dv_sequences_data.json`)

### 2c — Reference model requirements

From the data flow and testplan checks, determine:
- Does the DUT transform data (encode/compress/encrypt/filter)?
- Does the DUT have state that affects outputs (FSM, counters, FIFOs)?
- Are there register-configurable behaviours that affect DUT output?
- Is the scoreboard purely reactive (protocol checks + RAL mirror) or does it
  need a prediction model?

### 2d — Build the question set

Based on the analysis, form a targeted question list. Only ask questions where
the answer is not derivable from the specification/testplan. Mark each question
as REQUIRED (cannot generate without) or OPTIONAL (has a sensible default).

---

## Step 3 — Interactive Design Questions (ALL in one message)

Print the analysis summary first, then ask all questions in **one message**.
Never ask questions one at a time.

```
============================================================
  S8 Design Analysis — <PROJECT_NAME>
============================================================
  Data flows detected:
    <stimulus_vip> → DUT → <response_vip>  [needs check: YES/NO]
    <reg_bus_vip>  → DUT (registers)        [RAL mirror: YES]
    ...

  Testplan checks to implement:
    Procedural/Both: N rows
    Already in SVA (skip): N rows
    Already in sequences (skip): N rows
    Net new checks for scoreboard: N

  Reference model assessment:
    DUT appears to <transform data / route data / only register I/O>
    → Prediction complexity: <simple/moderate/complex>
============================================================

  Please answer the following to configure the scoreboard:

  [Q1] Scoreboard comparison style:
       Based on the DUT's <describe data path>, I suggest:
       a) In-order FIFO  — transactions matched in arrival order
       b) Out-of-order   — transactions matched by key (ID/address/tag)
       c) Reactive only  — no expected/actual queue; checks protocol
                          correctness and RAL mirror only
       Which? (a/b/c) [default: <inferred>]:

  [Q2] If out-of-order (b): what field is the transaction matching key?
       (e.g. AXID, transaction tag, address, sequence number)
       [skip if a or c]:

  [Q3] Check trigger:
       a) Automatic — check on every write_<response_vip>() call
       b) Explicit  — vseq calls scoreboard.check() at test end
       c) Configurable — env_cfg.sb_trigger field controls it at runtime
       Which? [default: a]:

  [Q4] Existing reference model?
       a) No — S8 generates SystemVerilog prediction stub
       b) Yes, SystemVerilog — provide path: ___
       c) Yes, C/C++ model — provide path and DPI function names: ___
       d) Yes, Python/other — provide description: ___
       Which? [default: a]:

  [Q5] Burst / packet reassembly needed?
       For AXI4 / AXI4-Stream: does the scoreboard compare individual
       beats or fully assembled packets/bursts?
       a) Individual beats
       b) Assembled packets (S8 generates reassembly logic)
       [default: a] [skip if not AXI4/Stream]:

  [Q6] RAL usage in scoreboard:
       a) Auto-compare all register reads against RAL mirror (recommended)
       b) Only compare registers explicitly listed in testplan checks
       c) No register checking in scoreboard (handled elsewhere)
       Which? [default: a]:

  [Q7] The following checks from the testplan appear to already be
       implemented:
         <list from cross-ref with dv_assertions_data.json>
         <list from cross-ref with dv_sequences_data.json>
       Should S8 skip these and avoid duplication? [Y/N, default: Y]:

  [Q8] Any protocol-specific checks that the VIP monitor already
       performs (e.g. APB handshake, AXI4 response codes)?
       S8 will NOT duplicate these — just confirm which VIPs have
       self-checking monitors:
         <list detected VIPs> — self-checking? [Y/N per VIP]:

  [Q9] Scoreboard pass threshold:
       How many checks must pass for the test to be considered passing?
       a) All checks must pass (zero tolerance)
       b) Configurable via plusarg +SB_MAX_ERRORS=N
       c) Per-feature threshold (ask per feature)
       Which? [default: a]:
============================================================
```

Wait for ALL answers before proceeding to generation.

---

## Step 4 — Confirm Check Allocation

After receiving answers, print a check allocation table for user confirmation:

```
============================================================
  Check Allocation — <PROJECT_NAME>
============================================================
  CHK_ID                          Where implemented
  ─────────────────────────────── ─────────────────────────
  CHK_UART_APB_PROTOCOL_001       SVA (skip — in S7)
  CHK_UART_TX_FUNCTIONAL_001      SVA (skip — in S7)
  CHK_UART_TX_DATA_INTEGRITY_001  Scoreboard — write_uart_vip()
  CHK_UART_BAUD_TIMING_001        Scoreboard — check_baud_rate()
  CHK_UART_REG_CTRL_001           Scoreboard — RAL mirror check
  ...
============================================================
  Proceed? [Y / edit]:
```

Wait for confirmation. If user edits, re-print the table.

---

## Step 5 — Generate Scoreboard Implementation

Replace (or flesh out) `dv/env/<proj>_scoreboard.sv`.

### Full scoreboard structure:

```systemverilog
// =============================================================================
// FILE: dv/env/<proj>_scoreboard.sv
// S8 generated — <date>
// Architecture: <in_order|out_of_order|reactive>
// Trigger     : <per_txn|explicit|configurable>
// =============================================================================
class <proj>_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(<proj>_scoreboard)

  // ── Analysis imports (one per VIP monitor + one for ref model) ────────────
  `uvm_analysis_imp_decl(_<vip1>)
  `uvm_analysis_imp_decl(_<vip2>)
  `uvm_analysis_imp_decl(_expected)   // from ref model

  uvm_analysis_imp__<vip1>    #(<vip1>_seq_item, <proj>_scoreboard) m_<vip1>_imp;
  uvm_analysis_imp__<vip2>    #(<vip2>_seq_item, <proj>_scoreboard) m_<vip2>_imp;
  uvm_analysis_imp__expected  #(<proj>_ref_txn,  <proj>_scoreboard) m_expected_imp;

  // ── Analysis export to functional coverage model ──────────────────────────
  uvm_analysis_port #(<proj>_sb_transaction) m_cov_ap;

  // ── Handles ───────────────────────────────────────────────────────────────
  <proj>_reg_block  ral;         // set by base_test before run_phase
  <proj>_env_cfg    cfg;         // set by env in connect_phase

  // ── Transaction storage ───────────────────────────────────────────────────
  // In-order style: separate queue per channel
  <vip1>_seq_item  m_<vip1>_q[$];
  <proj>_ref_txn   m_expected_q[$];
  // Out-of-order style (if selected): assoc array keyed by match_key
  // <type>          m_actual_aa[<key_type>];
  // <proj>_ref_txn  m_expected_aa[<key_type>];

  // ── Check counters (per CHK_ID) ───────────────────────────────────────────
  int m_pass_cnt[string];
  int m_fail_cnt[string];
  int m_total_checks;

  // ── Scoreboard enable (controlled by cfg) ─────────────────────────────────
  bit m_sb_enabled = 1;

  // ── Constructor + UVM phases ──────────────────────────────────────────────
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    m_<vip1>_imp   = new("m_<vip1>_imp",   this);
    m_<vip2>_imp   = new("m_<vip2>_imp",   this);
    m_expected_imp = new("m_expected_imp", this);
    m_cov_ap       = new("m_cov_ap",       this);
  endfunction

  function void connect_phase(uvm_phase phase);
    // cfg and ral are set by env — no action needed here
  endfunction

  // ── write functions — called by each VIP monitor ─────────────────────────
  // [see Step 5a below for per-VIP implementations]

  // ── write_expected — called by ref model ─────────────────────────────────
  function void write_expected(<proj>_ref_txn txn);
    m_expected_q.push_back(txn);
  endfunction

  // ── Per-feature check tasks ───────────────────────────────────────────────
  // [see Step 5b below for per-check implementations]

  // ── report_phase — CHK_ID summary table ──────────────────────────────────
  function void report_phase(uvm_phase phase);
    // [see Step 5c below]
  endfunction
endclass
```

### Step 5a — write() functions per VIP

Generate one `write_<vip>()` function per VIP that sends to the scoreboard.

**For register bus VIP (e.g. APB/AHB RAL bus):**
```systemverilog
function void write_<reg_vip>(<reg_vip>_seq_item txn);
  if (!m_sb_enabled) return;
  // Register reads: compare against RAL mirror
  if (txn.is_read()) begin
    uvm_reg        rg;
    uvm_reg_data_t mirror_val;
    rg = ral.default_map.get_reg_by_offset(txn.addr);
    if (rg == null) begin
      `uvm_error(`gtn, $sformatf(
        "[FAIL] CHK_<IP>_REG_UNKNOWN — No RAL register at addr 0x%0h", txn.addr))
      m_fail_cnt["CHK_<IP>_REG_UNKNOWN"]++;
      return;
    end
    mirror_val = rg.get_mirrored_value();
    _chk_reg_read(rg.get_name(), txn.rdata, mirror_val);
  end
  // Register writes: update RAL mirror
  else begin
    uvm_status_e status;
    uvm_reg rg = ral.default_map.get_reg_by_offset(txn.addr);
    if (rg != null)
      rg.predict(txn.wdata, .kind(UVM_PREDICT_WRITE));
  end
endfunction
```

**For data-path VIP (e.g. AXI4-Stream output):**
```systemverilog
function void write_<data_vip>(<data_vip>_seq_item txn);
  if (!m_sb_enabled) return;
  m_<data_vip>_q.push_back(txn);
  // Trigger: automatic per-transaction
  if (cfg.sb_trigger == SB_TRIGGER_AUTO && m_expected_q.size() > 0)
    _compare_<data_vip>(txn, m_expected_q.pop_front());
  else if (cfg.sb_trigger == SB_TRIGGER_AUTO && m_expected_q.size() == 0)
    `uvm_warning(`gtn, $sformatf(
      "[WARN] Received %s transaction but expected queue is empty — ref model lagging?",
      "<data_vip>"))
endfunction
```

### Step 5b — Per-feature check tasks

**Generate one check task per unique CHK_ID allocated to scoreboard:**

```systemverilog
// ── CHK_ID: <chk_id> — <feature>/<subfeature> ──────────────────────────────
// Testplan: <brief_description>
// Checks  : <Checks section from testcase_description>
// Criteria: <Pass Criteria section>
task _chk_<sanitized_feature>(
  input <type> actual,
  input <type> expected,
  input string context_info = ""
);
  m_total_checks++;
  if (actual === expected) begin
    m_pass_cnt["<chk_id>"]++;
    `uvm_info(`gtn, $sformatf(
      "[PASS] <chk_id> — <description>: act=0x%0h exp=0x%0h %s",
      actual, expected, context_info), UVM_MEDIUM)
    // Send passing transaction to coverage model
    begin
      <proj>_sb_transaction sb_txn = <proj>_sb_transaction::type_id::create("sb_txn");
      sb_txn.chk_id    = "<chk_id>";
      sb_txn.feature   = "<feature>";
      sb_txn.result    = SB_PASS;
      sb_txn.actual    = actual;
      sb_txn.expected  = expected;
      m_cov_ap.write(sb_txn);
    end
  end else begin
    m_fail_cnt["<chk_id>"]++;
    `uvm_error(`gtn, $sformatf(
      "[FAIL] <chk_id> — <description>: act=0x%0h exp=0x%0h %s",
      actual, expected, context_info))
  end
endtask
```

**RAL register read check (auto-generated for every register):**
```systemverilog
task _chk_reg_read(
  input string     reg_name,
  input uvm_reg_data_t actual,
  input uvm_reg_data_t expected
);
  string chk_id = $sformatf("CHK_%s_REG_%s_READ", "<IP>", reg_name.toupper());
  m_total_checks++;
  if (actual === expected) begin
    m_pass_cnt[chk_id]++;
    `uvm_info(`gtn, $sformatf(
      "[PASS] %s — reg %s: act=0x%0h exp=0x%0h (mirror)", chk_id, reg_name, actual, expected),
      UVM_MEDIUM)
  end else begin
    m_fail_cnt[chk_id]++;
    `uvm_error(`gtn, $sformatf(
      "[FAIL] %s — reg %s: act=0x%0h exp=0x%0h (mirror)", chk_id, reg_name, actual, expected))
  end
endtask
```

### Step 5c — report_phase

```systemverilog
function void report_phase(uvm_phase phase);
  int total_pass = 0, total_fail = 0;
  super.report_phase(phase);

  foreach (m_pass_cnt[id]) total_pass += m_pass_cnt[id];
  foreach (m_fail_cnt[id]) total_fail += m_fail_cnt[id];

  $display("");
  $display("============================================================");
  $display("  Scoreboard Report — <proj>  (time=%0t)", $time);
  $display("============================================================");
  $display("  %-2s %-42s %-8s %-8s", "  ", "CHK_ID", "PASS", "FAIL");
  $display("  %s", {80{"-"}});

  foreach (m_pass_cnt[id]) begin
    string status = (m_fail_cnt.exists(id) && m_fail_cnt[id] > 0) ? "✗" : "✓";
    $display("  %s %-40s %-8d %-8d", status, id,
             m_pass_cnt[id],
             m_fail_cnt.exists(id) ? m_fail_cnt[id] : 0);
  end

  $display("  %s", {80{"-"}});
  $display("  TOTAL: PASS=%-6d FAIL=%-6d  (total checks=%0d)",
           total_pass, total_fail, m_total_checks);

  if (total_fail == 0)
    `uvm_info(`gtn, "[PASS] All scoreboard checks passed", UVM_NONE)
  else
    `uvm_error(`gtn, $sformatf("[FAIL] %0d scoreboard check(s) failed", total_fail))
endfunction
```

**Also add a public `check_all()` task** (called from vseq when trigger=explicit):
```systemverilog
task check_all();
  // Drain all queues and compare remaining expected vs actual
  while (m_expected_q.size() > 0 && m_<data_vip>_q.size() > 0)
    _compare_<data_vip>(m_<data_vip>_q.pop_front(), m_expected_q.pop_front());
  if (m_expected_q.size() > 0)
    `uvm_error(`gtn, $sformatf("[FAIL] %0d expected transactions never received from DUT",
               m_expected_q.size()))
  if (m_<data_vip>_q.size() > 0)
    `uvm_error(`gtn, $sformatf("[FAIL] %0d unexpected DUT transactions have no prediction",
               m_<data_vip>_q.size()))
endtask
```

---

## Step 6 — Generate Reference Model

Replace (or flesh out) `dv/env/<proj>_ref_model.sv`.

### Architecture:
```
VIP Monitor(s)
    │  analysis port (input transactions)
    ▼
<proj>_ref_model
    │  m_sb_ap (predicted output)
    ▼
<proj>_scoreboard.m_expected_imp
```

```systemverilog
// =============================================================================
// FILE: dv/env/<proj>_ref_model.sv
// S8 generated — <date>
// Reference model: receives input stimulus from monitors, predicts DUT output,
// sends prediction to scoreboard via m_sb_ap.
//
// ⚠️ NEEDS_ENGINEER_REVIEW: predict() must be filled with DUT behavioral model
// =============================================================================
class <proj>_ref_model extends uvm_component;
  `uvm_component_utils(<proj>_ref_model)

  // ── Receive input transactions from stimulus VIP monitors ────────────────
  uvm_analysis_imp #(<stim_vip>_seq_item, <proj>_ref_model) m_<stim_vip>_imp;

  // ── Send predictions to scoreboard ────────────────────────────────────────
  uvm_analysis_port #(<proj>_ref_txn) m_sb_ap;

  // ── RAL + cfg (DUT configuration for prediction) ──────────────────────────
  <proj>_reg_block  ral;   // set by base_test — use for register-configurable behaviour
  <proj>_env_cfg    cfg;

  // ── Internal state (DUT model state) ──────────────────────────────────────
  // TODO: add counters, FIFOs, FSM state variables matching DUT internals
  // ⚠️ NEEDS_ENGINEER_REVIEW: mirror DUT state here

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    m_<stim_vip>_imp = new("m_<stim_vip>_imp", this);
    m_sb_ap          = new("m_sb_ap", this);
  endfunction

  // ── write() — called by stimulus VIP monitor ──────────────────────────────
  function void write(<stim_vip>_seq_item txn);
    predict(txn);
  endfunction

  // ── predict() — DUT behavioral model ──────────────────────────────────────
  // Given input transaction, compute expected DUT output and send to scoreboard.
  //
  // Structure:
  //   1. Read DUT config from RAL: operating mode, enables, thresholds
  //   2. Apply DUT transformation to input data
  //   3. Create <proj>_ref_txn with predicted output fields
  //   4. Send to scoreboard via m_sb_ap
  //
  // ⚠️ NEEDS_ENGINEER_REVIEW: implement DUT behaviour below
  protected function void predict(<stim_vip>_seq_item txn);
    <proj>_ref_txn pred;
    uvm_reg_data_t ctrl_val, mode_val;

    // Step 1: Read DUT operating config from RAL mirror
    // Example: ctrl_val = ral.<ctrl_reg>.get_mirrored_value();
    //          mode_val = ral.<ctrl_reg>.<mode_field>.get();
    // TODO: add register reads for all config-dependent fields  // ⚠️ NEEDS_ENGINEER_REVIEW

    // Step 2: Compute prediction
    pred = <proj>_ref_txn::type_id::create("pred");
    pred.stimulus = txn;

    // TODO: implement DUT transform here  // ⚠️ NEEDS_ENGINEER_REVIEW
    // Example patterns:
    //   pred.data = txn.data;              // pass-through
    //   pred.data = txn.data ^ mask;       // XOR transform
    //   pred.data = crc(txn.data);         // CRC computation
    //   pred.data = fifo_model.pop();      // FIFO model

    // Step 3: Send prediction to scoreboard
    m_sb_ap.write(pred);
  endfunction

  // ── Optional: DPI-C interface for C reference model ───────────────────────
  // If Q4 answer was "C/C++ model", uncomment and fill:
  // import "DPI-C" function void c_predict(
  //   input  int unsigned data_in,
  //   output int unsigned data_out
  // );

endclass : <proj>_ref_model
```

### `<proj>_ref_txn` transaction class:

```systemverilog
class <proj>_ref_txn extends uvm_sequence_item;
  `uvm_object_utils(<proj>_ref_txn)

  // Source stimulus transaction (for context in error messages)
  <stim_vip>_seq_item stimulus;

  // Predicted output fields — match response VIP seq_item fields
  // TODO: add fields matching <resp_vip>_seq_item  // ⚠️ NEEDS_ENGINEER_REVIEW
  rand logic [<data_width>-1:0] data;
  rand logic [<addr_width>-1:0] addr;
  rand logic [1:0]               status;

  function new(string name = "<proj>_ref_txn");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("ref_txn: data=0x%0h addr=0x%0h status=%0b", data, addr, status);
  endfunction
endclass
```

---

## Step 7 — Generate Scoreboard Transaction (SB → Coverage)

`dv/env/<proj>_sb_transaction.sv`:
```systemverilog
// Transaction type sent from scoreboard to functional coverage model
// on every PASSING check — carries context for coverage sampling
typedef enum { SB_PASS, SB_FAIL } sb_result_e;

class <proj>_sb_transaction extends uvm_sequence_item;
  `uvm_object_utils(<proj>_sb_transaction)

  string       chk_id;
  string       feature;
  sb_result_e  result;
  logic [63:0] actual;
  logic [63:0] expected;
  string       context_info;

  function new(string name = "<proj>_sb_transaction");
    super.new(name);
  endfunction
endclass
```

---

## Step 8 — Generate Functional Coverage Model

`dv/env/<proj>_functional_coverage.sv`:

This is a `uvm_subscriber` that receives `<proj>_sb_transaction` from the
scoreboard's `m_cov_ap` and samples functional coverage groups.

```systemverilog
// =============================================================================
// FILE: dv/env/<proj>_functional_coverage.sv
// S8 generated — <date>
// Receives PASSING transactions from scoreboard → samples functional coverage.
// This is the ONLY component that samples functional coverage.
// Per-VIP protocol coverage is in <vip>_coverage.sv (generated by S5).
// =============================================================================
class <proj>_functional_coverage extends uvm_subscriber #(<proj>_sb_transaction);
  `uvm_component_utils(<proj>_functional_coverage)

  // ── Coverage groups — one per major feature ───────────────────────────────
  // Each covergroup samples on a passing scoreboard transaction

  covergroup cg_<feature> @(posedge cov_event);
    cp_result: coverpoint last_txn.result {
      bins pass = {SB_PASS};
    }
    // TODO: add data/mode coverpoints from feature analysis  // ⚠️ NEEDS_REVIEW
    // cp_data: coverpoint last_txn.actual[7:0];
    // cp_mode: coverpoint cfg_mode { bins mode_a = {2'b00}; bins mode_b = {2'b01}; }
  endgroup

  <proj>_sb_transaction last_txn;
  event                  cov_event;
  bit                    cov_enabled = 1;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    cg_<feature> = new();
  endfunction

  // ── write() — called by scoreboard m_cov_ap ───────────────────────────────
  function void write(<proj>_sb_transaction txn);
    if (!cov_enabled) return;
    last_txn = txn;
    -> cov_event;
    // Route to feature-specific covergroup
    case (txn.feature)
      "<feature1>": /* cg_<feature1> already triggered by event */ ;
      // add cases per feature
      default: ; // unknown feature — no coverage
    endcase
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info(`gtn, $sformatf(
      "[COV] <proj>_functional_coverage: cg_<feature> = %.1f%%",
      cg_<feature>.get_coverage()), UVM_NONE)
  endfunction
endclass
```

---

## Step 9 — Update env.sv

After generating the new files, instruct the user to update `<proj>_env.sv`:

Add to the env:
```systemverilog
// In class declaration:
<proj>_ref_model          ref_model;
<proj>_functional_coverage func_cov;

// In build_phase:
ref_model = <proj>_ref_model::type_id::create("ref_model", this);
func_cov  = <proj>_functional_coverage::type_id::create("func_cov", this);

// In connect_phase (add to existing connections):
// Stimulus monitor → ref model
m_<stim_vip>_agent.monitor.ap.connect(ref_model.m_<stim_vip>_imp);
// Ref model → scoreboard
ref_model.m_sb_ap.connect(scoreboard.m_expected_imp);
// Scoreboard → coverage
scoreboard.m_cov_ap.connect(func_cov.analysis_export);
// RAL and cfg handles
scoreboard.ral = ral;
scoreboard.cfg = cfg;
ref_model.ral  = ral;
ref_model.cfg  = cfg;
```

Print this as a code block with a message:
> "The following changes must be made to `<proj>_env.sv` to wire up the new components:"

---

## Step 10 — Update compile.f

Append (deduplicated):
```
// S8 scoreboard and reference model
${DV_ROOT}/env/<proj>_sb_transaction.sv
${DV_ROOT}/env/<proj>_ref_txn.sv
${DV_ROOT}/env/<proj>_ref_model.sv
${DV_ROOT}/env/<proj>_scoreboard.sv
${DV_ROOT}/env/<proj>_functional_coverage.sv
```

---

## Step 11 — Write dv_scoreboard_data.json

```json
{
  "skill": "dv-scoreboard",
  "version": "1.0",
  "project_name": "<proj>",
  "generated_date": "<ISO date>",
  "config": {
    "style":           "in_order|out_of_order|reactive",
    "trigger":         "per_txn|explicit|configurable",
    "match_key":       "null|<field_name>",
    "has_ref_model":   true,
    "ref_model_type":  "sv_stub|sv_existing|dpi_c",
    "ral_checks":      true,
    "burst_reassembly":false
  },
  "checks": [
    {
      "chk_id":    "CHK_...",
      "feature":   "...",
      "type":      "data_compare|ral_mirror|protocol",
      "task_name": "_chk_<sanitized>",
      "milestone": "DV-I|DV-C|DV-F"
    }
  ],
  "files": {
    "scoreboard":     "dv/env/<proj>_scoreboard.sv",
    "ref_model":      "dv/env/<proj>_ref_model.sv",
    "ref_txn":        "dv/env/<proj>_ref_txn.sv",
    "sb_transaction": "dv/env/<proj>_sb_transaction.sv",
    "func_coverage":  "dv/env/<proj>_functional_coverage.sv"
  },
  "summary": {
    "total_checks":         0,
    "ral_checks":           0,
    "data_compare_checks":  0,
    "protocol_checks":      0,
    "skipped_in_sva":       0,
    "needs_review_count":   0
  }
}
```

---

## Step 12 — Terminal Summary

```
============================================================
  DV Scoreboard — Complete
  Project   : <PROJECT_NAME>
  Output    : <dv_root>/env/
============================================================
  Architecture  : <in_order|out_of_order|reactive>
  Trigger       : <per_txn|explicit|configurable>
  Reference model: <sv_stub|sv_existing|dpi_c>
------------------------------------------------------------
  Check tasks generated : N
    RAL mirror checks   : N  (auto, all registers)
    Data compare checks : N  (from testplan)
    Protocol checks     : N
    Skipped (in SVA)    : N
------------------------------------------------------------
  Coverage model : <proj>_functional_coverage.sv
    Covergroups  : N
    Fed from     : scoreboard.m_cov_ap
------------------------------------------------------------
  ⚠️  NEEDS_ENGINEER_REVIEW: N items
     → predict() in <proj>_ref_model.sv  (DUT model)
     → coverpoint values in _functional_coverage.sv
     → DUT-internal signal connections in _dut_bind.sv
  grep -r "NEEDS_ENGINEER_REVIEW" <dv_root>/env
------------------------------------------------------------
  env.sv wiring: see connection block printed above
------------------------------------------------------------
  Next step: /dv-regression (S9) to set up regression Makefile
============================================================
```

---

## Important Notes

- **Always ask before generating** — never assume scoreboard architecture from protocol alone
- **Avoid duplicating SVA checks** — cross-reference `dv_assertions_data.json` before adding a check task
- **RAL mirror checks are free** — generate `_chk_reg_read()` for ALL registers automatically without asking
- **predict() is always a stub** — the DUT behavioral model is design-specific; always mark `// ⚠️ NEEDS_ENGINEER_REVIEW`
- **CHK_ID in every check call** — every `_chk_*()` task call must pass the CHK_ID string; no anonymous checks
- **Scoreboard must be passive-safe** — all write() functions guard on `m_sb_enabled`; never block in write()
- **Coverage model is a subscriber** — not a monitor; no clock sensitivity; pure data-driven
- **Never replace env.sv directly** — print the required changes as a code block; engineer applies them
- **One question batch only** — all design questions in Step 3 go in one message; wait for full response before coding
