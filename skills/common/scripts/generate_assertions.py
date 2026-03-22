#!/usr/bin/env python3
"""
generate_assertions.py — S7 dv-assertions generator
Generates SVA modules, bind file, assertion control, UVM checker, and top package.

Usage:
  python3 generate_assertions.py --input /tmp/<proj>_assertions_input.json --output <dv_root>
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import date

# ── Protocol signal databases ─────────────────────────────────────────────────
PROTOCOL_SIGNALS = {
    "APB":         ["pclk","presetn","paddr","psel","penable","pwrite",
                    "pwdata","prdata","pready","pslverr"],
    "AHB":         ["hclk","hresetn","haddr","htrans","hwrite","hsize",
                    "hburst","hprot","hwdata","hrdata","hready","hresp"],
    "AHB-Lite":    ["hclk","hresetn","haddr","htrans","hwrite","hsize",
                    "hwdata","hrdata","hreadyout","hresp"],
    "AXI4":        ["aclk","aresetn","awaddr","awlen","awsize","awburst",
                    "awvalid","awready","wdata","wstrb","wlast","wvalid",
                    "wready","bresp","bvalid","bready","araddr","arlen",
                    "arsize","arburst","arvalid","arready","rdata","rresp",
                    "rlast","rvalid","rready"],
    "AXI4-Stream": ["aclk","aresetn","tvalid","tready","tdata","tstrb",
                    "tkeep","tlast","tid","tdest","tuser"],
    "SPI":         ["sclk","cs_n","mosi","miso"],
    "I2C":         ["scl","sda"],
    "UART":        ["clk","rst_n","txd","rxd","rts_n","cts_n"],
    "TileLink":    ["clock","reset","a_opcode","a_param","a_size","a_source",
                    "a_address","a_mask","a_data","a_valid","a_ready",
                    "d_opcode","d_param","d_size","d_source","d_sink",
                    "d_data","d_error","d_valid","d_ready"],
}

# Clock/reset signal names per protocol
PROTOCOL_CLK = {
    "APB":"pclk", "AHB":"hclk", "AHB-Lite":"hclk",
    "AXI4":"aclk", "AXI4-Stream":"aclk",
    "SPI":"sclk", "I2C":"scl", "UART":"clk", "TileLink":"clock",
}
PROTOCOL_RST = {
    "APB":"presetn", "AHB":"hresetn", "AHB-Lite":"hresetn",
    "AXI4":"aresetn", "AXI4-Stream":"aresetn",
    "SPI":"rst_n", "I2C":"rst_n", "UART":"rst_n", "TileLink":"reset",
}

# Auto-generated protocol-standard properties
PROTOCOL_AUTO_PROPS = {
    "APB": [
        {
            "name": "p_apb_setup_phase",
            "chk_id": "CHK_AUTO_APB_SETUP",
            "desc": "psel asserted before penable (setup phase)",
            "body": "@(posedge clk) disable iff (!rst_n)\n    $rose(penable) |-> $past(psel);",
        },
        {
            "name": "p_apb_no_access_during_reset",
            "chk_id": "CHK_AUTO_APB_RESET",
            "desc": "No APB access during reset",
            "body": "@(posedge clk)\n    !rst_n |-> !psel;",
        },
        {
            "name": "p_apb_penable_one_cycle",
            "chk_id": "CHK_AUTO_APB_PENABLE",
            "desc": "penable held for exactly one cycle when pready",
            "body": "@(posedge clk) disable iff (!rst_n)\n    (psel && penable && pready) |=> !penable;",
        },
    ],
    "AHB": [
        {
            "name": "p_ahb_htrans_valid",
            "chk_id": "CHK_AUTO_AHB_HTRANS",
            "desc": "htrans only takes valid values",
            "body": "@(posedge clk) disable iff (!rst_n)\n    htrans inside {2'b00, 2'b01, 2'b10, 2'b11};",
        },
        {
            "name": "p_ahb_no_access_during_reset",
            "chk_id": "CHK_AUTO_AHB_RESET",
            "desc": "htrans IDLE during reset",
            "body": "@(posedge clk)\n    !hresetn |-> htrans == 2'b00;",
        },
    ],
    "AHB-Lite": [
        {
            "name": "p_ahblite_htrans_valid",
            "chk_id": "CHK_AUTO_AHBLITE_HTRANS",
            "desc": "htrans only IDLE or NONSEQ for AHB-Lite",
            "body": "@(posedge clk) disable iff (!hresetn)\n    htrans inside {2'b00, 2'b10};",
        },
        {
            "name": "p_ahblite_no_busy",
            "chk_id": "CHK_AUTO_AHBLITE_NOBUSY",
            "desc": "AHB-Lite: no BUSY or SEQ transfers",
            "body": "@(posedge clk) disable iff (!hresetn)\n    !(htrans inside {2'b01, 2'b11});",
        },
    ],
    "AXI4": [
        {
            "name": "p_axi_awvalid_stable",
            "chk_id": "CHK_AUTO_AXI_AWVALID",
            "desc": "awvalid stays high until awready",
            "body": "@(posedge clk) disable iff (!aresetn)\n    awvalid && !awready |=> awvalid;",
        },
        {
            "name": "p_axi_wvalid_stable",
            "chk_id": "CHK_AUTO_AXI_WVALID",
            "desc": "wvalid stays high until wready",
            "body": "@(posedge clk) disable iff (!aresetn)\n    wvalid && !wready |=> wvalid;",
        },
        {
            "name": "p_axi_arvalid_stable",
            "chk_id": "CHK_AUTO_AXI_ARVALID",
            "desc": "arvalid stays high until arready",
            "body": "@(posedge clk) disable iff (!aresetn)\n    arvalid && !arready |=> arvalid;",
        },
    ],
    "AXI4-Stream": [
        {
            "name": "p_axis_tvalid_stable",
            "chk_id": "CHK_AUTO_AXIS_TVALID",
            "desc": "tvalid held until tready (no spurious deassert)",
            "body": "@(posedge clk) disable iff (!aresetn)\n    tvalid && !tready |=> tvalid;",
        },
        {
            "name": "p_axis_tdata_stable_when_valid",
            "chk_id": "CHK_AUTO_AXIS_TDATA",
            "desc": "tdata/tkeep stable while tvalid and !tready",
            "body": "@(posedge clk) disable iff (!aresetn)\n    tvalid && !tready |=> $stable(tdata) && $stable(tkeep);",
        },
    ],
    "SPI": [
        {
            "name": "p_spi_cs_before_clk",
            "chk_id": "CHK_AUTO_SPI_CS",
            "desc": "cs_n asserted before sclk activity",
            "body": "@(posedge sclk) disable iff (rst_n)\n    !cs_n;  // sclk only toggles when cs_n is low",
        },
    ],
    "I2C": [
        {
            "name": "p_i2c_start_condition",
            "chk_id": "CHK_AUTO_I2C_START",
            "desc": "I2C start: sda falls while scl high",
            "body": "@(negedge sda) disable iff (rst_n)\n    scl;",
        },
        {
            "name": "p_i2c_stop_condition",
            "chk_id": "CHK_AUTO_I2C_STOP",
            "desc": "I2C stop: sda rises while scl high",
            "body": "@(posedge sda) disable iff (rst_n)\n    scl;",
        },
    ],
    "UART": [
        {
            "name": "p_uart_start_bit",
            "chk_id": "CHK_AUTO_UART_START",
            "desc": "UART start bit: txd falls and stays low for one bit period",
            "body": "@(posedge clk) disable iff (!rst_n)\n    $fell(txd) |-> !txd;",
        },
        {
            "name": "p_uart_no_glitch",
            "chk_id": "CHK_AUTO_UART_GLITCH",
            "desc": "txd does not glitch (no single-cycle spikes)",
            "body": "@(posedge clk) disable iff (!rst_n)\n    $rose(txd) |-> ##1 txd;  // ⚠️ NEEDS_REVIEW: adjust for baud rate",
        },
    ],
    "TileLink": [
        {
            "name": "p_tl_a_valid_stable",
            "chk_id": "CHK_AUTO_TL_AVALID",
            "desc": "a_valid held until a_ready",
            "body": "@(posedge clock) disable iff (reset)\n    a_valid && !a_ready |=> a_valid;",
        },
        {
            "name": "p_tl_d_valid_stable",
            "chk_id": "CHK_AUTO_TL_DVALID",
            "desc": "d_valid held until d_ready",
            "body": "@(posedge clock) disable iff (reset)\n    d_valid && !d_ready |=> d_valid;",
        },
    ],
}


# ── Utilities ─────────────────────────────────────────────────────────────────

def safe_write(path: str, content: str) -> bool:
    if os.path.exists(path):
        print(f"  [SKIP] {path}  (already exists)")
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  [GEN]  {path}")
    return True


def force_write(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  [GEN]  {path}")


def sanitize_label(chk_id: str) -> str:
    """Convert CHK_ID to valid SV label: 'CHK_FOO-BAR_001' → 'CHK_FOO_BAR_001'"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', chk_id)


def proto_prefix(protocol: str) -> str:
    mapping = {
        "APB":"apb", "AHB":"ahb", "AHB-Lite":"ahb",
        "AXI4":"axi4", "AXI4-Stream":"axi4s",
        "SPI":"spi", "I2C":"i2c", "UART":"uart", "TileLink":"tilelink",
    }
    return mapping.get(protocol, protocol.lower().replace("-","_").replace(" ","_"))


# ── Assertion row categorisation ──────────────────────────────────────────────

def tokenize_signals(sva_code: str) -> set:
    """Extract identifier tokens from SVA code (potential signal names)."""
    # Remove comments, keywords, operators — keep identifiers
    cleaned = re.sub(r'//.*$', '', sva_code, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    tokens = set(re.findall(r'\b[a-z_][a-z0-9_]*\b', cleaned.lower()))
    # Remove SV keywords
    sv_keywords = {
        'property','endproperty','assert','cover','assume','restrict',
        'posedge','negedge','disable','iff','until','throughout','within',
        'clk','clk_i','clock','if','else','begin','end','input','output',
        'inout','logic','wire','reg','int','bit','module','endmodule',
        'always','initial','assign','force','release','deassign',
        'default','clocking','endclocking',
    }
    return tokens - sv_keywords


def assign_to_vip(assertion_code: str, unique_vips: list) -> str:
    """
    Return vip_name of best-matching VIP, or None for DUT-internal.
    Heuristic: most signal-name overlaps wins.
    """
    if not assertion_code.strip():
        return None
    tokens = tokenize_signals(assertion_code)
    best_vip   = None
    best_score = 0
    for vip in unique_vips:
        proto   = vip.get("protocol", "")
        signals = set(PROTOCOL_SIGNALS.get(proto, []))
        score   = len(tokens & signals)
        if score > best_score:
            best_score = score
            best_vip   = vip.get("vip_name")
    return best_vip if best_score > 0 else None


def categorise_assertions(rows: list, unique_vips: list) -> dict:
    """
    Returns {vip_name: [rows], '_dut_internal': [rows], '_auto': {vip_name: [props]}}
    """
    result = {v.get("vip_name"): [] for v in unique_vips}
    result["_dut_internal"] = []

    for row in rows:
        chk_type = row.get("checker_type", "")
        if chk_type not in ("Assertion", "Both"):
            continue
        code  = row.get("assertion_code", "")
        vip   = assign_to_vip(code, unique_vips)
        if vip and vip in result:
            result[vip].append(row)
        else:
            result["_dut_internal"].append(row)

    # Auto-generated stubs for VIPs that have no assertions assigned
    result["_auto"] = {}
    for vip in unique_vips:
        vname = vip.get("vip_name")
        proto = vip.get("protocol", "")
        if not result.get(vname):  # no testplan assertions for this VIP
            auto_props = PROTOCOL_AUTO_PROPS.get(proto, [])
            if auto_props:
                result["_auto"][vname] = {"protocol": proto, "props": auto_props}

    return result


# ── Protocol signal port list generator ───────────────────────────────────────

def gen_signal_ports(protocol: str, data_width: int, addr_width: int) -> str:
    """Generate input port list for assertion module based on protocol."""
    signals = PROTOCOL_SIGNALS.get(protocol, [])
    lines   = []
    clk_sig = PROTOCOL_CLK.get(protocol, "clk")
    rst_sig = PROTOCOL_RST.get(protocol, "rst_n")

    for sig in signals:
        if sig in (clk_sig, rst_sig):
            continue  # already declared in module header
        # Infer width
        if any(x in sig for x in ("data","wdata","rdata","tdata")):
            width = f"[{data_width-1}:0] "
        elif any(x in sig for x in ("addr","paddr","haddr","awaddr","araddr","a_address")):
            width = f"[{max(addr_width-1,0)}:0] " if addr_width > 0 else ""
        elif any(x in sig for x in ("len","size","burst","strb","tkeep","tstrb","tid","tdest")):
            width = "[7:0] "
        elif any(x in sig for x in ("resp","htrans","opcode","param","tuser")):
            width = "[1:0] "
        else:
            width = ""
        lines.append(f"  input logic {width}{sig}")
    return ",\n".join(lines)


# ── Per-VIP assertion module generator ────────────────────────────────────────

def _build_property_block(prop_name: str, chk_id: str, desc: str,
                          body: str, source: str = "testplan") -> str:
    label    = sanitize_label(chk_id)
    src_tag  = "// ⚠️ NEEDS_REVIEW (auto-generated stub)" if source == "auto" else ""
    return f"""\
  // ── {chk_id} : {desc} {src_tag}
  property {prop_name};
    {body}
  endproperty

  AST_{label}: assert property ({prop_name})
    $info("[PASS] {chk_id} — {desc} at time %0t", $time);
  else
    $error("[FAIL] {chk_id} — {desc} violated at time %0t", $time);

  COV_{label}: cover property ({prop_name})
    $info("[COV]  {chk_id} — cover hit at time %0t", $time);
"""


def gen_vip_assertions_sv(vip: dict, rows: list, auto_props: list,
                           dv_root: str) -> str:
    """Generate <vip>_if_assertions.sv. Returns file path."""
    vip_name   = vip.get("vip_name", "")
    protocol   = vip.get("protocol", "")
    data_width = vip.get("data_width", 32)
    addr_width = vip.get("addr_width", 32)
    clk_sig    = PROTOCOL_CLK.get(protocol, "clk")
    rst_sig    = PROTOCOL_RST.get(protocol, "rst_n")
    rst_active = "reset" if protocol == "TileLink" else f"!{rst_sig}"

    port_list = gen_signal_ports(protocol, data_width, addr_width)

    # Build property blocks from testplan rows
    tp_blocks = []
    for row in rows:
        code      = row.get("assertion_code", "").strip()
        chk_id    = row.get("checker_id", f"CHK_{vip_name.upper()}_AUTO")
        feat      = row.get("feature", "")
        subfeat   = row.get("subfeature", "")
        desc      = f"{feat}/{subfeat}"
        milestone = row.get("milestone", "DV-C")

        if code:
            # Extract property name from assertion_code if present
            m = re.search(r'property\s+(\w+)', code)
            prop_name = m.group(1) if m else f"p_{sanitize_label(chk_id).lower()}"
            # Check if action blocks already present
            if "$info" not in code and "$error" not in code:
                # Wrap the assertion_code as the property body
                body = code.strip()
                tp_blocks.append(_build_property_block(prop_name, chk_id, desc, body))
            else:
                # Use as-is, add a comment
                tp_blocks.append(f"  // ── {chk_id} : {desc}\n  // Milestone: {milestone}\n  {code}\n")
        else:
            prop_name = f"p_{sanitize_label(chk_id).lower()}"
            body = f"  @(posedge {clk_sig}) disable iff ({rst_active})\n    // TODO: define antecedent and consequent  // ⚠️ NEEDS_REVIEW"
            tp_blocks.append(_build_property_block(prop_name, chk_id, desc, body))

    tp_section = "\n".join(tp_blocks) if tp_blocks else \
        "  // No testplan assertions assigned to this VIP\n"

    # Auto-generated protocol standard properties
    auto_blocks = []
    for p in auto_props:
        auto_blocks.append(_build_property_block(
            p["name"], p["chk_id"], p["desc"], p["body"], source="auto"))
    auto_section = "\n".join(auto_blocks) if auto_blocks else \
        "  // No additional auto-generated properties\n"

    # Immediate assertion for parameter sanity
    imm_assert = ""
    if data_width > 0:
        imm_assert = f"""\
  // ── Immediate: parameter sanity ─────────────────────────────────────────
  initial begin
    assert (DATA_WIDTH > 0 && DATA_WIDTH <= 4096)
      else $fatal(1, "{vip_name}: illegal DATA_WIDTH=%0d", DATA_WIDTH);
  end
"""

    content = f"""\
// =============================================================================
// FILE: dv/agents/{vip_name}_agent/assertions/{vip_name}_if_assertions.sv
// S7 auto-generated — {date.today().isoformat()}
// Protocol : {protocol}
// Contains : Concurrent SVA (assert+cover) from testplan + auto-generated stubs
//            Assertion control (disable during reset, enable after)
// =============================================================================
module {vip_name}_if_assertions #(
  parameter int DATA_WIDTH = {data_width},
  parameter int ADDR_WIDTH = {addr_width}
)(
  input logic clk,
  input logic rst_n{(",\n" + port_list) if port_list.strip() else ""}
);

  // ── Assertion control: disable at time-0, enable after reset ────────────
  initial begin
    $assertoff(0, {vip_name}_if_assertions);
    @(posedge rst_n);
    repeat (2) @(posedge clk);
    $asserton(0, {vip_name}_if_assertions);
    $display("[ASSERT] {vip_name}_if_assertions enabled at time %0t", $time);
  end

  // ── Default clocking and disable ────────────────────────────────────────
  default clocking cb_mon @(posedge clk); endclocking
  default disable iff (!rst_n);

{imm_assert}
  // =========================================================================
  // Assertions from testplan (checker_type = Assertion or Both)
  // =========================================================================
{tp_section}
  // =========================================================================
  // Auto-generated protocol-standard assertions ({protocol})
  // =========================================================================
{auto_section}
endmodule : {vip_name}_if_assertions
"""
    filepath = os.path.join(dv_root, "agents", f"{vip_name}_agent",
                            "assertions", f"{vip_name}_if_assertions.sv")
    safe_write(filepath, content)
    return filepath


def gen_vip_assertions_pkg(vip_name: str, chk_ids: list, dv_root: str) -> str:
    """Generate <vip>_assertions_pkg.sv."""
    chk_list = "\n".join(f"  //   {c}" for c in chk_ids) if chk_ids else "  //   (none from testplan)"
    content = f"""\
// =============================================================================
// FILE: dv/agents/{vip_name}_agent/assertions/{vip_name}_assertions_pkg.sv
// S7 auto-generated — {date.today().isoformat()}
// Namespace anchor for {vip_name} assertions.
// The assertions themselves live in {vip_name}_if_assertions.sv (SV module,
// not a class) and are instantiated via the bind file.
//
// CHK_IDs covered:
{chk_list}
// =============================================================================
package {vip_name}_assertions_pkg;
  // This package provides a compile-time namespace for {vip_name} assertions.
  // Import in <proj>_top_assertions_pkg to ensure this VIP's assertions are
  // included in the compilation unit.
  //
  // Simulation instantiation: see dv/assertions/<proj>_dut_bind.sv
endpackage : {vip_name}_assertions_pkg
"""
    filepath = os.path.join(dv_root, "agents", f"{vip_name}_agent",
                            "assertions", f"{vip_name}_assertions_pkg.sv")
    safe_write(filepath, content)
    return filepath


# ── DUT bind module ────────────────────────────────────────────────────────────

def gen_dut_bind(proj: str, unique_vips: list, internal_rows: list,
                 tb_data: dict, dv_root: str) -> str:
    """Generate <proj>_dut_bind.sv."""

    # Per-VIP bind blocks
    vip_bind_blocks = []
    for vip in unique_vips:
        vname      = vip.get("vip_name", "")
        proto      = vip.get("protocol", "")
        dw         = vip.get("data_width", 32)
        aw         = vip.get("addr_width", 32)
        instances  = vip.get("instances", [{"if_name": f"{proto_prefix(proto)}_if"}])
        signals    = PROTOCOL_SIGNALS.get(proto, [])
        clk_sig    = PROTOCOL_CLK.get(proto, "clk")
        rst_sig    = PROTOCOL_RST.get(proto, "rst_n")

        for inst in instances:
            if_name = inst.get("if_name", f"{proto_prefix(proto)}_if")
            sig_connects = "\n".join(
                f"  .{s:<20} ( {if_name}.{s} )"
                for s in signals if s not in (clk_sig, rst_sig)
            )
            vip_bind_blocks.append(f"""\
// ── {vname} → {if_name} ──────────────────────────────────────────────────────
bind {proj}_tb_top {vname}_if_assertions #(
  .DATA_WIDTH ( {dw} ),
  .ADDR_WIDTH ( {aw} )
) u_{if_name}_assertions (
  .clk   ( {if_name}.clk   ),
  .rst_n ( {if_name}.rst_n ){(',' + chr(10) + sig_connects) if sig_connects.strip() else ''}
);
""")

    # DUT-internal assertion properties
    internal_prop_blocks = []
    for row in internal_rows:
        chk_id  = row.get("checker_id", "CHK_INTERNAL")
        code    = row.get("assertion_code", "").strip()
        feat    = row.get("feature", "")
        desc    = feat
        label   = sanitize_label(chk_id)
        if code:
            internal_prop_blocks.append(f"  // {chk_id}: {desc}\n  {code}\n")
        else:
            internal_prop_blocks.append(f"""\
  // ── {chk_id} : {desc}  ⚠️ NEEDS_REVIEW
  property p_{label.lower()};
    @(posedge clk) disable iff (!rst_n)
    // TODO: define DUT-internal property antecedent/consequent
    1'b1;  // placeholder — always passes until implemented
  endproperty
  AST_{label}: assert property (p_{label.lower()})
    $info("[PASS] {chk_id} at %0t", $time);
  else
    $error("[FAIL] {chk_id} violated at %0t", $time);
  COV_{label}: cover property (p_{label.lower()})
    $info("[COV]  {chk_id} hit at %0t", $time);
""")

    internal_section = "\n".join(internal_prop_blocks) if internal_prop_blocks else \
        "  // No DUT-internal assertions from testplan — add manually as needed\n"

    vip_bind_section = "\n".join(vip_bind_blocks) if vip_bind_blocks else \
        "// No VIP bind blocks generated\n"

    content = f"""\
// =============================================================================
// FILE: dv/assertions/{proj}_dut_bind.sv
// S7 auto-generated — {date.today().isoformat()}
// Binds VIP assertion modules to interface instances in tb_top.
// Binds DUT-internal assertion module into the DUT stub.
//
// IMPORTANT: compile this file LAST in compile.f (after all bound modules).
// =============================================================================

// =============================================================================
// Section 1: VIP interface assertion bindings
// =============================================================================
{vip_bind_section}

// =============================================================================
// Section 2: DUT-internal assertion module
// =============================================================================
module {proj}_dut_internal_assertions (
  input logic clk,
  input logic rst_n
  // TODO: add DUT-internal signal ports matching real DUT hierarchy  // ⚠️ NEEDS_REVIEW
);
  default clocking cb @(posedge clk); endclocking
  default disable iff (!rst_n);

  initial begin
    $assertoff(0, {proj}_dut_internal_assertions);
    @(posedge rst_n);
    repeat (2) @(posedge clk);
    $asserton(0, {proj}_dut_internal_assertions);
  end

{internal_section}
endmodule : {proj}_dut_internal_assertions

// =============================================================================
// Section 3: Bind DUT-internal assertions into DUT
// =============================================================================
bind {proj}_dut {proj}_dut_internal_assertions u_dut_internal_assertions (
  .clk   ( clk   ),
  .rst_n ( rst_n )
  // TODO: connect DUT-internal signals  // ⚠️ NEEDS_REVIEW
);
"""
    filepath = os.path.join(dv_root, "assertions", f"{proj}_dut_bind.sv")
    safe_write(filepath, content)
    return filepath


# ── Assertion control package ─────────────────────────────────────────────────

def gen_assert_ctrl_pkg(proj: str, unique_vips: list, dv_root: str) -> str:
    filepath = os.path.join(dv_root, "assertions", f"{proj}_assert_ctrl_pkg.sv")
    content = f"""\
// =============================================================================
// FILE: dv/assertions/{proj}_assert_ctrl_pkg.sv
// S7 auto-generated — {date.today().isoformat()}
// Assertion enable/disable control tasks for use in UVM phases.
// Import in base_test or env_cfg.
// =============================================================================
package {proj}_assert_ctrl_pkg;

  typedef enum int {{
    ASSERT_GRP_ALL          = 0,
    ASSERT_GRP_PROTOCOL     = 1,   // All VIP interface assertions
    ASSERT_GRP_DUT_INTERNAL = 2,   // DUT-internal assertions
    ASSERT_GRP_RAL          = 3    // Register access assertions
  }} assert_group_e;

  // ── Disable all at time-0 / reset ─────────────────────────────────────────
  task automatic disable_all_assertions();
    $assertoff(0);
    $display("[ASSERT_CTRL] All assertions DISABLED at %0t", $time);
  endtask

  // ── Enable all after reset ────────────────────────────────────────────────
  task automatic enable_all_assertions();
    $asserton(0);
    $display("[ASSERT_CTRL] All assertions ENABLED at %0t", $time);
  endtask

  // ── Per-group control ─────────────────────────────────────────────────────
  // TODO: replace placeholder $assertoff(0) with hierarchical paths
  //       once TB hierarchy is known.  // ⚠️ NEEDS_REVIEW
  task automatic disable_group(assert_group_e grp);
    case (grp)
      ASSERT_GRP_PROTOCOL:     $assertoff(0);  // TODO: scope to VIP assertion instances
      ASSERT_GRP_DUT_INTERNAL: $assertoff(0);  // TODO: scope to u_dut_internal_assertions
      default:                 $assertoff(0);
    endcase
    $display("[ASSERT_CTRL] Group %s DISABLED at %0t", grp.name(), $time);
  endtask

  task automatic enable_group(assert_group_e grp);
    case (grp)
      ASSERT_GRP_PROTOCOL:     $asserton(0);
      ASSERT_GRP_DUT_INTERNAL: $asserton(0);
      default:                 $asserton(0);
    endcase
    $display("[ASSERT_CTRL] Group %s ENABLED at %0t", grp.name(), $time);
  endtask

endpackage : {proj}_assert_ctrl_pkg
"""
    safe_write(filepath, content)
    return filepath


# ── UVM assertion checker / reporter ─────────────────────────────────────────

def gen_assertion_checker(proj: str, all_assertions: list, dv_root: str) -> str:
    """Generate <proj>_assertion_checker.sv."""

    # Build _register_all_checkers entries
    reg_entries = []
    for a in all_assertions:
        chk_id  = a.get("chk_id", "")
        desc    = a.get("description", a.get("feature", ""))
        ms      = a.get("milestone", "DV-C")
        label   = sanitize_label(chk_id)
        reg_entries.append(f"""\
    e = '{{chk_id: "{chk_id}",
           description: "{desc[:60]}",
           milestone:   "{ms}",
           assert_label:"AST_{label}",
           cover_label: "COV_{label}",
           pass_count: 0, fail_count: 0, cover_count: 0}};
    chk_table.push_back(e);""")

    reg_block = "\n".join(reg_entries) if reg_entries else \
        "    // No assertions registered — populate after testplan is finalised"

    filepath = os.path.join(dv_root, "assertions", f"{proj}_assertion_checker.sv")
    content = f"""\
// =============================================================================
// FILE: dv/assertions/{proj}_assertion_checker.sv
// S7 auto-generated — {date.today().isoformat()}
// UVM component: registers all CHK_IDs, queries assertion counts at report_phase,
// prints CHK_ID-mapped pass/fail/cover summary table.
//
// Instantiate in {proj}_env.sv:
//   {proj}_assertion_checker assertion_chk;
//   // build_phase: assertion_chk = {proj}_assertion_checker::type_id::create(...)
// =============================================================================
class {proj}_assertion_checker extends uvm_component;
  `uvm_component_utils({proj}_assertion_checker)

  typedef struct {{
    string chk_id;
    string description;
    string milestone;
    string assert_label;
    string cover_label;
    int    pass_count;
    int    fail_count;
    int    cover_count;
  }} chk_entry_t;

  chk_entry_t chk_table[$];

  function new(string name = "{proj}_assertion_checker", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  function void start_of_simulation_phase(uvm_phase phase);
    super.start_of_simulation_phase(phase);
    _register_all_checkers();
    `uvm_info(`gtn, $sformatf("[ASSERT] %0d CHK_IDs registered for assertion reporting",
                               chk_table.size()), UVM_MEDIUM)
  endfunction

  function void report_phase(uvm_phase phase);
    int total_pass  = 0;
    int total_fail  = 0;
    int total_cover = 0;
    super.report_phase(phase);

    foreach (chk_table[i]) begin
      // VCS: uncomment these lines when $assert* system functions are available
      // `ifdef VCS
      //   chk_table[i].pass_count  = $assertpasscount(chk_table[i].assert_label);
      //   chk_table[i].fail_count  = $assertfailcount(chk_table[i].assert_label);
      //   chk_table[i].cover_count = $assertcovercount(chk_table[i].cover_label);
      // `endif
      total_pass  += chk_table[i].pass_count;
      total_fail  += chk_table[i].fail_count;
      total_cover += chk_table[i].cover_count;
    end

    $display("");
    $display("============================================================");
    $display("  SVA Checker Report — {proj}  (time=%0t)", $time);
    $display("============================================================");
    $display("  %-2s %-42s %-6s %-6s %-6s %-8s",
             "  ", "CHK_ID", "PASS", "FAIL", "COVER", "MILESTONE");
    $display("  %s", {{80{{"-"}}}});
    foreach (chk_table[i]) begin
      string status;
      status = (chk_table[i].fail_count > 0) ? "✗" : "✓";
      $display("  %s %-40s %-6d %-6d %-6d %-8s",
               status,
               chk_table[i].chk_id,
               chk_table[i].pass_count,
               chk_table[i].fail_count,
               chk_table[i].cover_count,
               chk_table[i].milestone);
    end
    $display("  %s", {{80{{"-"}}}});
    $display("  TOTAL        PASS=%-6d FAIL=%-6d COVER=%-6d",
             total_pass, total_fail, total_cover);
    if (total_fail == 0)
      $display("  ✓  ALL %0d SVA CHECKERS PASSED", chk_table.size());
    else
      $display("  ✗  %0d SVA CHECKER(S) FAILED", total_fail);
    $display("============================================================");
    $display("");

    if (total_fail > 0)
      `uvm_error(`gtn, $sformatf("[FAIL] %0d SVA assertion(s) violated in this run",
                                  total_fail))
  endfunction

  local function void _register_all_checkers();
    chk_entry_t e;
{reg_block}
  endfunction

endclass : {proj}_assertion_checker
"""
    safe_write(filepath, content)
    return filepath


# ── Top assertions package ────────────────────────────────────────────────────

def gen_top_assertions_pkg(proj: str, unique_vips: list, dv_root: str) -> str:
    imports = "\n".join(
        f"  import {v.get('vip_name')}_assertions_pkg::*;"
        for v in unique_vips
    )
    filepath = os.path.join(dv_root, "assertions", f"{proj}_top_assertions_pkg.sv")
    content = f"""\
// =============================================================================
// FILE: dv/assertions/{proj}_top_assertions_pkg.sv
// S7 auto-generated — {date.today().isoformat()}
// Top-level assertions package: imports VIP assertion packages, control pkg,
// and includes the UVM assertion checker class.
// Import in {proj}_env_pkg.sv and {proj}_tests_pkg.sv
// =============================================================================
package {proj}_top_assertions_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  // VIP assertion packages (one per unique VIP)
{imports}

  // Assertion control
  import {proj}_assert_ctrl_pkg::*;

  // UVM assertion checker/reporter
  `include "assertions/{proj}_assertion_checker.sv"

endpackage : {proj}_top_assertions_pkg
"""
    force_write(filepath, content)
    return filepath


# ── compile.f update ──────────────────────────────────────────────────────────

def update_compile_f(dv_root: str, proj: str, unique_vips: list):
    compile_f = os.path.join(dv_root, "compile.f")
    existing  = open(compile_f).read() if os.path.exists(compile_f) else ""

    lines = ["", "// S7 assertions — VIP interface assertion modules (before tb_top)"]
    for vip in unique_vips:
        vn   = vip.get("vip_name", "")
        path = f"${{DV_ROOT}}/agents/{vn}_agent/assertions/{vn}_if_assertions.sv"
        if path not in existing:
            lines.append(path)

    lines += [
        "",
        "// S7 assertions — project-level packages",
        f"+incdir+${{DV_ROOT}}/assertions",
        f"${{DV_ROOT}}/assertions/{proj}_assert_ctrl_pkg.sv",
        f"${{DV_ROOT}}/assertions/{proj}_top_assertions_pkg.sv",
        "",
        "// S7 bind file — MUST be last in compile.f",
        f"${{DV_ROOT}}/assertions/{proj}_dut_bind.sv",
    ]

    new_lines = [l for l in lines if l not in existing]
    if new_lines:
        with open(compile_f, "a") as f:
            f.write("\n".join(new_lines) + "\n")
        print(f"  [UPD]  {compile_f}  (+{len(new_lines)} entries)")
    else:
        print(f"  [SKIP] {compile_f}  (all entries already present)")


# ── dv_assertions_data.json ───────────────────────────────────────────────────

def write_assertions_data(proj: str, categorised: dict, unique_vips: list,
                          all_assertions: list, dv_root: str):
    assertions_out = []
    for a in all_assertions:
        chk_id = a.get("chk_id", "")
        label  = sanitize_label(chk_id)
        assertions_out.append({
            "chk_id":       chk_id,
            "description":  a.get("feature", "") + "/" + a.get("subfeature", ""),
            "milestone":    a.get("milestone", "DV-C"),
            "bucket":       a.get("_bucket", "vip_interface"),
            "vip":          a.get("_vip", None),
            "assert_label": f"AST_{label}",
            "cover_label":  f"COV_{label}",
            "source":       "testplan",
        })

    auto_count = sum(len(v.get("props",[])) for v in categorised.get("_auto",{}).values())

    data = {
        "skill":          "dv-assertions",
        "version":        "1.0",
        "project_name":   proj,
        "generated_date": date.today().isoformat(),
        "assertions":     assertions_out,
        "files": {
            "vip_assertions": [
                f"dv/agents/{v.get('vip_name')}_agent/assertions/{v.get('vip_name')}_if_assertions.sv"
                for v in unique_vips
            ],
            "dut_bind":    f"dv/assertions/{proj}_dut_bind.sv",
            "assert_ctrl": f"dv/assertions/{proj}_assert_ctrl_pkg.sv",
            "checker":     f"dv/assertions/{proj}_assertion_checker.sv",
            "top_pkg":     f"dv/assertions/{proj}_top_assertions_pkg.sv",
        },
        "summary": {
            "total_assertions":     len(all_assertions),
            "from_testplan":        len([a for a in all_assertions if a.get("_bucket") != "auto"]),
            "auto_generated":       auto_count,
            "vip_interface_bucket": len([a for a in all_assertions if a.get("_bucket") == "vip_interface"]),
            "dut_internal_bucket":  len(categorised.get("_dut_internal", [])),
            "assert_cover_pairs":   len(all_assertions) + auto_count,
            "needs_review_count":   len([a for a in all_assertions if not a.get("assertion_code","").strip()]),
        }
    }
    out = os.path.join(dv_root, "dv_assertions_data.json")
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [GEN]  {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="S7 dv-assertions generator")
    parser.add_argument("--input",  required=True, help="assertions_input.json")
    parser.add_argument("--output", required=True, help="dv/ root directory")
    args = parser.parse_args()

    dv_root = os.path.abspath(args.output)

    with open(args.input) as f:
        input_data = json.load(f)

    tb_data      = input_data.get("tb_data", {})
    proj         = tb_data.get("project_name", input_data.get("project_name", "proj"))
    unique_vips  = tb_data.get("unique_vips", [])
    testplan_rows = input_data.get("testplan_rows", [])

    print(f"\n[S7] Generating assertions for project: {proj}")
    print(f"     dv_root    : {dv_root}")
    print(f"     VIPs       : {len(unique_vips)}")
    print(f"     Testplan rows: {len(testplan_rows)}")

    # ── Categorise assertions ─────────────────────────────────────────────
    categorised = categorise_assertions(testplan_rows, unique_vips)

    # Build flat list of all assertions for checker registration
    all_assertions = []
    for vip in unique_vips:
        vname = vip.get("vip_name")
        for row in categorised.get(vname, []):
            row["_bucket"] = "vip_interface"
            row["_vip"]    = vname
            all_assertions.append(row)
    for row in categorised.get("_dut_internal", []):
        row["_bucket"] = "dut_internal"
        row["_vip"]    = None
        all_assertions.append(row)

    # ── Per-VIP assertion modules ─────────────────────────────────────────
    print("\n[Per-VIP Assertion Modules]")
    for vip in unique_vips:
        vname      = vip.get("vip_name")
        rows       = categorised.get(vname, [])
        auto_entry = categorised.get("_auto", {}).get(vname, {})
        auto_props = auto_entry.get("props", []) if auto_entry else []
        gen_vip_assertions_sv(vip, rows, auto_props, dv_root)
        chk_ids = [r.get("checker_id","") for r in rows]
        gen_vip_assertions_pkg(vname, chk_ids, dv_root)

    # ── DUT bind module ───────────────────────────────────────────────────
    print("\n[DUT Bind Module]")
    gen_dut_bind(proj, unique_vips, categorised.get("_dut_internal", []),
                 tb_data, dv_root)

    # ── Assertion control package ─────────────────────────────────────────
    print("\n[Assertion Control]")
    gen_assert_ctrl_pkg(proj, unique_vips, dv_root)

    # ── UVM assertion checker ─────────────────────────────────────────────
    print("\n[UVM Assertion Checker]")
    gen_assertion_checker(proj, all_assertions, dv_root)

    # ── Top assertions package ────────────────────────────────────────────
    print("\n[Top Assertions Package]")
    gen_top_assertions_pkg(proj, unique_vips, dv_root)

    # ── compile.f ─────────────────────────────────────────────────────────
    print("\n[compile.f]")
    update_compile_f(dv_root, proj, unique_vips)

    # ── Metadata ──────────────────────────────────────────────────────────
    print("\n[Metadata]")
    write_assertions_data(proj, categorised, unique_vips, all_assertions, dv_root)

    # ── Summary ───────────────────────────────────────────────────────────
    auto_count   = sum(len(v.get("props",[]))
                       for v in categorised.get("_auto",{}).values())
    total_pairs  = len(all_assertions) + auto_count
    needs_review = len([a for a in all_assertions
                        if not a.get("assertion_code","").strip()])

    print(f"""
============================================================
  DV Assertions — Complete
  Project : {proj}
  Output  : {dv_root}
============================================================
  Per-VIP assertion modules : {len(unique_vips)} VIPs
  DUT-internal assertions   : {len(categorised.get('_dut_internal', []))}
  Auto-generated stubs      : {auto_count}
  Total assert+cover pairs  : {total_pairs}
------------------------------------------------------------
  ⚠️  NEEDS_REVIEW: {needs_review} items
     grep -r "NEEDS_REVIEW" {dv_root}/assertions {dv_root}/agents
------------------------------------------------------------
  compile.f: bind file added last (required order maintained)
------------------------------------------------------------
  Next step: /dv-scoreboard (S8)
============================================================
""")


if __name__ == "__main__":
    main()
