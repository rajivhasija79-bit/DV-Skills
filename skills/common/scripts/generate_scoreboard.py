#!/usr/bin/env python3
"""
generate_scoreboard.py — S8 dv-scoreboard generator
Generates scoreboard, reference model, sb_transaction, functional coverage.

Usage:
  python3 generate_scoreboard.py --input /tmp/<proj>_sb_input.json --output <dv_root>
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import date

# ── Utilities ─────────────────────────────────────────────────────────────────

def safe_write(path, content):
    if os.path.exists(path):
        print(f"  [SKIP] {path}  (exists — use --force to overwrite)")
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  [GEN]  {path}")
    return True


def force_write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  [GEN]  {path}")


def sanitize(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()


def parse_testcase_sections(desc):
    sections = {}
    current = None
    for line in (desc or "").splitlines():
        line = line.strip()
        for key in ["DUT Config", "Stimulus", "Expected Behavior",
                    "Checks", "Pass Criteria", "Notes"]:
            if line.startswith(key + ":"):
                current = key
                sections[current] = line[len(key)+1:].strip()
                break
        else:
            if current and line:
                sections[current] = sections.get(current, "") + " " + line
    return sections


def ip_tag(proj):
    """Uppercase IP tag from project name."""
    return proj.upper().replace("_", "_")


# ── Data width helpers ────────────────────────────────────────────────────────

def max_data_width(unique_vips):
    widths = [v.get("data_width", 32) for v in unique_vips if v.get("data_width", 0) > 0]
    return max(widths) if widths else 32


def max_addr_width(unique_vips):
    widths = [v.get("addr_width", 32) for v in unique_vips if v.get("addr_width", 0) > 0]
    return max(widths) if widths else 32


# ── Check allocation: filter out SVA-covered CHK_IDs ─────────────────────────

def load_sva_chk_ids(dv_root):
    path = os.path.join(dv_root, "dv_assertions_data.json")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        data = json.load(f)
    return {a.get("chk_id", "") for a in data.get("assertions", [])}


def load_seq_chk_ids(dv_root):
    path = os.path.join(dv_root, "dv_sequences_data.json")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        data = json.load(f)
    chk_ids = set()
    for s in data.get("sequences", []):
        for c in s.get("checker_ids", []):
            chk_ids.add(c)
    return chk_ids


def get_sb_checks(testplan_rows, sva_ids, seq_ids, skip_duplicates=True):
    """Return rows that need scoreboard check tasks."""
    result = []
    for row in testplan_rows:
        chk_type = row.get("checker_type", "")
        chk_id   = row.get("checker_id", "")
        if chk_type not in ("Procedural", "Both"):
            continue
        if skip_duplicates and chk_id in sva_ids:
            continue  # already in SVA
        result.append(row)
    return result


# ── sb_transaction generator ──────────────────────────────────────────────────

def gen_sb_transaction(proj, dv_root):
    filepath = os.path.join(dv_root, "env", f"{proj}_sb_transaction.sv")
    content = f"""\
// =============================================================================
// FILE: dv/env/{proj}_sb_transaction.sv
// S8 auto-generated — {date.today().isoformat()}
// Transaction sent from scoreboard → functional coverage model on every check.
// =============================================================================

typedef enum bit {{ SB_PASS = 1'b0, SB_FAIL = 1'b1 }} sb_result_e;

class {proj}_sb_transaction extends uvm_sequence_item;
  `uvm_object_utils({proj}_sb_transaction)

  string       chk_id;
  string       feature;
  sb_result_e  result;
  logic [63:0] actual;
  logic [63:0] expected;
  string       context_info;

  function new(string name = "{proj}_sb_transaction");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("[%s] %s feat=%s act=0x%0h exp=0x%0h %s",
                     result == SB_PASS ? "PASS" : "FAIL",
                     chk_id, feature, actual, expected, context_info);
  endfunction
endclass : {proj}_sb_transaction
"""
    safe_write(filepath, content)
    return filepath


# ── ref_txn generator ─────────────────────────────────────────────────────────

def gen_ref_txn(proj, unique_vips, dv_root):
    dw = max_data_width(unique_vips)
    aw = max_addr_width(unique_vips)

    # Find stimulus VIP (first non-register-bus VIP, or first VIP)
    stim_vip = next(
        (v for v in unique_vips if v.get("role","") in ("master","slave")),
        unique_vips[0] if unique_vips else {}
    )
    stim_vip_name = stim_vip.get("vip_name", "stim_vip")

    filepath = os.path.join(dv_root, "env", f"{proj}_ref_txn.sv")
    content = f"""\
// =============================================================================
// FILE: dv/env/{proj}_ref_txn.sv
// S8 auto-generated — {date.today().isoformat()}
// Predicted output transaction from ref model → scoreboard.
// ⚠️ NEEDS_ENGINEER_REVIEW: add fields matching response VIP seq_item
// =============================================================================
class {proj}_ref_txn extends uvm_sequence_item;
  `uvm_object_utils({proj}_ref_txn)

  // Source stimulus (for context in error messages)
  // {stim_vip_name}_seq_item stimulus;  // ⚠️ NEEDS_ENGINEER_REVIEW: uncomment

  // Predicted output fields — must match response VIP seq_item
  // ⚠️ NEEDS_ENGINEER_REVIEW: replace with actual DUT output fields
  rand logic [{dw-1}:0] data;
  rand logic [{aw-1}:0] addr;
  rand logic [1:0]       status;

  function new(string name = "{proj}_ref_txn");
    super.new(name);
  endfunction

  function string convert2string();
    return $sformatf("ref_txn: data=0x%0h addr=0x%0h status=0b%02b", data, addr, status);
  endfunction
endclass : {proj}_ref_txn
"""
    safe_write(filepath, content)
    return filepath


# ── Scoreboard generator ──────────────────────────────────────────────────────

def gen_scoreboard(proj, unique_vips, sb_checks, ral_info, sb_config, dv_root):
    style     = sb_config.get("style",   "in_order")
    trigger   = sb_config.get("trigger", "auto")
    ral_class = ral_info.get("reg_block_class", f"{proj}_reg_block")
    registers = ral_info.get("registers", [])

    # Identify register bus VIP
    reg_bus_vip = ral_info.get("register_bus_vip", "")

    # Separate VIPs into reg-bus and data-path
    reg_vips  = [v for v in unique_vips if v.get("vip_name") == reg_bus_vip]
    data_vips = [v for v in unique_vips if v.get("vip_name") != reg_bus_vip]

    # ── analysis_imp_decl macros ──────────────────────────────────────────────
    imp_decls = "\n".join(
        f"  `uvm_analysis_imp_decl(_{v.get('vip_name')})"
        for v in unique_vips
    ) + "\n  `uvm_analysis_imp_decl(_expected)"

    # ── analysis_imp handles ──────────────────────────────────────────────────
    imp_handles = "\n".join(
        f"  uvm_analysis_imp__{v.get('vip_name')} "
        f"#({v.get('vip_name')}_seq_item, {proj}_scoreboard) "
        f"m_{v.get('vip_name')}_imp;"
        for v in unique_vips
    )
    imp_handles += f"\n  uvm_analysis_imp__expected #({proj}_ref_txn, {proj}_scoreboard) m_expected_imp;"

    # ── transaction queues ────────────────────────────────────────────────────
    queues = "\n".join(
        f"  {v.get('vip_name')}_seq_item  m_{v.get('vip_name')}_q[$];"
        for v in data_vips
    )
    queues += f"\n  {proj}_ref_txn             m_expected_q[$];"

    # ── build_phase new() calls ───────────────────────────────────────────────
    build_news = "\n".join(
        f'    m_{v.get("vip_name")}_imp = new("m_{v.get("vip_name")}_imp", this);'
        for v in unique_vips
    )
    build_news += f'\n    m_expected_imp = new("m_expected_imp", this);'
    build_news += f'\n    m_cov_ap       = new("m_cov_ap",       this);'

    # ── write() functions per VIP ─────────────────────────────────────────────
    write_funcs = []

    # Register bus VIP write function
    for v in reg_vips:
        vn = v.get("vip_name")
        proto = v.get("protocol", "")
        # Detect read/write field name by protocol
        is_read_expr = "txn.pwrite == 1'b0" if "APB" in proto else \
                       "txn.hwrite == 1'b0" if "AHB" in proto else \
                       "txn.is_read()"
        write_expr   = "txn.pwrite == 1'b1" if "APB" in proto else \
                       "txn.hwrite == 1'b1" if "AHB" in proto else \
                       "txn.is_write()"
        rdata_field  = "txn.prdata" if "APB" in proto else \
                       "txn.hrdata" if "AHB" in proto else \
                       "txn.rdata"
        wdata_field  = "txn.pwdata" if "APB" in proto else \
                       "txn.hwdata" if "AHB" in proto else \
                       "txn.wdata"
        addr_field   = "txn.paddr" if "APB" in proto else \
                       "txn.haddr" if "AHB" in proto else \
                       "txn.addr"

        write_funcs.append(f"""\
  // ── Register bus: {vn} ────────────────────────────────────────────────────
  function void write_{vn}({vn}_seq_item txn);
    if (!m_sb_enabled) return;
    if ({is_read_expr}) begin
      // Register read: compare against RAL mirror
      uvm_reg        rg;
      uvm_reg_data_t mirror_val;
      rg = ral.default_map.get_reg_by_offset({addr_field});
      if (rg == null) begin
        `uvm_error(`gtn, $sformatf(
          "[FAIL] CHK_{ip_tag(proj)}_REG_UNKNOWN — no RAL register at addr 0x%0h",
          {addr_field}))
        m_fail_cnt["CHK_{ip_tag(proj)}_REG_UNKNOWN"]++;
      end else begin
        mirror_val = rg.get_mirrored_value();
        _chk_reg_read(rg.get_name(), {rdata_field}, mirror_val);
      end
    end else begin
      // Register write: update RAL mirror
      uvm_reg rg = ral.default_map.get_reg_by_offset({addr_field});
      if (rg != null)
        void'(rg.predict({wdata_field}, .kind(UVM_PREDICT_WRITE)));
    end
  endfunction
""")

    # Data-path VIP write functions
    trigger_str = "SB_TRIGGER_AUTO" if trigger == "auto" else "cfg.sb_trigger == SB_TRIGGER_AUTO"
    for v in data_vips:
        vn = v.get("vip_name")
        write_funcs.append(f"""\
  // ── Data VIP: {vn} ───────────────────────────────────────────────────────
  function void write_{vn}({vn}_seq_item txn);
    if (!m_sb_enabled) return;
    m_{vn}_q.push_back(txn);
    if (m_expected_q.size() > 0)
      _compare_{vn}(m_{vn}_q.pop_front(), m_expected_q.pop_front());
    else
      `uvm_warning(`gtn,
        "[WARN] {vn}: actual received but expected queue empty — ref model may be lagging")
  endfunction
""")

    # ── _compare_ tasks per data VIP ─────────────────────────────────────────
    compare_tasks = []
    for v in data_vips:
        vn = v.get("vip_name")
        dw = v.get("data_width", 32)
        compare_tasks.append(f"""\
  // ── Compare task: {vn} ───────────────────────────────────────────────────
  protected task _compare_{vn}({vn}_seq_item actual, {proj}_ref_txn expected);
    // ⚠️ NEEDS_ENGINEER_REVIEW: map actual seq_item fields to predicted fields
    // Default: compare first data_width bits
    logic [{dw-1}:0] act_data;
    logic [{dw-1}:0] exp_data;
    // TODO: extract correct fields from actual and expected  // ⚠️ NEEDS_ENGINEER_REVIEW
    // act_data = actual.data;
    // exp_data = expected.data;
    // _chk_data_compare(act_data, exp_data, "CHK_TODO", "{vn}");
    `uvm_info(`gtn, "[WARN] _compare_{vn}: implement comparison logic  // ⚠️ NEEDS_ENGINEER_REVIEW",
              UVM_MEDIUM)
  endtask
""")

    # ── check tasks from testplan ─────────────────────────────────────────────
    check_tasks = []
    check_tasks.append(f"""\
  // ── Generic data compare (called from _compare_* tasks) ──────────────────
  protected task _chk_data_compare(
    input logic [63:0] actual,
    input logic [63:0] expected,
    input string       chk_id,
    input string       context_info = ""
  );
    {proj}_sb_transaction sb_txn;
    m_total_checks++;
    if (actual === expected) begin
      m_pass_cnt[chk_id]++;
      `uvm_info(`gtn, $sformatf("[PASS] %s — act=0x%0h exp=0x%0h %s",
                                 chk_id, actual, expected, context_info), UVM_MEDIUM)
      sb_txn = {proj}_sb_transaction::type_id::create("sb_txn");
      sb_txn.chk_id       = chk_id;
      sb_txn.result       = SB_PASS;
      sb_txn.actual       = actual;
      sb_txn.expected     = expected;
      sb_txn.context_info = context_info;
      m_cov_ap.write(sb_txn);
    end else begin
      m_fail_cnt[chk_id]++;
      `uvm_error(`gtn, $sformatf("[FAIL] %s — act=0x%0h exp=0x%0h %s",
                                  chk_id, actual, expected, context_info))
    end
  endtask

  // ── RAL register read check ───────────────────────────────────────────────
  protected task _chk_reg_read(
    input string         reg_name,
    input uvm_reg_data_t actual,
    input uvm_reg_data_t expected
  );
    string chk_id = $sformatf("CHK_{ip_tag(proj)}_REG_%s_READ", reg_name.toupper());
    {proj}_sb_transaction sb_txn;
    m_total_checks++;
    if (actual === expected) begin
      m_pass_cnt[chk_id]++;
      `uvm_info(`gtn, $sformatf("[PASS] %s — reg=%s act=0x%0h exp=0x%0h (mirror)",
                                 chk_id, reg_name, actual, expected), UVM_MEDIUM)
      sb_txn = {proj}_sb_transaction::type_id::create("sb_txn");
      sb_txn.chk_id   = chk_id;
      sb_txn.feature  = "RAL_REG_CHECK";
      sb_txn.result   = SB_PASS;
      sb_txn.actual   = actual;
      sb_txn.expected = expected;
      m_cov_ap.write(sb_txn);
    end else begin
      m_fail_cnt[chk_id]++;
      `uvm_error(`gtn, $sformatf("[FAIL] %s — reg=%s act=0x%0h exp=0x%0h (mirror)",
                                  chk_id, reg_name, actual, expected))
    end
  endtask
""")

    # Per-CHK_ID check stubs from testplan
    for row in sb_checks:
        chk_id   = row.get("checker_id", "")
        feature  = row.get("feature", "")
        subfeat  = row.get("subfeature", "")
        brief    = row.get("brief_description", "")
        sections = parse_testcase_sections(row.get("testcase_description", ""))
        checks   = sections.get("Checks", "TODO")
        criteria = sections.get("Pass Criteria", "TODO")
        sani     = sanitize(chk_id or feature)

        check_tasks.append(f"""\
  // ── {chk_id} : {feature}/{subfeat} ──────────────────────────────────────
  // Brief  : {brief[:80]}
  // Checks : {checks[:80]}
  // Criteria: {criteria[:80]}
  task _chk_{sani}(
    input logic [63:0] actual,
    input logic [63:0] expected,
    input string       context_info = ""
  );
    // ⚠️ NEEDS_ENGINEER_REVIEW: set correct actual/expected extraction above
    _chk_data_compare(actual, expected, "{chk_id}", context_info);
  endtask
""")

    # ── check_all() task ──────────────────────────────────────────────────────
    check_all_drains = "\n".join(f"""\
    while (m_expected_q.size() > 0 && m_{v.get('vip_name')}_q.size() > 0)
      _compare_{v.get('vip_name')}(m_{v.get('vip_name')}_q.pop_front(), m_expected_q.pop_front());
    if (m_{v.get('vip_name')}_q.size() > 0)
      `uvm_error(`gtn, $sformatf("[FAIL] %0d unexpected {v.get('vip_name')} transactions (no prediction)",
                 m_{v.get('vip_name')}_q.size()));"""
        for v in data_vips
    ) if data_vips else "    // No data-path VIPs"

    # ── report_phase ──────────────────────────────────────────────────────────
    report_phase = f"""\
  function void report_phase(uvm_phase phase);
    int total_pass = 0, total_fail = 0;
    super.report_phase(phase);
    foreach (m_pass_cnt[id]) total_pass += m_pass_cnt[id];
    foreach (m_fail_cnt[id]) total_fail += m_fail_cnt[id];
    $display("");
    $display("============================================================");
    $display("  Scoreboard Report — {proj}  (time=%0t)", $time);
    $display("============================================================");
    $display("  %-2s %-44s %-8s %-8s", "  ", "CHK_ID", "PASS", "FAIL");
    $display("  %s", {{80{{"-"}}}});
    foreach (m_pass_cnt[id]) begin
      string status = (m_fail_cnt.exists(id) && m_fail_cnt[id] > 0) ? "x" : "v";
      $display("  %s %-42s %-8d %-8d",
               status, id, m_pass_cnt[id],
               m_fail_cnt.exists(id) ? m_fail_cnt[id] : 0);
    end
    $display("  %s", {{80{{"-"}}}});
    $display("  TOTAL: PASS=%-6d FAIL=%-6d  checks=%0d",
             total_pass, total_fail, m_total_checks);
    if (total_fail == 0)
      `uvm_info(`gtn, "[PASS] All scoreboard checks passed", UVM_NONE)
    else
      `uvm_error(`gtn, $sformatf("[FAIL] %0d scoreboard check(s) failed", total_fail))
  endfunction"""

    filepath = os.path.join(dv_root, "env", f"{proj}_scoreboard.sv")
    content = f"""\
// =============================================================================
// FILE: dv/env/{proj}_scoreboard.sv
// S8 auto-generated — {date.today().isoformat()}
// Style   : {style}
// Trigger : {trigger}
// =============================================================================
// Import sb_result_e from {proj}_sb_transaction.sv (compiled first)

class {proj}_scoreboard extends uvm_scoreboard;
  `uvm_component_utils({proj}_scoreboard)

  // ── Analysis imp declarations (one per VIP + expected) ───────────────────
{imp_decls}

  // ── Analysis import handles ───────────────────────────────────────────────
{imp_handles}

  // ── Analysis export → functional coverage model ──────────────────────────
  uvm_analysis_port #({proj}_sb_transaction) m_cov_ap;

  // ── Handles ───────────────────────────────────────────────────────────────
  {ral_class}   ral;
  {proj}_env_cfg cfg;

  // ── Transaction queues ────────────────────────────────────────────────────
{queues}

  // ── Check counters ────────────────────────────────────────────────────────
  int m_pass_cnt[string];
  int m_fail_cnt[string];
  int m_total_checks;

  // ── Scoreboard enable ─────────────────────────────────────────────────────
  bit m_sb_enabled = 1;

  // ─────────────────────────────────────────────────────────────────────────
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
{build_news}
  endfunction

  // ── write() — expected from ref model ─────────────────────────────────────
  function void write_expected({proj}_ref_txn txn);
    if (!m_sb_enabled) return;
    m_expected_q.push_back(txn);
  endfunction

  // ── write() functions per VIP monitor ────────────────────────────────────
{"".join(write_funcs)}
  // ── Compare tasks ─────────────────────────────────────────────────────────
{"".join(compare_tasks)}
  // ── Explicit check: call from vseq when trigger=explicit ─────────────────
  task check_all();
{check_all_drains}
    if (m_expected_q.size() > 0)
      `uvm_error(`gtn, $sformatf("[FAIL] %0d predictions never matched by DUT",
                 m_expected_q.size()));
  endtask

  // ── Internal check tasks ──────────────────────────────────────────────────
{"".join(check_tasks)}
  // ── report_phase ──────────────────────────────────────────────────────────
{report_phase}

endclass : {proj}_scoreboard
"""
    force_write(filepath, content)
    return filepath


# ── Reference model generator ─────────────────────────────────────────────────

def gen_ref_model(proj, unique_vips, ral_info, sb_config, dv_root):
    ral_class    = ral_info.get("reg_block_class", f"{proj}_reg_block")
    ref_type     = sb_config.get("ref_model_type", "sv_stub")
    has_dpi      = (ref_type == "dpi_c")
    dpi_fn       = sb_config.get("dpi_function", "c_predict")

    # Best guess for stimulus VIP (first non-reg-bus)
    reg_bus = ral_info.get("register_bus_vip", "")
    stim_vips = [v for v in unique_vips if v.get("vip_name") != reg_bus]
    stim_vip  = stim_vips[0] if stim_vips else (unique_vips[0] if unique_vips else {})
    sv_name   = stim_vip.get("vip_name", "stim_vip")

    dpi_block = ""
    if has_dpi:
        dpi_block = f"""\

  // ── DPI-C interface ────────────────────────────────────────────────────────
  import "DPI-C" function void {dpi_fn}(
    input  int unsigned data_in,
    output int unsigned data_out
    // ⚠️ NEEDS_ENGINEER_REVIEW: update signature to match C model
  );
"""

    filepath = os.path.join(dv_root, "env", f"{proj}_ref_model.sv")
    content = f"""\
// =============================================================================
// FILE: dv/env/{proj}_ref_model.sv
// S8 auto-generated — {date.today().isoformat()}
// Reference model: receives input stimulus → predicts DUT output → scoreboard
// ⚠️ NEEDS_ENGINEER_REVIEW: implement predict() with DUT behavioral model
// =============================================================================
class {proj}_ref_model extends uvm_component;
  `uvm_component_utils({proj}_ref_model)

  // ── Receive input from stimulus VIP monitor ───────────────────────────────
  uvm_analysis_imp #({sv_name}_seq_item, {proj}_ref_model) m_{sv_name}_imp;

  // ── Send predictions to scoreboard ────────────────────────────────────────
  uvm_analysis_port #({proj}_ref_txn) m_sb_ap;

  // ── DUT configuration handles ─────────────────────────────────────────────
  {ral_class}   ral;   // use ral.<reg>.get_mirrored_value() for config-dependent predict
  {proj}_env_cfg cfg;
{dpi_block}
  // ── Internal DUT model state ──────────────────────────────────────────────
  // ⚠️ NEEDS_ENGINEER_REVIEW: add state variables mirroring DUT internals
  // Examples:
  //   int unsigned m_byte_count;       // DUT byte counter
  //   logic [7:0]  m_fifo[$];          // DUT FIFO model
  //   typedef enum {{IDLE, ACTIVE}} fsm_e;
  //   fsm_e        m_state;            // DUT FSM mirror

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    m_{sv_name}_imp = new("m_{sv_name}_imp", this);
    m_sb_ap         = new("m_sb_ap",         this);
  endfunction

  // ── write() — called when stimulus VIP monitor observes a transaction ─────
  function void write({sv_name}_seq_item txn);
    predict(txn);
  endfunction

  // ── predict() — DUT behavioral model ──────────────────────────────────────
  // Steps:
  //   1. Read DUT config from RAL mirror (operating mode, enables, thresholds)
  //   2. Apply DUT transformation to input data
  //   3. Create {proj}_ref_txn with predicted output
  //   4. Send to scoreboard via m_sb_ap
  //
  // ⚠️ NEEDS_ENGINEER_REVIEW: replace TODO stubs with actual DUT logic
  protected function void predict({sv_name}_seq_item txn);
    {proj}_ref_txn pred;
    // uvm_reg_data_t ctrl_val;

    // Step 1: Read config from RAL mirror
    // ctrl_val = ral.<ctrl_reg>.get_mirrored_value();
    // ⚠️ NEEDS_ENGINEER_REVIEW: add register reads for each config field

    // Step 2: Compute prediction
    pred = {proj}_ref_txn::type_id::create("pred");

    // ⚠️ NEEDS_ENGINEER_REVIEW: implement DUT transform below
    // Common patterns:
    //   pred.data = txn.data;              // pass-through
    //   pred.data = txn.data ^ mask;       // bitwise transform
    //   pred.data = compute_crc(txn.data); // CRC/checksum
    //   m_fifo.push_back(txn.data);        // enqueue
    //   pred.data = m_fifo.pop_front();    // dequeue
{('    ' + dpi_fn + '(.data_in(txn.data), .data_out(pred.data));') if has_dpi else '    // pred.data = txn.data;  // ⚠️ NEEDS_ENGINEER_REVIEW'}

    // Step 3: Send prediction
    m_sb_ap.write(pred);
  endfunction

endclass : {proj}_ref_model
"""
    force_write(filepath, content)
    return filepath


# ── Functional coverage model ─────────────────────────────────────────────────

def gen_functional_coverage(proj, sb_checks, dv_root):
    # Unique features from checks
    features = list({sanitize(r.get("feature", "misc")): r for r in sb_checks}.keys())
    if not features:
        features = ["misc"]

    cg_blocks = []
    for feat in features:
        cg_blocks.append(f"""\
  covergroup cg_{feat} @(posedge cov_event_{feat});
    cp_result: coverpoint last_txn.result {{
      bins pass = {{SB_PASS}};
    }}
    // ⚠️ NEEDS_REVIEW: add data/mode coverpoints for feature '{feat}'
    // cp_data: coverpoint last_txn.actual[7:0];
  endgroup
  event cov_event_{feat};
""")

    route_cases = "\n".join(
        f'      "{feat}": -> cov_event_{feat};'
        for feat in features
    )

    report_lines = "\n".join(
        f'    `uvm_info(`gtn, $sformatf("[COV] cg_{feat} = %.1f%%", cg_{feat}.get_coverage()), UVM_NONE)'
        for feat in features
    )

    new_cgs = "\n".join(
        f"    cg_{feat} = new();"
        for feat in features
    )

    filepath = os.path.join(dv_root, "env", f"{proj}_functional_coverage.sv")
    content = f"""\
// =============================================================================
// FILE: dv/env/{proj}_functional_coverage.sv
// S8 auto-generated — {date.today().isoformat()}
// Receives PASSING transactions from scoreboard.m_cov_ap → samples coverage.
// This component is the ONLY place project-level functional coverage is sampled.
// Per-VIP protocol coverage lives in <vip>_coverage.sv (S5).
// ⚠️ NEEDS_REVIEW: add meaningful coverpoints per feature
// =============================================================================
class {proj}_functional_coverage extends uvm_subscriber #({proj}_sb_transaction);
  `uvm_component_utils({proj}_functional_coverage)

  {proj}_sb_transaction last_txn;
  bit                    cov_enabled = 1;

  // ── Covergroups (one per feature) ────────────────────────────────────────
{"".join(cg_blocks)}
  function new(string name, uvm_component parent);
    super.new(name, parent);
{new_cgs}
  endfunction

  // ── write() — called by scoreboard for every PASSING check ───────────────
  function void write({proj}_sb_transaction txn);
    if (!cov_enabled) return;
    last_txn = txn;
    case (txn.feature)
{route_cases}
      default: ; // unrecognised feature — no coverage sampled
    endcase
  endfunction

  function void report_phase(uvm_phase phase);
{report_lines}
  endfunction

endclass : {proj}_functional_coverage
"""
    safe_write(filepath, content)
    return filepath


# ── compile.f update ──────────────────────────────────────────────────────────

def update_compile_f(dv_root, proj):
    compile_f = os.path.join(dv_root, "compile.f")
    existing  = open(compile_f).read() if os.path.exists(compile_f) else ""
    files = [
        f"${{DV_ROOT}}/env/{proj}_sb_transaction.sv",
        f"${{DV_ROOT}}/env/{proj}_ref_txn.sv",
        f"${{DV_ROOT}}/env/{proj}_ref_model.sv",
        f"${{DV_ROOT}}/env/{proj}_scoreboard.sv",
        f"${{DV_ROOT}}/env/{proj}_functional_coverage.sv",
    ]
    new_lines = [f for f in files if f not in existing]
    if new_lines:
        with open(compile_f, "a") as f:
            f.write("\n// S8 scoreboard, ref model, coverage\n")
            f.write("\n".join(new_lines) + "\n")
        print(f"  [UPD]  {compile_f}")
    else:
        print(f"  [SKIP] {compile_f}  (entries present)")


# ── dv_scoreboard_data.json ───────────────────────────────────────────────────

def write_sb_data(proj, sb_checks, sb_config, sva_skipped, dv_root):
    checks_out = [
        {
            "chk_id":    r.get("checker_id", ""),
            "feature":   r.get("feature", ""),
            "type":      "data_compare",
            "task_name": f"_chk_{sanitize(r.get('checker_id', r.get('feature','')))}",
            "milestone": r.get("milestone", "DV-C"),
        }
        for r in sb_checks
    ]
    data = {
        "skill":   "dv-scoreboard",
        "version": "1.0",
        "project_name":   proj,
        "generated_date": date.today().isoformat(),
        "config":  sb_config,
        "checks":  checks_out,
        "files": {
            "scoreboard":     f"dv/env/{proj}_scoreboard.sv",
            "ref_model":      f"dv/env/{proj}_ref_model.sv",
            "ref_txn":        f"dv/env/{proj}_ref_txn.sv",
            "sb_transaction": f"dv/env/{proj}_sb_transaction.sv",
            "func_coverage":  f"dv/env/{proj}_functional_coverage.sv",
        },
        "summary": {
            "total_checks":        len(sb_checks),
            "skipped_in_sva":      len(sva_skipped),
            "needs_review_count":  len([r for r in sb_checks
                                        if not r.get("testcase_description","").strip()]),
        }
    }
    out = os.path.join(dv_root, "dv_scoreboard_data.json")
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [GEN]  {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="S8 dv-scoreboard generator")
    parser.add_argument("--input",  required=True, help="sb_input.json")
    parser.add_argument("--output", required=True, help="dv/ root")
    parser.add_argument("--force",  action="store_true",
                        help="Overwrite existing scoreboard/ref_model files")
    args = parser.parse_args()

    dv_root = os.path.abspath(args.output)
    with open(args.input) as f:
        input_data = json.load(f)

    tb_data      = input_data.get("tb_data", {})
    proj         = tb_data.get("project_name", input_data.get("project_name", "proj"))
    unique_vips  = tb_data.get("unique_vips", [])
    ral_info     = tb_data.get("ral", {})
    testplan_rows = input_data.get("testplan_rows", [])
    sb_config    = input_data.get("sb_config", {
        "style": "in_order", "trigger": "auto",
        "ref_model_type": "sv_stub", "skip_sva_duplicates": True
    })

    print(f"\n[S8] Generating scoreboard for project: {proj}")
    print(f"     VIPs: {len(unique_vips)}")

    sva_ids  = load_sva_chk_ids(dv_root)
    seq_ids  = load_seq_chk_ids(dv_root)
    skip_dup = sb_config.get("skip_sva_duplicates", True)
    sb_checks = get_sb_checks(testplan_rows, sva_ids, seq_ids, skip_dup)
    sva_skipped = [r for r in testplan_rows
                   if r.get("checker_id","") in sva_ids
                   and r.get("checker_type","") in ("Procedural","Both")]

    print(f"     Checks from testplan : {len(testplan_rows)}")
    print(f"     Skipped (in SVA)     : {len(sva_skipped)}")
    print(f"     Net SB checks        : {len(sb_checks)}")

    print("\n[SB Transaction]");  gen_sb_transaction(proj, dv_root)
    print("\n[Ref Transaction]");  gen_ref_txn(proj, unique_vips, dv_root)
    print("\n[Scoreboard]");       gen_scoreboard(proj, unique_vips, sb_checks, ral_info, sb_config, dv_root)
    print("\n[Reference Model]");  gen_ref_model(proj, unique_vips, ral_info, sb_config, dv_root)
    print("\n[Coverage Model]");   gen_functional_coverage(proj, sb_checks, dv_root)
    print("\n[compile.f]");        update_compile_f(dv_root, proj)
    print("\n[Metadata]");         write_sb_data(proj, sb_checks, sb_config, sva_skipped, dv_root)

    needs_review = len([r for r in sb_checks if not r.get("testcase_description","").strip()])
    print(f"""
============================================================
  DV Scoreboard — Complete  ({proj})
============================================================
  Style     : {sb_config.get('style','in_order')}
  Trigger   : {sb_config.get('trigger','auto')}
  Ref model : {sb_config.get('ref_model_type','sv_stub')}
  SB checks : {len(sb_checks)}  (skipped SVA: {len(sva_skipped)})
  Coverage  : {proj}_functional_coverage.sv (fed from SB pass events)
------------------------------------------------------------
  ⚠️  NEEDS_ENGINEER_REVIEW: {needs_review} items
     predict() in {proj}_ref_model.sv
     Compare logic in _compare_*() tasks
     grep -r "NEEDS_ENGINEER_REVIEW" {dv_root}/env
------------------------------------------------------------
  env.sv wiring required — see SKILL.md Step 9
------------------------------------------------------------
  Next step: /dv-regression (S9)
============================================================
""")


if __name__ == "__main__":
    main()
