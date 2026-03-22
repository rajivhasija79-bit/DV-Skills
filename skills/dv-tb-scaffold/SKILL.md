---
name: dv-tb-scaffold
description: |
  Design Verification skill that generates a complete, synthesizable UVM testbench
  scaffold for a hardware DUT. Identifies all unique VIP protocols from the DUT
  interface list, generates fully parameterized UVM VIP components for each
  (driver, monitor, sequencer, sequence item, config, agent, functional coverage,
  base sequences, interface with clocking blocks/modports/SVA), generates a UVM RAL
  model from the register map, generates the top-level UVM environment (env, env_cfg,
  scoreboard, reference model, virtual sequencer), and produces a DUT RTL stub for
  immediate compilation. All generated code is complete, syntactically correct
  SystemVerilog/UVM that compiles with VCS.

  Use this skill whenever a user wants to:
  - Generate a UVM testbench scaffold from a DUT spec or S1/S2/S3/S4 outputs
  - Create VIP (agent/driver/monitor/sequencer/coverage) for AXI/AHB/APB/SPI/I2C/UART
    or any proprietary protocol
  - Generate a UVM RAL model from a register map
  - Create a DUT RTL stub for testbench bring-up
  - Set up the full UVM env hierarchy (env, scoreboard, ref model, virtual sequencer)
  - Run /dv-tb-scaffold or S5 in the DV end-to-end flow

  Trigger on: "generate testbench", "create TB scaffold", "generate VIP", "dv-tb-scaffold",
  "/dv-tb-scaffold", "S5", "generate UVM agent", "create RAL model", "generate DUT stub",
  "create UVM environment", "scaffold TB", "generate agents from spec"
---

# DV TB Scaffold — S5

You are acting as a senior DV infrastructure architect generating a complete, production-quality
UVM testbench scaffold. Every file you generate must be syntactically correct, compile cleanly
with VCS, and follow UVM 1.2 best practices. Generated code is the foundation the DV team builds
on — placeholder TODOs must be clear and actionable.

---

## Step 0 — Check Environment (ALWAYS run first)

```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s5 --install
```

**If Bash is not available:**
- Inform the user: *"Note: Bash is not available. I will generate all SV files directly
  using the Write tool. Diagrams will be skipped. Grant Bash permission for full output."*
- Continue with all steps — write all SV files directly using the Write tool.

---

## Step 1 — Scan for Existing Resources

Before asking the user for anything, scan the conversation and working directory for
outputs from previous skills. Announce each file found and ask the user in a
**single message** whether to use it:

**Files to look for:**
| File | Source | Contains |
|------|--------|---------|
| `dv_spec_summary.json` | S1 | Interface list, register map, proprietary protocols, signals |
| `testplan.xlsx` or `dv_testplan_data.json` | S2 | Checker IDs, assertions, coverage, test names |
| `dv_verif_plan_data.json` | S3 | TB architecture, checker component mapping |
| `dv_env_data.json` | S4 | Project root, directory structure, tool paths |

> "I found the following files from previous skills: [list]. Use each? [y/n per file]"

**NEVER use a found file without explicit user confirmation.**

Also check for:
- Any existing `agents/` directory (existing VIP code)
- Any existing `ral/` directory (existing RAL model)
- Any reference model file (C model, SystemC, MATLAB, or SV golden model)

---

## Step 2 — Gather Required Inputs

After scanning, ask for any still-missing required inputs in a **single message**:

| Input | Description | If Missing |
|---|---|---|
| `PROJECT_NAME` | Block name (e.g. `data_gw`, `apb_uart`) | Ask user |
| `PROJECT_ROOT` | Absolute path where `dv/` directory lives | Get from S4 env data, else ask |
| `INTERFACE_SOURCE` | How to get the interface list | S1 JSON preferred; else ask for spec file |

---

## Step 3 — Extract and Group Interfaces → Unique VIPs

### 3a. Get Interface List

**If S1 JSON available:** Read the `interfaces` array. For each interface:
```
name: <interface_name>
protocol: <protocol_type>   (AXI4, AXI4-Lite, AXI4-Stream, AHB-Lite, APB, SPI, I2C,
                              UART, TileLink, PCIe, CHI, ACE, or PROPRIETARY)
width: <data_width>
direction: master|slave|bidir
```

**If no S1 JSON:** Ask the user to list all DUT interfaces:
> "Please list all DUT interfaces in this format (one per line):
> `<if_name>  <protocol>  <data_width>  <role (master/slave)>`
> Example: `ahb_reg  AHB-Lite  32  slave`"

### 3b. Identify Unique VIPs

Group interfaces by `(protocol, data_width, addr_width)`. Apply these rules:

1. **Identical interfaces** (same protocol + same key parameters) → one VIP, one interface
   file, instantiated N times in tb_top with different names but same parameters.
2. **Same protocol, different parameters** (e.g. TileLink 256-bit vs TileLink 128-bit) →
   same VIP class with `parameter` overrides, but creates separate interface instances.
3. **Proprietary protocol** → one VIP per proprietary protocol (regardless of width, since
   signal list may differ). Check S1 `proprietary_interfaces` for signal list.

**Print VIP summary for user confirmation:**
```
============================================================
  VIP Analysis — <PROJECT_NAME>
============================================================
  DUT Interfaces Found:
  ┌─────────────────────┬──────────────┬───────┬────────┐
  │ Interface Name      │ Protocol     │ Width │ Role   │
  ├─────────────────────┼──────────────┼───────┼────────┤
  │ ahb_reg_if          │ AHB-Lite     │  32   │ slave  │
  │ axi4_data_if        │ AXI4         │  64   │ slave  │
  │ spi_out_if          │ SPI          │   1   │ master │
  │ i2c_out_if          │ I2C          │   1   │ master │
  └─────────────────────┴──────────────┴───────┴────────┘

  Unique VIPs to generate:
  ┌───────────────┬──────────────┬─────────────────────────────┐
  │ VIP Name      │ Protocol     │ Used by Interfaces           │
  ├───────────────┼──────────────┼─────────────────────────────┤
  │ ahb_vip       │ AHB-Lite     │ ahb_reg_if                  │
  │ axi4_vip      │ AXI4         │ axi4_data_if                │
  │ spi_vip       │ SPI          │ spi_out_if                  │
  │ i2c_vip       │ I2C          │ i2c_out_if                  │
  └───────────────┴──────────────┴─────────────────────────────┘

  Does this look correct? Any changes? [y to proceed / describe changes]
============================================================
```

Wait for user confirmation before proceeding.

---

## Step 4 — Per-VIP Protocol Detail Gathering (Interactive)

For each unique VIP, gather the specific protocol details needed to generate
correct driver/monitor/interface code. Do this **per-VIP**, one at a time if
multiple unknowns exist.

### For Known Standard Protocols

For AXI4, AXI4-Lite, AXI4-Stream, AHB-Lite, APB, SPI, I2C, UART, TileLink:
- Use your built-in protocol knowledge for signal list, handshake, clocking.
- Still ask user to confirm key parameters:

**AXI4 / AXI4-Lite:**
- DATA_WIDTH (default 32), ADDR_WIDTH (default 32), ID_WIDTH (default 4)
- Supports bursts? (AXI4 yes, AXI4-Lite no)
- Supports outstanding transactions? How many?

**AXI4-Stream:**
- DATA_WIDTH, DEST_WIDTH, USER_WIDTH, TID_WIDTH
- Is TLAST used? TKEEP? TSTRB?

**AHB-Lite:**
- DATA_WIDTH (default 32), ADDR_WIDTH (default 32)
- Number of bus masters (if DUT is master), number of slaves

**APB:**
- DATA_WIDTH (default 32), ADDR_WIDTH (default 32)
- APB2 or APB3 (PREADY signal)? APB4 (PSTRB)?

**SPI:**
- CPOL/CPHA mode (0/0, 0/1, 1/0, 1/1 — or ask all modes supported)
- Data width per frame (default 8 bits)
- CS active polarity
- Is it full-duplex (MOSI+MISO) or simplex?

**I2C:**
- Standard mode (100kHz), Fast mode (400kHz), or Fast-plus (1MHz)?
- 7-bit or 10-bit addressing?
- Does DUT act as master, slave, or both?

**UART:**
- Configurable baud? Data bits (7/8), parity (none/even/odd), stop bits (1/2)
- Flow control (RTS/CTS)?

**TileLink:**
- TileLink-UL, TileLink-UH, or TileLink-C?
- DATA_WIDTH, ADDR_WIDTH, SOURCE_WIDTH, SINK_WIDTH, SIZE_WIDTH

### For Proprietary Protocols

Check if S1 JSON has `proprietary_interfaces` entry for this interface.
If yes: display the extracted signal list and ask user to confirm/augment:
> "S1 extracted the following for `<if_name>`:
> [signal list]
> Is this complete? Any missing signals or timing rules?"

If no S1 data available, ask the user interactively:
> "I need protocol details for `<if_name>` (proprietary interface).
> Please provide:
> 1. Complete signal list (name, direction, width, description)
> 2. Clock/reset: which clock drives this interface?
> 3. Protocol phases: describe each phase (arbitration, address, data, response)
> 4. Handshake: req/ack, valid/ready, or other?
> 5. Timing: e.g. 'addr presented on cycle N, data sampled N+2 cycles later'
> 6. Ordering: in-order, out-of-order, pipelined?
> 7. Error signaling: how does the interface signal errors?"

**Do NOT generate the VIP until you have sufficient protocol information.**
If critical information is still missing after asking, generate the VIP with
clearly-marked `// TODO:` placeholders and note what's missing.

---

## Step 5 — Extract Register Map for RAL

### 5a. Check Sources

Check in this priority order:
1. S1 JSON `register_map` field — use if populated (non-empty array)
2. `dv_spec_summary.json` from project directory
3. Raw spec file (if user provides it)
4. Ask user to provide register map

### 5b. Display and Confirm

Print the extracted register map for confirmation:
```
  Register Map for RAL — <PROJECT_NAME>
  Register bus: <protocol> at base address <addr>
  ┌──────────────┬────────┬─────────────┬──────────────────────────┐
  │ Register     │ Offset │ Reset Value │ Fields                   │
  ├──────────────┼────────┼─────────────┼──────────────────────────┤
  │ CTRL         │ 0x00   │ 0x00000000  │ MODE[1:0] RW, EN[0] RW  │
  │ STATUS       │ 0x04   │ 0x00000000  │ BUSY[0] RO, DONE[0] W1C │
  └──────────────┴────────┴─────────────┴──────────────────────────┘
  Register access bus: <which interface carries register traffic?>
```

Ask: *"Which interface is used for register access? (e.g. `ahb_reg_if`)"*
This determines which VIP gets the RAL adapter.

### 5c. No Registers

If `register_map` is empty or absent, ask:
> "No register map found in spec. Does this DUT have memory-mapped registers?
> If yes, please provide the register list. If no, I will skip RAL generation."

---

## Step 6 — Reference Model (Interactive)

Ask the user in a **single message**:

> "Does a reference model for `<PROJECT_NAME>` already exist?
> (a) Yes — C/C++ model → provide the path; I will wrap it with DPI-C
> (b) Yes — SystemC model → provide the path; I will generate SC-SV binding
> (c) Yes — SystemVerilog/UVM model → provide the path; I will integrate it
> (d) Yes — MATLAB/Python golden model → I will generate a DPI wrapper stub
> (e) No → I will generate a UVM reference model skeleton with predict() hooks
>
> If yes, please also describe:
> - Input stimulus the model takes (which transactions)
> - Output it produces (what the scoreboard should compare against)"

Based on the answer:
- **(a/b/d):** Generate a DPI wrapper stub with `import "DPI-C"` declarations.
  Leave the actual C function implementations as TODOs.
- **(c):** Read the provided file, integrate by instantiating it in the environment.
- **(e):** Generate a full `<project>_ref_model` class (extends `uvm_component`)
  with `analysis_imp_port` inputs, internal `predict()` function, and
  `analysis_port` output to the scoreboard.

---

## Step 7 — Extract Checkers and Assertions from Testplan (Interactive)

If S2 testplan data (`dv_testplan_data.json`) is available:
- Extract all rows where `checker_type` = `Assertion` or `Both`
- Extract `assertion_code` field from each
- Extract `checker_id` and `checker_type` for all rows
- Map checkers to components using S3 checker plan if available

Ask user to confirm checker-to-component mapping:
```
  Checker Component Mapping
  ┌────────────────────────────┬───────────┬──────────────────┐
  │ Checker ID                 │ Type      │ Proposed Component│
  ├────────────────────────────┼───────────┼──────────────────┤
  │ CHK_UART_APB_PROTOCOL_001  │ Assertion │ Interface (SVA)  │
  │ CHK_UART_TX_DATA_002       │ Procedural│ Scoreboard       │
  └────────────────────────────┴───────────┴──────────────────┘
  Confirm? Or override any mapping? [y / describe changes]
```

SVA assertions go into the interface file.
Procedural checkers get a skeleton check function in the scoreboard.
Monitor-based checks get a task skeleton in the monitor.

---

## Step 8 — Assemble TB Scaffold Data JSON

Write all gathered information to `/tmp/<project_name>_tb_scaffold_data.json`:

```json
{
  "project_name":   "<name>",
  "project_root":   "<path>",
  "generated_by":   "dv-tb-scaffold",
  "date":           "<YYYY-MM-DD>",
  "unique_vips": [
    {
      "vip_name":    "<proto>_vip",
      "protocol":    "<PROTOCOL>",
      "is_known_protocol": true,
      "parameters":  { "DATA_WIDTH": 32, "ADDR_WIDTH": 32 },
      "instances": [
        {
          "if_name":    "<if_name>",
          "role":       "master|slave",
          "data_width": 32,
          "addr_width": 32
        }
      ],
      "signals": [
        { "name": "", "direction": "", "width": "", "in_clocking_block": true }
      ],
      "is_register_bus":  false,
      "clocking_block":   true,
      "modports":         true,
      "inline_sva":       true,
      "sva_from_testplan": [],
      "foundational_seqs": ["base_seq", "reset_seq"],
      "protocol_seqs":    []
    }
  ],
  "register_map": {
    "bus_vip":    "<proto>_vip",
    "bus_if":     "<if_name>",
    "base_addr":  "0x0",
    "registers":  []
  },
  "ref_model": {
    "exists":     false,
    "form":       null,
    "path":       null,
    "inputs":     [],
    "outputs":    []
  },
  "checkers": [],
  "tb_dir":         "<project_root>/dv",
  "sources_used":   []
}
```

---

## Step 9 — Generate VIP Components (one VIP at a time)

For each unique VIP in `unique_vips`, generate the following files.
All files go in `<PROJECT_ROOT>/dv/agents/<vip_name>/`.

**NEVER overwrite an existing file.** Skip with a warning.

Run the generation script if Bash is available:
```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_tb_scaffold.py \
  --config /tmp/<project_name>_tb_scaffold_data.json \
  --phase vips
```

**If Bash unavailable**, generate each file directly with the Write tool
following the templates below.

### File 1: `<vip_name>_if.sv` — Interface

```systemverilog
// <VIP_NAME> Interface — generated by dv-tb-scaffold (S5)
// Protocol: <PROTOCOL>
// Parameters: DATA_WIDTH=<N>, ADDR_WIDTH=<N>
// DO NOT EDIT generated sections. Add custom code in marked regions.

interface <vip_name>_if #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
)(input logic clk, input logic rst_n);

  // ── Signal Declarations ──────────────────────────────────────────
  // [list all protocol signals with correct widths]

  // ── Clocking Block: Driver (Master) perspective ─────────────────
  clocking driver_cb @(posedge clk);
    default input #1step output #1;
    // [output: signals driven by driver, input: sampled by driver]
  endclocking

  // ── Clocking Block: Monitor perspective ─────────────────────────
  clocking monitor_cb @(posedge clk);
    default input #1step;
    // [all signals as input]
  endclocking

  // ── Modports ─────────────────────────────────────────────────────
  modport master_mp  (clocking driver_cb,  input rst_n);
  modport slave_mp   (/* reverse of master — output becomes input */);
  modport monitor_mp (clocking monitor_cb, input rst_n);

  // ── Protocol SVA ─────────────────────────────────────────────────
  // [Insert inline SVA from testplan here, disable iff (!rst_n)]
  // [For each CHK_ID with type Assertion or Both:]
  // property p_<name>;
  //   @(posedge clk) disable iff (!rst_n)
  //   <antecedent> |-> <consequent>;
  // endproperty
  // assert property (p_<name>) else
  //   $error("[%m] <CHK_ID> violated at %0t", $time);

endinterface : <vip_name>_if
```

### File 2: `<vip_name>_seq_item.sv` — Transaction Class

```systemverilog
// <VIP_NAME> Sequence Item — generated by dv-tb-scaffold (S5)
class <vip_name>_seq_item #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_sequence_item;

  `uvm_object_param_utils_begin(<vip_name>_seq_item#(DATA_WIDTH, ADDR_WIDTH))
    // register all rand fields with factory
    `uvm_field_int(addr,       UVM_ALL_ON)
    `uvm_field_int(data,       UVM_ALL_ON)
    // [add remaining fields]
  `uvm_object_param_utils_end

  // ── Fields that change per transaction ──────────────────────────
  rand logic [ADDR_WIDTH-1:0] addr;
  rand logic [DATA_WIDTH-1:0] data;
  rand <vip_name>_kind_e      kind;          // e.g. READ/WRITE/BURST
  rand int unsigned            pkt_size;     // number of beats in burst
  rand <delay_type_e>          delay_type;   // ZERO / FIXED / RANDOM
  rand int unsigned            delay_val;    // cycles (0 if ZERO)
  // [Add protocol-specific transaction fields here]

  // ── Constraints ──────────────────────────────────────────────────
  constraint c_delay {
    if (delay_type == ZERO)   delay_val == 0;
    else if (delay_type == FIXED) delay_val inside {[1:10]};
    else                          delay_val inside {[0:20]};
  }
  constraint c_pkt_size { pkt_size inside {[1:16]}; }

  function new(string name = "<vip_name>_seq_item");
    super.new(name);
  endfunction

  virtual function string convert2string();
    return $sformatf("[%s] addr=0x%0h data=0x%0h kind=%s pkt_size=%0d",
                     get_type_name(), addr, data, kind.name(), pkt_size);
  endfunction
endclass
```

### File 3: `<vip_name>_cfg.sv` — Config Class

```systemverilog
// <VIP_NAME> Config Class — generated by dv-tb-scaffold (S5)
// Fields here remain constant for the duration of a test run.
class <vip_name>_cfg extends uvm_object;
  `uvm_object_utils_begin(<vip_name>_cfg)
    `uvm_field_enum(uvm_active_passive_enum, is_active, UVM_ALL_ON)
    `uvm_field_int(error_inject_en, UVM_ALL_ON)
    // [add protocol-specific config fields]
  `uvm_object_utils_end

  uvm_active_passive_enum is_active       = UVM_ACTIVE;
  bit                     error_inject_en = 0;
  int unsigned            data_width      = DATA_WIDTH;
  int unsigned            addr_width      = ADDR_WIDTH;
  // [Protocol-specific constant config:]
  // e.g. spi_mode, i2c_speed, axi_id_width, uart_baud_rate, etc.

  function new(string name = "<vip_name>_cfg");
    super.new(name);
  endfunction
endclass
```

### File 4: `<vip_name>_driver.sv` — Driver BFM

```systemverilog
// <VIP_NAME> Driver — generated by dv-tb-scaffold (S5)
class <vip_name>_driver #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_driver #(<vip_name>_seq_item#(DATA_WIDTH, ADDR_WIDTH));

  `uvm_component_param_utils(<vip_name>_driver#(DATA_WIDTH, ADDR_WIDTH))

  typedef <vip_name>_seq_item #(DATA_WIDTH, ADDR_WIDTH) seq_item_t;

  virtual <vip_name>_if #(DATA_WIDTH, ADDR_WIDTH) vif;
  <vip_name>_cfg cfg;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual <vip_name>_if#(DATA_WIDTH,ADDR_WIDTH))
        ::get(this, "", "vif", vif))
      `uvm_fatal("NO_VIF", {"vif not found for ", get_full_name()})
    if (!uvm_config_db #(<vip_name>_cfg)::get(this, "", "cfg", cfg))
      `uvm_fatal("NO_CFG", {"cfg not found for ", get_full_name()})
  endfunction

  task run_phase(uvm_phase phase);
    // Drive reset-idle state on interface
    drive_idle();
    @(posedge vif.clk iff vif.rst_n);  // wait for reset deassert
    forever begin
      seq_item_port.get_next_item(req);
      `uvm_info(get_type_name(), $sformatf("Driving: %s", req.convert2string()), UVM_HIGH)
      if (req.delay_type != ZERO) repeat(req.delay_val) @(posedge vif.clk);
      drive_item(req);
      seq_item_port.item_done();
    end
  endtask

  task drive_idle();
    // TODO: drive all interface signals to protocol-defined idle state
    // e.g. @(vif.driver_cb); vif.driver_cb.valid <= 0; etc.
  endtask

  task drive_item(seq_item_t item);
    // TODO: implement full protocol state machine for driving one transaction
    // Phase 1: [describe protocol phase]
    // Phase 2: [describe protocol phase]
    // ...
    @(posedge vif.clk);
  endtask
endclass
```

### File 5: `<vip_name>_monitor.sv` — Monitor

```systemverilog
// <VIP_NAME> Monitor — generated by dv-tb-scaffold (S5)
class <vip_name>_monitor #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_monitor;

  `uvm_component_param_utils(<vip_name>_monitor#(DATA_WIDTH, ADDR_WIDTH))

  typedef <vip_name>_seq_item #(DATA_WIDTH, ADDR_WIDTH) seq_item_t;

  virtual <vip_name>_if #(DATA_WIDTH, ADDR_WIDTH) vif;
  <vip_name>_cfg cfg;

  // Analysis port — connect to scoreboard and coverage
  uvm_analysis_port #(seq_item_t) ap;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual <vip_name>_if#(DATA_WIDTH,ADDR_WIDTH))
        ::get(this, "", "vif", vif))
      `uvm_fatal("NO_VIF", {"vif not found for ", get_full_name()})
    if (!uvm_config_db #(<vip_name>_cfg)::get(this, "", "cfg", cfg))
      `uvm_fatal("NO_CFG", {"cfg not found for ", get_full_name()})
  endfunction

  task run_phase(uvm_phase phase);
    @(posedge vif.clk iff vif.rst_n);  // wait for reset deassert
    forever begin
      seq_item_t item = seq_item_t::type_id::create("item");
      collect_transaction(item);
      `uvm_info(get_type_name(), $sformatf("Observed: %s", item.convert2string()), UVM_HIGH)
      ap.write(item);
    end
  endtask

  task collect_transaction(seq_item_t item);
    // TODO: sample interface signals to reconstruct a completed transaction
    // Wait for transaction start condition
    // Capture address phase
    // Capture data phase
    // Capture response phase (if applicable)
    @(posedge vif.clk);
  endtask
endclass
```

### File 6: `<vip_name>_sequencer.sv` — Sequencer

```systemverilog
// <VIP_NAME> Sequencer — generated by dv-tb-scaffold (S5)
class <vip_name>_sequencer #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_sequencer #(<vip_name>_seq_item#(DATA_WIDTH, ADDR_WIDTH));

  `uvm_component_param_utils(<vip_name>_sequencer#(DATA_WIDTH, ADDR_WIDTH))

  // Handle to virtual interface and config — accessible from sequences
  // via p_sequencer cast
  virtual <vip_name>_if #(DATA_WIDTH, ADDR_WIDTH) vif;
  <vip_name>_cfg cfg;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual <vip_name>_if#(DATA_WIDTH,ADDR_WIDTH))
        ::get(this, "", "vif", vif))
      `uvm_fatal("NO_VIF", {"vif not found for ", get_full_name()})
    if (!uvm_config_db #(<vip_name>_cfg)::get(this, "", "cfg", cfg))
      `uvm_fatal("NO_CFG", {"cfg not found for ", get_full_name()})
  endfunction
endclass
```

### File 7: `<vip_name>_coverage.sv` — Functional Coverage Model

```systemverilog
// <VIP_NAME> Functional Coverage — generated by dv-tb-scaffold (S5)
// Coverage model for <PROTOCOL> transactions.
// This is a UVM subscriber that samples coverage when a transaction is written.
class <vip_name>_coverage #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_subscriber #(<vip_name>_seq_item#(DATA_WIDTH, ADDR_WIDTH));

  `uvm_component_param_utils(<vip_name>_coverage#(DATA_WIDTH, ADDR_WIDTH))

  typedef <vip_name>_seq_item #(DATA_WIDTH, ADDR_WIDTH) seq_item_t;

  seq_item_t trans;  // current transaction (set in write, sampled by CGs)

  // ── Covergroup: Transaction kinds ────────────────────────────────
  covergroup cg_<vip_name>_kind;
    cp_kind: coverpoint trans.kind {
      // TODO: add bins per <vip_name>_kind_e value
    }
  endgroup

  // ── Covergroup: Packet size distribution ─────────────────────────
  covergroup cg_<vip_name>_pkt_size;
    cp_pkt_size: coverpoint trans.pkt_size {
      bins single   = {1};
      bins small    = {[2:4]};
      bins medium   = {[5:8]};
      bins large    = {[9:16]};
    }
  endgroup

  // ── Covergroup: Delay type ────────────────────────────────────────
  covergroup cg_<vip_name>_delay;
    cp_delay_type: coverpoint trans.delay_type;
  endgroup

  // TODO: Add protocol-specific covergroups extracted from S2 testplan.
  // Covergroups defined in testplan (col 6) should be added here verbatim.

  function new(string name, uvm_component parent);
    super.new(name, parent);
    cg_<vip_name>_kind     = new();
    cg_<vip_name>_pkt_size = new();
    cg_<vip_name>_delay    = new();
  endfunction

  virtual function void write(seq_item_t t);
    trans = t;
    cg_<vip_name>_kind.sample();
    cg_<vip_name>_pkt_size.sample();
    cg_<vip_name>_delay.sample();
    // TODO: sample protocol-specific covergroups
  endfunction
endclass
```

### File 8: `<vip_name>_agent.sv` — Agent

```systemverilog
// <VIP_NAME> Agent — generated by dv-tb-scaffold (S5)
// Supports both UVM_ACTIVE (driver + sequencer) and UVM_PASSIVE (monitor only).
class <vip_name>_agent #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_agent;

  `uvm_component_param_utils(<vip_name>_agent#(DATA_WIDTH, ADDR_WIDTH))

  typedef <vip_name>_driver    #(DATA_WIDTH, ADDR_WIDTH) driver_t;
  typedef <vip_name>_monitor   #(DATA_WIDTH, ADDR_WIDTH) monitor_t;
  typedef <vip_name>_sequencer #(DATA_WIDTH, ADDR_WIDTH) sequencer_t;
  typedef <vip_name>_coverage  #(DATA_WIDTH, ADDR_WIDTH) coverage_t;

  driver_t    m_driver;
  monitor_t   m_monitor;
  sequencer_t m_sequencer;
  coverage_t  m_coverage;

  <vip_name>_cfg cfg;

  // Analysis port — passthrough from monitor
  uvm_analysis_port #(<vip_name>_seq_item#(DATA_WIDTH, ADDR_WIDTH)) ap;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(<vip_name>_cfg)::get(this, "", "cfg", cfg)) begin
      cfg = <vip_name>_cfg::type_id::create("cfg");
      `uvm_warning("NO_CFG", "Using default cfg")
    end
    m_monitor  = monitor_t::type_id::create("m_monitor", this);
    m_coverage = coverage_t::type_id::create("m_coverage", this);
    if (cfg.is_active == UVM_ACTIVE) begin
      m_driver    = driver_t::type_id::create("m_driver", this);
      m_sequencer = sequencer_t::type_id::create("m_sequencer", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    if (cfg.is_active == UVM_ACTIVE)
      m_driver.seq_item_port.connect(m_sequencer.seq_item_export);
    m_monitor.ap.connect(m_coverage.analysis_export);
    ap = m_monitor.ap;  // expose to environment for scoreboard connection
  endfunction
endclass
```

### File 9: `<vip_name>_base_seq.sv` — Base Sequence

```systemverilog
// <VIP_NAME> Base Sequence — generated by dv-tb-scaffold (S5)
// All VIP sequences extend this. Provides access to vif and cfg via p_sequencer.
class <vip_name>_base_seq #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends uvm_sequence #(<vip_name>_seq_item#(DATA_WIDTH, ADDR_WIDTH));

  `uvm_object_param_utils(<vip_name>_base_seq#(DATA_WIDTH, ADDR_WIDTH))
  `uvm_declare_p_sequencer(<vip_name>_sequencer#(DATA_WIDTH, ADDR_WIDTH))

  typedef <vip_name>_seq_item #(DATA_WIDTH, ADDR_WIDTH) seq_item_t;

  function new(string name = "<vip_name>_base_seq");
    super.new(name);
  endfunction

  // Helper: send one transaction and wait for completion
  task send(seq_item_t item);
    start_item(item);
    if (!item.randomize()) `uvm_fatal("RAND_FAIL", "randomize() failed")
    finish_item(item);
  endtask

  // Helper: wait N clock cycles
  task wait_clk(int unsigned n = 1);
    repeat(n) @(posedge p_sequencer.vif.clk);
  endtask

  virtual task body();
    // Override in derived sequences
  endtask
endclass
```

### File 10: `<vip_name>_reset_seq.sv` — Reset Sequence

```systemverilog
// <VIP_NAME> Reset / Idle Sequence — generated by dv-tb-scaffold (S5)
// Drives the interface to protocol-defined idle state during reset.
class <vip_name>_reset_seq #(
  parameter int DATA_WIDTH = <N>,
  parameter int ADDR_WIDTH = <N>
) extends <vip_name>_base_seq #(DATA_WIDTH, ADDR_WIDTH);

  `uvm_object_param_utils(<vip_name>_reset_seq#(DATA_WIDTH, ADDR_WIDTH))

  function new(string name = "<vip_name>_reset_seq");
    super.new(name);
  endfunction

  virtual task body();
    // TODO: drive protocol idle/reset state on interface
    // e.g. deassert valid, drive address to 0, etc.
    // Wait for reset deassertion:
    @(posedge p_sequencer.vif.clk iff p_sequencer.vif.rst_n);
    `uvm_info(get_type_name(), "Reset deasserted — interface idle", UVM_MEDIUM)
  endtask
endclass
```

### File 11: `<vip_name>_agent_pkg.sv` — Package

```systemverilog
// <VIP_NAME> Agent Package — generated by dv-tb-scaffold (S5)
// Include this package in compile.f BEFORE any file that references <vip_name>_*.
package <vip_name>_agent_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  // Enums and typedefs
  typedef enum logic [1:0] {
    <VIP_NAME>_READ  = 2'b00,
    <VIP_NAME>_WRITE = 2'b01
    // TODO: add protocol-specific transaction kinds
  } <vip_name>_kind_e;

  typedef enum logic [1:0] {
    ZERO   = 2'b00,
    FIXED  = 2'b01,
    RANDOM = 2'b10
  } delay_type_e;

  // Ordered includes (dependencies first)
  `include "<vip_name>_cfg.sv"
  `include "<vip_name>_seq_item.sv"
  `include "<vip_name>_sequencer.sv"
  `include "<vip_name>_driver.sv"
  `include "<vip_name>_monitor.sv"
  `include "<vip_name>_coverage.sv"
  `include "<vip_name>_agent.sv"
  `include "<vip_name>_base_seq.sv"
  `include "<vip_name>_reset_seq.sv"
  // TODO: add protocol-specific sequences here
endpackage : <vip_name>_agent_pkg
```

---

## Step 10 — Generate RAL Model

If `register_map` is non-empty, generate the RAL model.
All RAL files go in `<PROJECT_ROOT>/dv/ral/`.

Run:
```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_tb_scaffold.py \
  --config /tmp/<project_name>_tb_scaffold_data.json \
  --phase ral
```

**If Bash unavailable**, generate directly with Write tool.

### Per-Register File: `<project>_<reg_name>_reg.sv`

```systemverilog
// <REG_NAME> Register — generated by dv-tb-scaffold (S5)
// Offset: <OFFSET>  Reset: <RESET_VALUE>
// <REGISTER_DESCRIPTION>
class <project>_<reg_name>_reg extends uvm_reg;
  `uvm_object_utils(<project>_<reg_name>_reg)

  // ── Register Fields ──────────────────────────────────────────────
  // For each field: rand uvm_reg_field <FIELD_NAME>;
  rand uvm_reg_field <FIELD_NAME>;
  // ... [one line per field]

  function new(string name = "<project>_<reg_name>_reg");
    super.new(name, 32, UVM_NO_COVERAGE);  // 32-bit register
  endfunction

  virtual function void build();
    // <FIELD_NAME>.configure(parent_reg, size, lsb_pos, access, volatile,
    //                        reset_val, has_reset, is_rand, indiv_acc)
    <FIELD_NAME> = uvm_reg_field::type_id::create("<FIELD_NAME>");
    <FIELD_NAME>.configure(
      .parent              (this),
      .size                (<FIELD_WIDTH>),
      .lsb_pos             (<LSB>),
      .access              ("<ACCESS>"),    // RW/RO/W1C/W1S/WO/RC/RS
      .volatile            (1'b0),
      .reset               (<RESET_VAL>),
      .has_reset           (1'b1),
      .is_rand             (1'b1),
      .individually_accessible (1'b0)
    );
  endfunction
endclass
```

### Register Block File: `<project>_reg_block.sv`

```systemverilog
// <PROJECT> Register Block — generated by dv-tb-scaffold (S5)
// Contains all <N> registers extracted from spec.
class <project>_reg_block extends uvm_reg_block;
  `uvm_object_utils(<project>_reg_block)

  // ── Register handles (one per register) ─────────────────────────
  rand <project>_<reg_name>_reg <reg_name>;
  // ... [one line per register]

  // ── Register map ─────────────────────────────────────────────────
  uvm_reg_map m_map;

  function new(string name = "<project>_reg_block");
    super.new(name, UVM_NO_COVERAGE);
  endfunction

  virtual function void build();
    // Create and configure each register
    <reg_name> = <project>_<reg_name>_reg::type_id::create("<reg_name>");
    <reg_name>.configure(.blk_parent(this), .hdl_path("<reg_name>"));
    <reg_name>.build();
    // ... [repeat for each register]

    // Create map: (name, base_addr, n_bytes per addr, endianness)
    m_map = create_map("m_map", <BASE_ADDR>, 4, UVM_LITTLE_ENDIAN);

    // Add registers to map: (reg_handle, offset, rights)
    m_map.add_reg(<reg_name>, <OFFSET>, "RW");
    // ... [repeat for each register]

    lock_model();
  endfunction

  // ── Backdoor Access ──────────────────────────────────────────────
  // Call set_hdl_path_root(<dut_hdl_path>) from the test's build_phase
  // e.g. m_reg_block.set_hdl_path_root("tb_top.<dut_instance>");
  //
  // Per-register HDL paths (auto-generated from signal names):
  virtual function void configure_backdoor(string dut_path);
    // TODO: verify these HDL paths match the DUT's actual hierarchy
    <reg_name>.add_hdl_path_slice($sformatf("%s.<reg_name>", dut_path), 0, 32);
    // ... [one per register]
  endfunction
endclass
```

### RAL Adapter File: `<reg_proto>_ral_adapter.sv`

```systemverilog
// <REG_PROTO> RAL Adapter — generated by dv-tb-scaffold (S5)
// Bridges UVM RAL (uvm_reg_bus_op) to <REG_PROTO> sequence items.
class <reg_proto>_ral_adapter extends uvm_reg_adapter;
  `uvm_object_utils(<reg_proto>_ral_adapter)

  function new(string name = "<reg_proto>_ral_adapter");
    super.new(name);
    supports_byte_enable = 0;
    provides_responses   = 1;
  endfunction

  virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw);
    <reg_proto>_seq_item item = <reg_proto>_seq_item::type_id::create("item");
    item.addr = rw.addr;
    item.data = rw.data;
    item.kind = (rw.kind == UVM_READ) ? <REG_PROTO>_READ : <REG_PROTO>_WRITE;
    // TODO: map any additional RAL fields to protocol-specific fields
    return item;
  endfunction

  virtual function void bus2reg(uvm_sequence_item bus_item,
                                ref uvm_reg_bus_op rw);
    <reg_proto>_seq_item item;
    if (!$cast(item, bus_item))
      `uvm_fatal("CAST_FAIL", "bus2reg: cast to <reg_proto>_seq_item failed")
    rw.addr   = item.addr;
    rw.data   = item.data;
    rw.kind   = (item.kind == <REG_PROTO>_READ) ? UVM_READ : UVM_WRITE;
    rw.status = UVM_IS_OK;
    // TODO: check protocol response for errors and set rw.status accordingly
  endfunction
endclass
```

### RAL Package: `<project>_ral_pkg.sv`

```systemverilog
package <project>_ral_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  `include "<project>_<reg_name>_reg.sv"  // one per register
  `include "<project>_reg_block.sv"
  `include "<reg_proto>_ral_adapter.sv"
endpackage
```

---

## Step 11 — Generate Top-Level Environment

All files in `<PROJECT_ROOT>/dv/env/`.

Run:
```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_tb_scaffold.py \
  --config /tmp/<project_name>_tb_scaffold_data.json \
  --phase env
```

### `<project>_env_cfg.sv` — Top Config

```systemverilog
// <PROJECT> Top Environment Config — generated by dv-tb-scaffold (S5)
// Instantiates one config object per VIP instance.
// Tests create this and set it in uvm_config_db before run_test().
class <project>_env_cfg extends uvm_object;
  `uvm_object_utils_begin(<project>_env_cfg)
    // [register all VIP config handles]
  `uvm_object_utils_end

  // ── Per-agent config handles (one per interface instance) ────────
  <proto1>_cfg m_<if1>_cfg;   // e.g. ahb_cfg m_ahb_reg_cfg
  <proto2>_cfg m_<if2>_cfg;
  // ... [one per interface instance]

  // ── RAL handle (set after reg_block.build()) ─────────────────────
  <project>_reg_block m_reg_block;

  function new(string name = "<project>_env_cfg");
    super.new(name);
    // Create all VIP configs
    m_<if1>_cfg = <proto1>_cfg::type_id::create("m_<if1>_cfg");
    m_<if2>_cfg = <proto2>_cfg::type_id::create("m_<if2>_cfg");
    // ... [one per interface instance]
  endfunction
endclass
```

### `<project>_ref_model.sv` — Reference Model

```systemverilog
// <PROJECT> Reference Model — generated by dv-tb-scaffold (S5)
// Receives stimulus from input agents, predicts expected output,
// sends predictions to scoreboard via ap_out.
//
// TODO: Implement the predict() function with your DUT's expected behavior.
// The scoreboard calls ap_out.write(predicted_item) after each input.
class <project>_ref_model extends uvm_component;
  `uvm_component_utils(<project>_ref_model)

  // ── Input analysis ports (one per stimulus agent) ────────────────
  // Connect from env: <input_agent>.m_monitor.ap → m_<input>_imp
  uvm_analysis_imp_<tag> #(<proto>_seq_item, <project>_ref_model) m_<input>_imp;

  // ── Output analysis port → scoreboard ────────────────────────────
  uvm_analysis_port #(<proto_out>_seq_item) ap_out;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    m_<input>_imp = new("m_<input>_imp", this);
    ap_out         = new("ap_out", this);
  endfunction

  // ── Prediction function — implement DUT behavior here ────────────
  virtual function void write_<tag>(<proto>_seq_item stimulus);
    // TODO: apply DUT transformation to stimulus
    // Create predicted output item
    // <proto_out>_seq_item predicted = <proto_out>_seq_item::type_id::create("predicted");
    // predicted.data = <transform>(stimulus.data);
    // ap_out.write(predicted);
    `uvm_info(get_type_name(),
      $sformatf("Received stimulus: %s", stimulus.convert2string()), UVM_HIGH)
  endfunction
endclass
```

### `<project>_scoreboard.sv` — Scoreboard

```systemverilog
// <PROJECT> Scoreboard — generated by dv-tb-scaffold (S5)
// Compares actual DUT output (from output monitor) against
// predicted output (from reference model).
class <project>_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(<project>_scoreboard)

  // ── Expected queue (predictions from ref model) ──────────────────
  <proto_out>_seq_item m_expected_q[$];
  uvm_analysis_imp_exp  #(<proto_out>_seq_item, <project>_scoreboard) m_exp_imp;

  // ── Actual output (from output monitor) ──────────────────────────
  uvm_analysis_imp_act  #(<proto_out>_seq_item, <project>_scoreboard) m_act_imp;

  // ── Pass/Fail counters ────────────────────────────────────────────
  int unsigned m_pass_cnt = 0;
  int unsigned m_fail_cnt = 0;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    m_exp_imp = new("m_exp_imp", this);
    m_act_imp = new("m_act_imp", this);
  endfunction

  // Called by ref model
  virtual function void write_exp(<proto_out>_seq_item item);
    m_expected_q.push_back(item);
  endfunction

  // Called by output monitor — triggers comparison
  virtual function void write_act(<proto_out>_seq_item actual);
    <proto_out>_seq_item expected;
    if (m_expected_q.size() == 0) begin
      m_fail_cnt++;
      `uvm_error("SB_UNEXPECTED",
        $sformatf("Unexpected transaction: %s", actual.convert2string()))
      return;
    end
    expected = m_expected_q.pop_front();
    if (actual.data !== expected.data) begin
      m_fail_cnt++;
      `uvm_error("SB_MISMATCH",
        $sformatf("DATA MISMATCH: expected=0x%0h actual=0x%0h",
                  expected.data, actual.data))
    end else begin
      m_pass_cnt++;
      `uvm_info("SB_MATCH",
        $sformatf("MATCH: data=0x%0h", actual.data), UVM_HIGH)
    end
    // TODO: add protocol-specific field comparisons
    // Procedural checkers from testplan go here:
    // CHK_xxx: check <condition>
  endfunction

  function void check_phase(uvm_phase phase);
    if (m_expected_q.size() > 0)
      `uvm_error("SB_LEFTOVER",
        $sformatf("%0d expected transactions never matched", m_expected_q.size()))
    `uvm_info("SB_SUMMARY",
      $sformatf("Scoreboard: PASS=%0d FAIL=%0d", m_pass_cnt, m_fail_cnt), UVM_NONE)
  endfunction
endclass
```

### `<project>_env.sv` — Top UVM Environment

```systemverilog
// <PROJECT> UVM Environment — generated by dv-tb-scaffold (S5)
// Instantiates all agents, scoreboard, reference model, RAL, virtual sequencer.
class <project>_env extends uvm_env;
  `uvm_component_utils(<project>_env)

  // ── Agent handles (one per interface instance) ───────────────────
  <proto1>_agent #(.DATA_WIDTH(<N>)) m_<if1>_agent;
  <proto2>_agent #(.DATA_WIDTH(<N>)) m_<if2>_agent;
  // ... [one per interface instance]

  // ── Environment components ────────────────────────────────────────
  <project>_scoreboard   m_scoreboard;
  <project>_ref_model    m_ref_model;
  <project>_env_cfg      cfg;

  // ── RAL ──────────────────────────────────────────────────────────
  <project>_reg_block    m_reg_block;
  <reg_proto>_ral_adapter m_ral_adapter;
  uvm_reg_predictor #(<reg_proto>_seq_item) m_reg_predictor;

  // ── Virtual sequencer ────────────────────────────────────────────
  <project>_virtual_seqr m_vseqr;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);

    // Get top config
    if (!uvm_config_db #(<project>_env_cfg)::get(this, "", "cfg", cfg))
      `uvm_fatal("NO_CFG", "env cfg not found in config_db")

    // Create agents and pass their configs
    m_<if1>_agent = <proto1>_agent#(<N>)::type_id::create("m_<if1>_agent", this);
    uvm_config_db #(<proto1>_cfg)::set(this, "m_<if1>_agent.*", "cfg", cfg.m_<if1>_cfg);
    // ... [repeat for each agent]

    // Create environment components
    m_scoreboard = <project>_scoreboard::type_id::create("m_scoreboard", this);
    m_ref_model  = <project>_ref_model::type_id::create("m_ref_model",  this);
    m_vseqr      = <project>_virtual_seqr::type_id::create("m_vseqr",   this);

    // Build RAL
    m_reg_block      = <project>_reg_block::type_id::create("m_reg_block");
    m_reg_block.build();
    m_ral_adapter    = <reg_proto>_ral_adapter::type_id::create("m_ral_adapter",   this);
    m_reg_predictor  = uvm_reg_predictor#(<reg_proto>_seq_item)
                       ::type_id::create("m_reg_predictor", this);
    cfg.m_reg_block  = m_reg_block;
  endfunction

  function void connect_phase(uvm_phase phase);
    // Connect RAL map to register agent
    m_reg_block.m_map.set_sequencer(
      m_<reg_if>_agent.m_sequencer, m_ral_adapter);
    m_reg_predictor.map     = m_reg_block.m_map;
    m_reg_predictor.adapter = m_ral_adapter;
    m_<reg_if>_agent.m_monitor.ap.connect(m_reg_predictor.bus_in);

    // Connect input monitor → ref model
    m_<input_if>_agent.m_monitor.ap.connect(m_ref_model.m_<input>_imp);

    // Connect ref model prediction → scoreboard expected
    m_ref_model.ap_out.connect(m_scoreboard.m_exp_imp);

    // Connect output monitor → scoreboard actual
    m_<output_if>_agent.m_monitor.ap.connect(m_scoreboard.m_act_imp);

    // Wire virtual sequencer handles
    m_vseqr.m_<if1>_seqr = m_<if1>_agent.m_sequencer;
    // ... [one per active agent]
  endfunction
endclass
```

### `<project>_virtual_seqr.sv` — Virtual Sequencer

```systemverilog
// <PROJECT> Virtual Sequencer — generated by dv-tb-scaffold (S5)
// Provides handles to all agent sequencers so virtual sequences
// can coordinate multi-agent stimulus.
class <project>_virtual_seqr extends uvm_sequencer;
  `uvm_component_utils(<project>_virtual_seqr)

  // ── Agent sequencer handles ───────────────────────────────────────
  <proto1>_sequencer #(<N>) m_<if1>_seqr;
  <proto2>_sequencer #(<N>) m_<if2>_seqr;
  // ... [one per active agent]

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
endclass
```

---

## Step 12 — Generate TB Top and DUT Stub

Files go in `<PROJECT_ROOT>/dv/tb/`.

### `<project>_tb_top.sv` — Testbench Top Module

```systemverilog
// <PROJECT> Testbench Top — generated by dv-tb-scaffold (S5)
// Instantiates DUT, all interfaces, drives clock/reset, runs UVM test.
module <project>_tb_top;
  import uvm_pkg::*;
  `include "uvm_macros.svh"
  import <project>_env_pkg::*;
  import <project>_ral_pkg::*;

  // ── Clock and Reset ──────────────────────────────────────────────
  // TODO: set period to match DUT spec
  parameter realtime CLK_PERIOD = 10ns;  // 100 MHz default

  logic clk;
  logic rst_n;

  initial clk = 0;
  always #(CLK_PERIOD/2) clk = ~clk;

  initial begin
    rst_n = 0;
    repeat(10) @(posedge clk);
    rst_n = 1;
    `uvm_info("TB_TOP", "Reset deasserted", UVM_NONE)
  end

  // ── Interface Instances ──────────────────────────────────────────
  // [one instance per DUT interface, with correct parameters]
  <proto1>_if #(.DATA_WIDTH(<N>)) u_<if1> (.clk(clk), .rst_n(rst_n));
  <proto2>_if #(.DATA_WIDTH(<N>)) u_<if2> (.clk(clk), .rst_n(rst_n));
  // ... [one per interface]

  // ── DUT Instance ─────────────────────────────────────────────────
  <project>_dut u_dut (
    .clk       (clk),
    .rst_n     (rst_n),
    // TODO: connect DUT ports to interface signals
    // .<port>  (u_<if>.<signal>),
  );

  // ── UVM Config DB — Pass interfaces to agents ────────────────────
  initial begin
    uvm_config_db #(virtual <proto1>_if#(<N>))
      ::set(null, "uvm_test_top.m_env.m_<if1>_agent.*", "vif", u_<if1>);
    // ... [one per interface]
    run_test();  // UVM test name from +UVM_TESTNAME plusarg
  end

  // ── Backdoor HDL path configuration ─────────────────────────────
  initial begin
    // TODO: Set RAL backdoor path after DUT is connected
    // env.m_reg_block.configure_backdoor("tb_top.u_dut");
  end

  // ── Bind assertions ──────────────────────────────────────────────
  // bind <project>_dut <project>_assertions u_assert(.clk(clk),.rst_n(rst_n),...);

endmodule : <project>_tb_top
```

### `<project>_dut_stub.sv` — DUT RTL Stub

```systemverilog
// <PROJECT> DUT Stub — generated by dv-tb-scaffold (S5)
// Synthesizable module shell. Port list derived from S1 interface spec.
// Replace this with the real RTL when available.
// All outputs driven to known values to avoid X-propagation issues.
module <project>_dut (
  input  logic        clk,
  input  logic        rst_n,

  // ── [IF1: <if1_name>] <protocol1> interface ──────────────────────
  // TODO: add all ports for <if1_name>
  // input  logic [<N>-1:0]  <signal_name>,
  // output logic [<N>-1:0]  <signal_name>,

  // ── [IF2: <if2_name>] <protocol2> interface ──────────────────────
  // TODO: add all ports for <if2_name>

  // ── Interrupt output ──────────────────────────────────────────────
  output logic        irq_o
);

  // ── Stub: drive all outputs to safe values ───────────────────────
  // TODO: replace with real RTL
  assign irq_o = 1'b0;
  // [assign all output ports to 0 or known-safe values]

endmodule : <project>_dut
```

### `<project>_env_pkg.sv` — Environment Package

```systemverilog
// <PROJECT> Environment Package — generated by dv-tb-scaffold (S5)
package <project>_env_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  // Import all VIP packages
  import <proto1>_agent_pkg::*;
  import <proto2>_agent_pkg::*;
  // ... [one per unique VIP]

  // Environment components (ordered by dependency)
  `include "<project>_env_cfg.sv"
  `include "<project>_ref_model.sv"
  `include "<project>_scoreboard.sv"
  `include "<project>_virtual_seqr.sv"
  `include "<project>_env.sv"
endpackage : <project>_env_pkg
```

---

## Step 13 — Update compile.f

If S4 `dv_env_data.json` is available, update the `compile.f` file to include all
newly generated files. If compile.f does not exist, generate it now.

```
// <PROJECT> Compile File List — updated by dv-tb-scaffold (S5)
// Pass to vlogan: vlogan -sverilog -f compile.f ...

// ── UVM ──────────────────────────────────────────────────────────
+incdir+${UVM_HOME}/src
${UVM_HOME}/src/uvm_pkg.sv
`include "uvm_macros.svh"

// ── RAL Package ──────────────────────────────────────────────────
${DV_ROOT}/ral/<project>_ral_pkg.sv

// ── VIP Packages (one per unique VIP) ────────────────────────────
${DV_ROOT}/agents/<proto1>_agent/<proto1>_if.sv
${DV_ROOT}/agents/<proto1>_agent/<proto1>_agent_pkg.sv
// ... [repeat for each VIP]

// ── Interfaces for TB top ─────────────────────────────────────────
// (already included via VIP pkg above)

// ── Environment Package ───────────────────────────────────────────
${DV_ROOT}/env/<project>_env_pkg.sv

// ── Sequences and Tests ───────────────────────────────────────────
${DV_ROOT}/seq_lib/<project>_virtual_seqr.sv
${DV_ROOT}/seq_lib/<project>_base_test.sv
${DV_ROOT}/seq_lib/<project>_sanity_test.sv

// ── TB Top ────────────────────────────────────────────────────────
${DV_ROOT}/tb/<project>_tb_top.sv
```

---

## Step 14 — Output dv_tb_data.json

Write `/tmp/<project_name>_tb_data_output.json` — consumed by S6+:

```json
{
  "project_name":   "<name>",
  "project_root":   "<path>",
  "generated_by":   "dv-tb-scaffold",
  "date":           "<YYYY-MM-DD>",
  "unique_vips": [
    {
      "vip_name":     "<proto>_vip",
      "protocol":     "<PROTOCOL>",
      "parameters":   { "DATA_WIDTH": 32, "ADDR_WIDTH": 32 },
      "instances":    [{ "if_name": "", "role": "", "data_width": 32 }],
      "files_generated": [
        "<path>/<vip_name>_if.sv",
        "<path>/<vip_name>_seq_item.sv",
        "<path>/<vip_name>_cfg.sv",
        "<path>/<vip_name>_driver.sv",
        "<path>/<vip_name>_monitor.sv",
        "<path>/<vip_name>_sequencer.sv",
        "<path>/<vip_name>_coverage.sv",
        "<path>/<vip_name>_agent.sv",
        "<path>/<vip_name>_base_seq.sv",
        "<path>/<vip_name>_reset_seq.sv",
        "<path>/<vip_name>_agent_pkg.sv"
      ]
    }
  ],
  "ral": {
    "generated": true,
    "reg_count": 5,
    "register_bus_vip": "<proto>_vip",
    "files_generated":  ["<path>/ral/<project>_reg_block.sv", "..."]
  },
  "env_files_generated": [
    "<path>/env/<project>_env_cfg.sv",
    "<path>/env/<project>_ref_model.sv",
    "<path>/env/<project>_scoreboard.sv",
    "<path>/env/<project>_env.sv",
    "<path>/seq_lib/<project>_virtual_seqr.sv",
    "<path>/tb/<project>_tb_top.sv",
    "<path>/tb/<project>_dut_stub.sv"
  ],
  "compile_f":  "<path>/dv/sim/compile.f",
  "build_cmd":  "make -C <path>/dv/sim compile",
  "sim_cmd":    "make -C <path>/dv/sim sim TEST=sanity SEED=1"
}
```

---

## Step 15 — Print Terminal Summary

```
============================================================
  DV TB Scaffold — Complete
  Project   : <PROJECT_NAME>
  Root      : <PROJECT_ROOT>
------------------------------------------------------------
  VIPs Generated    : N  unique protocols
    <proto1>_vip    : 11 files  (N interface instances)
    <proto2>_vip    : 11 files  (N interface instances)
    ...
------------------------------------------------------------
  RAL Model         : N registers, N total fields
    Register bus    : <if_name> (<protocol>)
    Frontdoor       : ✓ (via <reg_proto>_ral_adapter)
    Backdoor        : ✓ (HDL paths in reg_block.configure_backdoor())
------------------------------------------------------------
  Environment       : env, env_cfg, scoreboard, ref_model,
                      virtual_seqr, tb_top, dut_stub
  Reference model   : <generated from scratch | integrated from path>
  Compile list      : compile.f updated
------------------------------------------------------------
  TODOs requiring engineer attention:
    ⚠  <N> drive_item() tasks in drivers (protocol state machines)
    ⚠  <N> collect_transaction() tasks in monitors
    ⚠  <N> predict() function in ref model (DUT behavior)
    ⚠  DUT port connections in tb_top
    ⚠  Backdoor HDL paths — verify against real DUT hierarchy
------------------------------------------------------------
  Quick start:
    source <PROJECT_ROOT>/proj.cshrc
    cd <PROJECT_ROOT>/dv/sim
    make compile
    make sim TEST=sanity SEED=1 WAVES=1
------------------------------------------------------------
  Next step: run /dv-sequences (S6) to generate protocol-
             specific directed and random sequences
============================================================
```

---

## Important Notes

- **Every generated file MUST be syntactically valid SystemVerilog** — mentally validate
  before writing. Unclosed `begin/end`, missing `;`, or wrong `endclass` labels
  cause compilation failures for the whole team.
- **Parameterization is mandatory** — all VIP classes must use `parameter` for
  DATA_WIDTH, ADDR_WIDTH. Hardcoded widths are not acceptable.
- **p_sequencer access for vif/cfg in sequences**: Sequences access the virtual
  interface and config via `p_sequencer.vif` and `p_sequencer.cfg` using
  `` `uvm_declare_p_sequencer ``. This is the only correct pattern — do NOT use
  `uvm_config_db` inside sequences.
- **analysis_port multiplexing**: Use `uvm_analysis_imp_<tag>` macros for scoreboards
  receiving from multiple analysis ports. The `<tag>` must be unique per imp.
- **RAL backdoor**: Always generate the `configure_backdoor()` function even if
  HDL paths are TBD — the function call in tb_top reminds the engineer to fill it.
- **Never overwrite existing files**: Check with `if p.exists()` in the script
  and with the Write tool — only write if the file does not already exist.
- **Proprietary protocol**: If protocol details are insufficient, generate the
  VIP template with maximum `// TODO:` coverage — do NOT block generation.
- **Interaction is mandatory**: Never assume protocol parameters, never assume
  which interface carries register traffic, never assume reference model state.
  Always ask and confirm before generating.
