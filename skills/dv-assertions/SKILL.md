---
name: dv-assertions
description: |
  Design Verification skill (S7) that generates SystemVerilog Assertions (SVA)
  for every protocol interface and DUT-internal signal in the verification
  environment. Consumes testplan assertion_code (S2), TB data (S5), and
  sequences data (S6). Generates per-VIP assertion modules, a DUT bind module
  for internal assertions, assertion control package, UVM assertion reporter,
  and a top-level assertions package.

  Use this skill whenever a user wants to:
  - Generate SVA files from a DV testplan (S2 Excel or JSON)
  - Create per-VIP interface assertion modules with assert+cover properties
  - Create a DUT bind module for internal/hierarchical assertions
  - Generate assertion control (enable/disable per group or phase)
  - Generate a UVM assertion checker that reports CHK_ID pass/fail at sim end
  - Run /dv-assertions or S7 in the DV end-to-end flow

  Trigger on: "generate assertions", "generate SVA", "dv-assertions",
  "/dv-assertions", "S7", "write SVA", "create property", "bind assertions",
  "assertion report", "cover property", "assert property"
---

# DV Assertions Generator — S7

You are acting as a senior DV architect with 20+ years of SVA and formal
verification experience. Every assertion you generate must be syntactically
correct, semantically meaningful, and include both `assert property` and
`cover property` twins. Checker IDs from the testplan must appear as string
literals in every pass/fail action block.

---

## Generated File Layout

```
dv/
  agents/
    <vip1>_agent/
      assertions/
        <vip1>_if_assertions.sv       ← SVA module for this VIP's interface
        <vip1>_assertions_pkg.sv      ← package wrapping VIP assertions
    <vip2>_agent/
      assertions/
        <vip2>_if_assertions.sv
        <vip2>_assertions_pkg.sv
    ...
  assertions/                         ← project-level assertions
    <proj>_dut_bind.sv                ← bind module for DUT-internal signals
    <proj>_assert_ctrl_pkg.sv         ← assertion enable/disable control
    <proj>_assertion_checker.sv       ← UVM reporter component
    <proj>_top_assertions_pkg.sv      ← imports all VIP + project assertions
```

---

## Step 0 — Check Environment (ALWAYS run first)

```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s7 --install
```

---

## Step 1 — Gather Inputs

Search for inputs in this order and confirm with user before using:

| Input | Location | If Missing |
|---|---|---|
| `dv_tb_data.json` | `<PROJECT_ROOT>/dv/` | Ask user for path — required |
| `testplan.xlsx` | `<PROJECT_ROOT>/dv/` | Try `testplan_data.json`; if neither found, ask |
| `dv_sequences_data.json` | `<PROJECT_ROOT>/dv/` | Optional — used to skip CHK_IDs already handled |

If `dv_tb_data.json` is missing — STOP with the same gate prompt as S6:
```
⛔  S7 STOPPED — dv_tb_data.json not found.
    Run /dv-tb-scaffold (S5) first, or provide the path manually.
```

From `dv_tb_data.json` extract:
- `project_name`, `project_root`
- `unique_vips[]` → each: `vip_name`, `protocol`, `data_width`, `addr_width`
- VIP signal lists → from PROTOCOL_SIGNALS knowledge or proprietary_interfaces from S1
- `ral.registers[]` → register names for RAL assertion stubs
- `env.env_class`, `base_test.base_test_class`
- DUT stub module name → `<proj>_dut` (from S5 gen_dut_stub)

---

## Step 2 — Parse and Categorise Assertion Rows

Parse testplan. For each row where `checker_type` is `Assertion` or `Both`:

Extract:
- `checker_id`
- `feature`, `subfeature`
- `assertion_code` (the SVA property text from Col 9)
- `milestone`

**Categorise each assertion into one of three buckets:**

| Bucket | Criterion | Destination |
|---|---|---|
| **VIP interface** | assertion_code references signals in a known VIP's signal list | `dv/agents/<vip>_agent/assertions/` |
| **DUT internal** | assertion_code references signals not in any VIP signal list (internal nets, FSM states) | `dv/assertions/<proj>_dut_bind.sv` |
| **Protocol generic** | No assertion_code provided but checker_type=Assertion — generate standard protocol property | VIP assertions based on protocol type |

**Assignment algorithm:**
1. Tokenise all signal names from `assertion_code` (regex: identifiers in `@(posedge ...)` and property body)
2. Compare against each VIP's protocol signal list
3. VIP with highest signal-name overlap → assigned to that VIP
4. If no VIP matches any signal → assigned to DUT internal bucket
5. If `assertion_code` is empty → generate protocol-standard property stub for the VIP implied by the feature name

**Auto-generate protocol-standard properties** when assertion_code is empty:

| Protocol | Auto-generated properties |
|---|---|
| APB | `p_apb_setup_phase`: psel asserted before penable; `p_apb_no_write_while_reset`: no psel during reset |
| AHB / AHB-Lite | `p_ahb_htrans_valid`: htrans only IDLE/NONSEQ/SEQ/BUSY; `p_ahb_hready_timeout`: hready asserted within N cycles |
| AXI4 | `p_axi_awvalid_stable`: awvalid stays high until awready; `p_axi_wvalid_stable`: wvalid stable until wready; `p_axi_rdata_valid`: rvalid implies arvalid preceded it |
| AXI4-Stream | `p_axis_tvalid_stable`: tvalid held until tready; `p_axis_tlast`: tlast asserts at packet end |
| SPI | `p_spi_cs_active`: mosi stable during cs_n low; `p_spi_clk_idle`: sclk idle when cs_n high |
| I2C | `p_i2c_start_cond`: sda falls while scl high; `p_i2c_stop_cond`: sda rises while scl high |
| UART | `p_uart_start_bit`: txd falls for exactly 1 bit period; `p_uart_frame`: 8 data bits after start |
| TileLink | `p_tl_a_valid_stable`: a_valid held until a_ready; `p_tl_d_valid_stable`: d_valid held until d_ready |

Print categorisation summary:
```
============================================================
  S7 Assertion Categorisation — <PROJECT_NAME>
============================================================
  From testplan (Assertion/Both rows): N
    → VIP assignments:
        <vip1>: N assertions
        <vip2>: N assertions
    → DUT internal: N assertions
  Auto-generated protocol stubs: N
  Total assertions to generate: N (assert+cover pairs = 2N properties)
============================================================
  Confirm? [Y/N]:
```

---

## Step 3 — Generate Per-VIP Assertion Modules (one per unique VIP)

**For each unique VIP**, generate two files in `dv/agents/<vip_name>_agent/assertions/`:

### File 1: `<vip_name>_if_assertions.sv`

Structure:
```systemverilog
// =============================================================================
// FILE: dv/agents/<vip_name>_agent/assertions/<vip_name>_if_assertions.sv
// S7 auto-generated — <date>
// Protocol : <PROTOCOL>
// Contains : concurrent SVA properties + cover properties
//            Assertion control (reset-aware enable/disable)
// =============================================================================
module <vip_name>_if_assertions #(
  parameter int DATA_WIDTH = <data_width>,
  parameter int ADDR_WIDTH = <addr_width>
)(
  input logic                    clk,
  input logic                    rst_n,
  // ── Protocol signals (from <PROTOCOL> signal list) ──────────────────────
  <protocol_signal_ports>
);

  // ── Assertion control: disable during reset, enable after ───────────────
  initial begin
    $assertoff(0, <vip_name>_if_assertions);
    @(posedge rst_n);
    repeat (2) @(posedge clk);
    $asserton(0, <vip_name>_if_assertions);
  end

  // ── Default clock/reset for all properties ──────────────────────────────
  default clocking cb_mon @(posedge clk); endclocking
  default disable iff (!rst_n);

  // =========================================================================
  // Properties — from testplan (checker_type = Assertion or Both)
  // =========================================================================

  // ── <CHK_ID> : <feature> / <subfeature> ─────────────────────────────────
  // Milestone: <milestone>
  property <prop_name>;
    @(posedge clk) disable iff (!rst_n)
    <antecedent> |-> <consequent>;
  endproperty

  AST_<CHK_ID>: assert property (<prop_name>)
    $info("[PASS] <CHK_ID> — <description> at time %0t", $time);
  else
    $error("[FAIL] <CHK_ID> — <description> violated at time %0t", $time);

  COV_<CHK_ID>: cover property (<prop_name>)
    $info("[COV]  <CHK_ID> — cover property hit at time %0t", $time);

  // =========================================================================
  // Auto-generated protocol-standard properties
  // =========================================================================

  <auto_generated_properties_for_this_protocol>

endmodule : <vip_name>_if_assertions
```

**Property generation rules:**
- `assert property` label: `AST_<sanitized_chk_id>` (replace `-` with `_`)
- `cover property` label:  `COV_<sanitized_chk_id>`
- Pass action block: `$info("[PASS] <CHK_ID> — <brief> at time %0t", $time);`
- Fail action block: `$error("[FAIL] <CHK_ID> — <brief> violated at time %0t", $time);`
- Cover action block: `$info("[COV] <CHK_ID> — cover hit at time %0t", $time);`
- If `assertion_code` provided in testplan: use it verbatim, add action blocks if missing
- If `assertion_code` empty: generate protocol-standard stub (see Step 2 table), mark `// ⚠️ NEEDS_REVIEW`
- Immediate assertions for data-width checks:
  ```systemverilog
  // Immediate: signal width sanity
  initial begin
    assert (DATA_WIDTH > 0 && DATA_WIDTH <= 1024)
      else $fatal(1, "<vip_name>: illegal DATA_WIDTH=%0d", DATA_WIDTH);
  end
  ```

### File 2: `<vip_name>_assertions_pkg.sv`

```systemverilog
// =============================================================================
// FILE: dv/agents/<vip_name>_agent/assertions/<vip_name>_assertions_pkg.sv
// S7 auto-generated — <date>
// =============================================================================
package <vip_name>_assertions_pkg;
  // This package is a namespace anchor — the assertions module is not a class.
  // It is instantiated/bound via <proj>_dut_bind.sv or tb_top.sv.
  //
  // CHK_IDs covered in this package:
  //   <list of checker_ids for this VIP>
  //
  // To include in simulation:
  //   Add dv/agents/<vip_name>_agent/assertions/<vip_name>_if_assertions.sv
  //   to compile.f BEFORE tb_top.sv
endpackage : <vip_name>_assertions_pkg
```

---

## Step 4 — Generate DUT Bind Module

Location: `dv/assertions/<proj>_dut_bind.sv`

This file:
1. Instantiates per-VIP assertion modules and binds them to the interface instances in `tb_top`
2. Contains a `<proj>_dut_internal_assertions` module for DUT-internal signal assertions
3. Binds that module into the DUT

```systemverilog
// =============================================================================
// FILE: dv/assertions/<proj>_dut_bind.sv
// S7 auto-generated — <date>
// Binds VIP assertion modules to interfaces and DUT-internal assertions to DUT
// Include in compile.f after all interface and DUT files.
// =============================================================================

// ── Per-VIP interface assertion bindings ─────────────────────────────────────
// VIP: <vip1_name> — bound to each interface instance in tb_top
bind <proj>_tb_top <vip1_name>_if_assertions #(
  .DATA_WIDTH ( <data_width> ),
  .ADDR_WIDTH ( <addr_width> )
) u_<if1_name>_assertions (
  .clk   ( <if1_name>.clk   ),
  .rst_n ( <if1_name>.rst_n ),
  // Protocol signals from interface
  <protocol_signal_connections_from_if1>
);

// [repeat for each interface instance of this VIP]

// ── DUT-internal assertion module ────────────────────────────────────────────
module <proj>_dut_internal_assertions (
  input logic clk,
  input logic rst_n
  // TODO: add DUT-internal signal ports here  // ⚠️ NEEDS_REVIEW
  // These must match actual DUT port/internal signal names
);
  default clocking cb @(posedge clk); endclocking
  default disable iff (!rst_n);

  initial begin
    $assertoff(0, <proj>_dut_internal_assertions);
    @(posedge rst_n);
    repeat (2) @(posedge clk);
    $asserton(0, <proj>_dut_internal_assertions);
  end

  // ── DUT-internal assertions (signals not on any VIP interface) ───────────
  // <For each DUT-internal assertion from the categorisation step>
  //
  // property <prop_name>;
  //   @(posedge clk) disable iff (!rst_n)
  //   <antecedent> |-> <consequent>;
  // endproperty
  // AST_<CHK_ID>: assert property (<prop_name>)
  //   $info("[PASS] <CHK_ID> at %0t", $time);
  // else
  //   $error("[FAIL] <CHK_ID> at %0t", $time);
  // COV_<CHK_ID>: cover property (<prop_name>)
  //   $info("[COV] <CHK_ID> hit at %0t", $time);

  // ⚠️ NEEDS_REVIEW: populate DUT signal ports and connect below
  // after DUT RTL is available

endmodule : <proj>_dut_internal_assertions

// ── Bind DUT-internal assertions to DUT ──────────────────────────────────────
bind <proj>_dut <proj>_dut_internal_assertions u_dut_internal_assertions (
  .clk   ( clk   ),
  .rst_n ( rst_n )
  // TODO: connect DUT-internal signals here  // ⚠️ NEEDS_REVIEW
);
```

---

## Step 5 — Generate Assertion Control Package

Location: `dv/assertions/<proj>_assert_ctrl_pkg.sv`

```systemverilog
// =============================================================================
// FILE: dv/assertions/<proj>_assert_ctrl_pkg.sv
// S7 auto-generated — <date>
// Provides tasks to enable/disable assertions by group or phase.
// Import in base_test or env to call from UVM phases.
// =============================================================================
package <proj>_assert_ctrl_pkg;

  // ── Assertion groups ──────────────────────────────────────────────────────
  // Add module hierarchical paths to each group as DUT hierarchy is known
  typedef enum {
    ASSERT_GRP_ALL,
    ASSERT_GRP_PROTOCOL,     // All VIP interface assertions
    ASSERT_GRP_DUT_INTERNAL, // DUT-internal FSM / datapath assertions
    ASSERT_GRP_RAL           // Register access assertions
  } assert_group_e;

  // ── Control tasks ─────────────────────────────────────────────────────────

  // Call in reset_phase or at test start before DUT is active
  task automatic disable_all_assertions();
    $assertoff(0);
    $display("[ASSERT_CTRL] All assertions DISABLED at time %0t", $time);
  endtask

  // Call after reset is released (when DUT is in known state)
  task automatic enable_all_assertions();
    $asserton(0);
    $display("[ASSERT_CTRL] All assertions ENABLED at time %0t", $time);
  endtask

  // Call to disable assertions during a specific operation (e.g. flush)
  task automatic disable_group(assert_group_e grp);
    case (grp)
      ASSERT_GRP_PROTOCOL:
        // TODO: $assertoff(0, <tb_path>.<vip_assertions_instance>)  // ⚠️ NEEDS_REVIEW
        $display("[ASSERT_CTRL] Protocol assertions DISABLED at %0t", $time);
      ASSERT_GRP_DUT_INTERNAL:
        // TODO: $assertoff(0, <dut_path>.u_dut_internal_assertions)  // ⚠️ NEEDS_REVIEW
        $display("[ASSERT_CTRL] DUT-internal assertions DISABLED at %0t", $time);
      default:
        $assertoff(0);
    endcase
  endtask

  task automatic enable_group(assert_group_e grp);
    case (grp)
      ASSERT_GRP_PROTOCOL:
        // TODO: $asserton(0, <tb_path>.<vip_assertions_instance>)  // ⚠️ NEEDS_REVIEW
        $display("[ASSERT_CTRL] Protocol assertions ENABLED at %0t", $time);
      ASSERT_GRP_DUT_INTERNAL:
        // TODO: $asserton(0, <dut_path>.u_dut_internal_assertions)  // ⚠️ NEEDS_REVIEW
        $display("[ASSERT_CTRL] DUT-internal assertions ENABLED at %0t", $time);
      default:
        $asserton(0);
    endcase
  endtask

  // ── Assertion count query helpers ─────────────────────────────────────────
  function automatic int get_assert_fail_count();
    // VCS: use $assertfailcount system function if available
    // For portability, the UVM checker component tracks this via callbacks
    return 0;  // placeholder — populated by <proj>_assertion_checker
  endfunction

endpackage : <proj>_assert_ctrl_pkg
```

---

## Step 6 — Generate UVM Assertion Checker / Reporter

Location: `dv/assertions/<proj>_assertion_checker.sv`

This is a UVM component instantiated in the env. It:
1. Registers every CHK_ID at `start_of_simulation_phase`
2. Hooks `$assertfailcount` / `$assertpasscount` at `report_phase`
3. Prints a CHK_ID-mapped pass/fail table at end of simulation

```systemverilog
// =============================================================================
// FILE: dv/assertions/<proj>_assertion_checker.sv
// S7 auto-generated — <date>
// UVM component: registers CHK_IDs, queries assertion counts, reports summary
// Instantiate in <proj>_env (add handle + build/connect calls)
// =============================================================================
class <proj>_assertion_checker extends uvm_component;
  `uvm_component_utils(<proj>_assertion_checker)

  // ── CHK_ID registry ───────────────────────────────────────────────────────
  typedef struct {
    string chk_id;
    string description;
    string milestone;
    string assert_label;   // e.g. "AST_CHK_UART_APB_PROTOCOL_001"
    string cover_label;    // e.g. "COV_CHK_UART_APB_PROTOCOL_001"
    int    pass_count;
    int    fail_count;
    int    cover_count;
  } chk_entry_t;

  chk_entry_t chk_table[$];

  // ── UVM phases ────────────────────────────────────────────────────────────
  function new(string name = "<proj>_assertion_checker", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void start_of_simulation_phase(uvm_phase phase);
    super.start_of_simulation_phase(phase);
    _register_all_checkers();
    `uvm_info(`gtn, $sformatf("[ASSERT] %0d checker IDs registered",
                               chk_table.size()), UVM_MEDIUM)
  endfunction

  // report_phase: query pass/fail/cover counts and print table
  function void report_phase(uvm_phase phase);
    int total_pass  = 0;
    int total_fail  = 0;
    int total_cover = 0;
    super.report_phase(phase);

    // Note: $assertpasscount / $assertfailcount are VCS extensions.
    // Counts below are populated from UVM_INFO callbacks if not available.
    foreach (chk_table[i]) begin
      // Attempt VCS system function query — wrapped in conditional compile
      // `ifdef VCS
      //   chk_table[i].pass_count  = $assertpasscount(chk_table[i].assert_label);
      //   chk_table[i].fail_count  = $assertfailcount(chk_table[i].assert_label);
      //   chk_table[i].cover_count = $assertcovercount(chk_table[i].cover_label);
      // `endif
      total_pass  += chk_table[i].pass_count;
      total_fail  += chk_table[i].fail_count;
      total_cover += chk_table[i].cover_count;
    end

    // Print header
    $display("");
    $display("============================================================");
    $display("  SVA Checker Report — <proj>  (%0s)", $sformatf("%t", $time));
    $display("============================================================");
    $display("  %-40s %-8s %-8s %-8s %-12s",
             "CHK_ID", "PASS", "FAIL", "COVER", "MILESTONE");
    $display("  %s", {80{"-"}});

    foreach (chk_table[i]) begin
      string status = (chk_table[i].fail_count > 0) ? "✗" : "✓";
      $display("  %s %-38s %-8s %-8s %-8s %-12s",
               status,
               chk_table[i].chk_id,
               chk_table[i].pass_count,
               chk_table[i].fail_count,
               chk_table[i].cover_count,
               chk_table[i].milestone);
    end

    $display("  %s", {80{"-"}});
    $display("  TOTAL:  PASS=%-6d FAIL=%-6d COVER=%-6d", total_pass, total_fail, total_cover);
    if (total_fail == 0)
      $display("  ✓ ALL SVA CHECKERS PASSED");
    else
      $display("  ✗ %0d SVA CHECKER(S) FAILED — see UVM_ERROR messages above", total_fail);
    $display("============================================================");
    $display("");

    // Propagate failures to UVM error count
    if (total_fail > 0)
      `uvm_error(`gtn, $sformatf("[FAIL] %0d SVA assertion(s) violated", total_fail))
  endfunction

  // ── Private: register all CHK_IDs ─────────────────────────────────────────
  // AUTO-GENERATED: one entry per (checker_id, assertion_label) pair
  local function void _register_all_checkers();
    chk_entry_t e;
    // <GENERATED_ENTRIES — one per assertion row from testplan>
    // Example:
    // e = '{chk_id: "CHK_UART_APB_PROTOCOL_001",
    //        description: "APB no-wait check",
    //        milestone: "DV-I",
    //        assert_label: "AST_CHK_UART_APB_PROTOCOL_001",
    //        cover_label:  "COV_CHK_UART_APB_PROTOCOL_001",
    //        pass_count: 0, fail_count: 0, cover_count: 0};
    // chk_table.push_back(e);
    // ⚠️ NEEDS_REVIEW: verify assert_label matches label in _if_assertions.sv
  endfunction

endclass : <proj>_assertion_checker
```

**After generating this file, add a note to the user:**
> Add `<proj>_assertion_checker` to `<proj>_env.sv`:
> ```systemverilog
> <proj>_assertion_checker assertion_chk;
> // in build_phase:
> assertion_chk = <proj>_assertion_checker::type_id::create("assertion_chk", this);
> ```

---

## Step 7 — Generate Top-Level Assertions Package

Location: `dv/assertions/<proj>_top_assertions_pkg.sv`

```systemverilog
// =============================================================================
// FILE: dv/assertions/<proj>_top_assertions_pkg.sv
// S7 auto-generated — <date>
// Top-level package: imports all VIP assertion packages + control package
// Import in env_pkg and tests_pkg
// =============================================================================
package <proj>_top_assertions_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  // VIP assertion packages
  import <vip1_name>_assertions_pkg::*;
  import <vip2_name>_assertions_pkg::*;
  // ... one per unique VIP

  // Assertion control
  import <proj>_assert_ctrl_pkg::*;

  // UVM assertion checker
  `include "assertions/<proj>_assertion_checker.sv"

endpackage : <proj>_top_assertions_pkg
```

---

## Step 8 — Update compile.f

Append to `dv/compile.f` (deduplicated, in dependency order):

```
// S7 assertions — VIP interface assertion modules
// Note: compile assertion modules BEFORE tb_top so bind elaborates correctly
${DV_ROOT}/agents/<vip1>_agent/assertions/<vip1>_if_assertions.sv
${DV_ROOT}/agents/<vip2>_agent/assertions/<vip2>_if_assertions.sv
// ... one per unique VIP

// S7 assertions — project-level
+incdir+${DV_ROOT}/assertions
${DV_ROOT}/assertions/<proj>_assert_ctrl_pkg.sv
${DV_ROOT}/assertions/<proj>_top_assertions_pkg.sv

// S7 bind file — must be last (after all modules it binds)
${DV_ROOT}/assertions/<proj>_dut_bind.sv
```

**Important:** Bind files must be compiled **after** all modules they reference. The assertion SVA modules must be compiled **before** the bind file.

---

## Step 9 — Write dv_assertions_data.json

Write `<PROJECT_ROOT>/dv/dv_assertions_data.json`:
```json
{
  "skill": "dv-assertions",
  "version": "1.0",
  "project_name": "<proj>",
  "generated_date": "<ISO date>",
  "assertions": [
    {
      "chk_id":         "CHK_...",
      "description":    "...",
      "milestone":      "DV-I|DV-C|DV-F",
      "bucket":         "vip_interface|dut_internal",
      "vip":            "<vip_name>  (null for DUT-internal)",
      "assert_label":   "AST_CHK_...",
      "cover_label":    "COV_CHK_...",
      "source":         "testplan|auto_generated",
      "file":           "dv/agents/<vip>_agent/assertions/<vip>_if_assertions.sv"
    }
  ],
  "files": {
    "vip_assertions": ["dv/agents/<vip1>_agent/assertions/<vip1>_if_assertions.sv"],
    "dut_bind":       "dv/assertions/<proj>_dut_bind.sv",
    "assert_ctrl":    "dv/assertions/<proj>_assert_ctrl_pkg.sv",
    "checker":        "dv/assertions/<proj>_assertion_checker.sv",
    "top_pkg":        "dv/assertions/<proj>_top_assertions_pkg.sv"
  },
  "summary": {
    "total_assertions":      0,
    "from_testplan":         0,
    "auto_generated":        0,
    "vip_interface_bucket":  0,
    "dut_internal_bucket":   0,
    "assert_cover_pairs":    0,
    "needs_review_count":    0
  }
}
```

---

## Step 10 — Run Script

Write `/tmp/<proj>_assertions_input.json` with all parsed data, then:

```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_assertions.py \
  --input   /tmp/<proj>_assertions_input.json \
  --output  <dv_root>
```

---

## Step 11 — Print Terminal Summary

```
============================================================
  DV Assertions — Complete
  Project  : <PROJECT_NAME>
  Output   : <dv_root>
============================================================
  Per-VIP assertion modules : N  (N protocols)
    <vip1>: N properties  (N assert + N cover)
    <vip2>: N properties  ...
  DUT-internal assertions   : N  (in _dut_bind.sv)
  Auto-generated stubs      : N  (⚠️ protocol defaults)
------------------------------------------------------------
  Total assert+cover pairs  : N
  Checker IDs covered       : N
  Milestone: DV-I=N  DV-C=N  DV-F=N
------------------------------------------------------------
  ⚠️  NEEDS_REVIEW : N items
     → grep -r "NEEDS_REVIEW" <dv_root>/assertions <dv_root>/agents
------------------------------------------------------------
  Files:
    compile.f updated  (+N entries, bind file last)
    dv_assertions_data.json written
------------------------------------------------------------
  Next step: /dv-scoreboard (S8) to generate scoreboard
             checker tasks referencing these CHK_IDs
============================================================
```

---

## Important Notes

- **assert + cover pair is mandatory** — every `assert property` must have a corresponding `cover property` with the same property expression
- **Action blocks are mandatory** — every `assert` must have both a pass-action `$info("[PASS] CHK_ID...")` and fail-action `$error("[FAIL] CHK_ID...")`; `cover` must have `$info("[COV] CHK_ID...")`
- **Label format is mandatory** — `AST_<CHK_ID_with_underscores>` and `COV_<CHK_ID_with_underscores>` — these labels are referenced by the assertion checker reporter
- **Bind file order** — bind file must come last in compile.f; assertion modules before tb_top
- **default clocking + default disable iff** — declare both at module level so all properties inherit them rather than repeating per property
- **Reset awareness** — every property must have `disable iff (!rst_n)` either via `default disable iff` or inline
- **`$assertoff` in initial block** — always disable assertions at time 0 and re-enable after reset; prevents false failures during power-on
- **SVA syntax correctness** — think carefully: `|->` is non-overlapping implication (same cycle), `|=>` is overlapping; `##N` means exactly N cycles; `[*N:M]` means N to M consecutive repetitions
- **Never overwrite** existing files — safe_write only
