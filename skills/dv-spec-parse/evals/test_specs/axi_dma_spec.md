# AXI DMA Controller — Design Specification
**Block:** AXI_DMA
**Version:** 0.9 (Draft)

---

## Overview
The AXI_DMA is a single-channel Direct Memory Access controller with an AXI4 master
interface for memory transfers and an APB slave interface for configuration and status.
It supports memory-to-memory transfers, configurable burst length, and interrupt on
transfer completion.

---

## Features
1. AXI4 master for source and destination memory access
2. APB slave for register configuration
3. Configurable transfer size (1 to 65535 bytes)
4. Burst transfers (INCR type, length 1–16 beats)
5. Transfer complete interrupt
6. Error interrupt on AXI slave error response
7. Scatter-gather not supported in this version

---

## Interfaces

### AXI4 Master Interface
| Signal       | Dir    | Width | Description              |
|--------------|--------|-------|--------------------------|
| aclk         | Input  | 1     | AXI clock                |
| aresetn      | Input  | 1     | AXI active-low reset     |
| awaddr       | Output | 32    | Write address            |
| awlen        | Output | 8     | Burst length             |
| awvalid      | Output | 1     | Write address valid      |
| awready      | Input  | 1     | Write address ready      |
| wdata        | Output | 32    | Write data               |
| wstrb        | Output | 4     | Write strobes            |
| wlast        | Output | 1     | Last write beat          |
| wvalid       | Output | 1     | Write data valid         |
| wready       | Input  | 1     | Write data ready         |
| bresp        | Input  | 2     | Write response           |
| bvalid       | Input  | 1     | Write response valid     |
| bready       | Output | 1     | Write response ready     |
| araddr       | Output | 32    | Read address             |
| arlen        | Output | 8     | Read burst length        |
| arvalid      | Output | 1     | Read address valid       |
| arready      | Input  | 1     | Read address ready       |
| rdata        | Input  | 32    | Read data                |
| rresp        | Input  | 2     | Read response            |
| rlast        | Input  | 1     | Last read beat           |
| rvalid       | Input  | 1     | Read data valid          |
| rready       | Output | 1     | Read data ready          |

### APB Slave Interface
| Signal   | Dir    | Width | Description          |
|----------|--------|-------|----------------------|
| pclk     | Input  | 1     | APB clock            |
| presetn  | Input  | 1     | APB reset active-low |
| psel     | Input  | 1     | Chip select          |
| penable  | Input  | 1     | Enable               |
| pwrite   | Input  | 1     | Write enable         |
| paddr    | Input  | 8     | Address              |
| pwdata   | Input  | 32    | Write data           |
| prdata   | Output | 32    | Read data            |
| pready   | Output | 1     | Ready                |

### Interrupt Interface
| Signal    | Dir    | Width | Description                  |
|-----------|--------|-------|------------------------------|
| dma_done  | Output | 1     | Transfer complete interrupt   |
| dma_err   | Output | 1     | AXI error interrupt           |

---

## Parameters
| Parameter    | Default | Description               |
|--------------|---------|---------------------------|
| DATA_WIDTH   | 32      | AXI data width            |
| ADDR_WIDTH   | 32      | AXI address width         |
| MAX_BURST    | 16      | Max AXI burst length      |

---

## Clocks and Resets
- aclk: AXI clock, 100–200 MHz
- pclk: APB clock, 50–100 MHz
- aresetn: async active-low, de-asserted synchronously to aclk
- presetn: sync active-low, synchronous to pclk

---

## Operating Modes
- Idle: No transfer in progress
- Active Transfer: DMA moving data from source to destination
- Error State: AXI error received, requires software clear

---

## Compliance
- AXI4 (AMBA AXI and ACE Protocol Specification, ARM IHI0022)
- APB v2.0

---

## Constraints
- Only memory-to-memory transfers supported
- Single outstanding transaction at a time
- Source and destination addresses must be word-aligned
