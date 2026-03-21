# DV Spec Summary — AXI DMA Controller

**Block:** AXI_DMA
**Version:** 0.9 (Draft)
**Project:** axi_dma

---

## 1. Overview

The AXI_DMA is a single-channel Direct Memory Access controller with an AXI4 master interface for memory transfers and an APB slave interface for configuration and status. It supports memory-to-memory transfers, configurable burst length, and interrupt on transfer completion.

---

## 2. Features

| # | Feature |
|---|---------|
| 1 | AXI4 master for source and destination memory access |
| 2 | APB slave for register configuration |
| 3 | Configurable transfer size: 1 to 65535 bytes |
| 4 | Burst transfers: INCR type, length 1–16 beats |
| 5 | Transfer complete interrupt |
| 6 | Error interrupt on AXI slave error response |
| 7 | Scatter-gather NOT supported in this version |

---

## 3. Interfaces

### 3.1 AXI4 Master Interface

| Signal   | Direction | Width | Description              |
|----------|-----------|-------|--------------------------|
| aclk     | Input     | 1     | AXI clock                |
| aresetn  | Input     | 1     | AXI active-low reset     |
| awaddr   | Output    | 32    | Write address            |
| awlen    | Output    | 8     | Burst length             |
| awvalid  | Output    | 1     | Write address valid      |
| awready  | Input     | 1     | Write address ready      |
| wdata    | Output    | 32    | Write data               |
| wstrb    | Output    | 4     | Write strobes            |
| wlast    | Output    | 1     | Last write beat          |
| wvalid   | Output    | 1     | Write data valid         |
| wready   | Input     | 1     | Write data ready         |
| bresp    | Input     | 2     | Write response           |
| bvalid   | Input     | 1     | Write response valid     |
| bready   | Output    | 1     | Write response ready     |
| araddr   | Output    | 32    | Read address             |
| arlen    | Output    | 8     | Read burst length        |
| arvalid  | Output    | 1     | Read address valid       |
| arready  | Input     | 1     | Read address ready       |
| rdata    | Input     | 32    | Read data                |
| rresp    | Input     | 2     | Read response            |
| rlast    | Input     | 1     | Last read beat           |
| rvalid   | Input     | 1     | Read data valid          |
| rready   | Output    | 1     | Read data ready          |

### 3.2 APB Slave Interface

| Signal  | Direction | Width | Description          |
|---------|-----------|-------|----------------------|
| pclk    | Input     | 1     | APB clock            |
| presetn | Input     | 1     | APB reset active-low |
| psel    | Input     | 1     | Chip select          |
| penable | Input     | 1     | Enable               |
| pwrite  | Input     | 1     | Write enable         |
| paddr   | Input     | 8     | Address              |
| pwdata  | Input     | 32    | Write data           |
| prdata  | Output    | 32    | Read data            |
| pready  | Output    | 1     | Ready                |

### 3.3 Interrupt Interface

| Signal   | Direction | Width | Description                 |
|----------|-----------|-------|-----------------------------|
| dma_done | Output    | 1     | Transfer complete interrupt |
| dma_err  | Output    | 1     | AXI error interrupt         |

---

## 4. Parameters

| Parameter  | Default | Description          |
|------------|---------|----------------------|
| DATA_WIDTH | 32      | AXI data width       |
| ADDR_WIDTH | 32      | AXI address width    |
| MAX_BURST  | 16      | Max AXI burst length |

---

## 5. Clocks and Resets

| Clock/Reset | Type        | Frequency     | Notes                                  |
|-------------|-------------|---------------|----------------------------------------|
| aclk        | Clock       | 100–200 MHz   | AXI clock domain                       |
| pclk        | Clock       | 50–100 MHz    | APB clock domain                       |
| aresetn     | Reset       | —             | Async active-low; de-asserted sync to aclk |
| presetn     | Reset       | —             | Sync active-low; synchronous to pclk  |

---

## 6. Operating Modes

| Mode            | Description                                               |
|-----------------|-----------------------------------------------------------|
| Idle            | No transfer in progress                                   |
| Active Transfer | DMA moving data from source to destination               |
| Error State     | AXI error received; requires software clear to recover   |

---

## 7. Compliance

- AXI4 (AMBA AXI and ACE Protocol Specification, ARM IHI0022)
- APB v2.0

---

## 8. Constraints / Limitations

| # | Constraint                                             |
|---|--------------------------------------------------------|
| 1 | Only memory-to-memory transfers supported              |
| 2 | Single outstanding transaction at a time               |
| 3 | Source and destination addresses must be word-aligned  |

---

## 9. DV-Relevant Notes

- **Transfer size range:** 1–65535 bytes — boundary values (1, 65535) and mid-range should be covered in tests.
- **Burst length range:** 1–16 beats (INCR only) — test min, max, and intermediate burst lengths.
- **No scatter-gather** — any attempt to exercise SG-like behavior is out of scope.
- **Single outstanding transaction** — back-to-back transaction overlap is an illegal scenario to verify is rejected/gated.
- **Word alignment requirement** — unaligned address corner cases should be tested for error handling.
- **Error state recovery** — software clear mechanism must be verified; error interrupt (dma_err) must assert.
- **Interrupt coverage** — both dma_done and dma_err interrupts must be stimulated and checked.
- **Clock domain crossing** — aclk and pclk are independent domains; CDC paths should be identified and constrained.
- **Reset behavior** — aresetn is async assert / sync de-assert; presetn is fully synchronous; both reset sequences must be tested.
