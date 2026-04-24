# Playbook — TLP Layer (Transaction Layer Packet)

IP triggers: hierarchy contains `tl_`, `u_tl`, module name begins `tl_`, message id in `PCIE_TLP_MALFORMED`, `PCIE_POISONED_TLP`, `PCIE_COMPLETION_TIMEOUT`.

## Steps

1. **Capture the offending TLP.** From waveform, sample `tl_rx_data` (and `tl_rx_valid`) for the 16-32 DW around `fail_time`.

2. **Decode the header.** First DW bits `[31:29]` = FMT, `[28:24]` = TYPE. Cross-check against the FMT/TYPE table in `protocol_spec_cheatsheet.md`.

3. **Validate invariants.**
   - FMT vs TYPE combo is a legal row of the spec table.
   - `Length` field matches number of data DWs actually transmitted.
   - Reserved bits are zero.
   - If completion: `Requester ID`, `Tag`, `Completer ID`, `Byte Count` self-consistent.
   - If request: `Address` aligned per `Length`; 4KB boundary not crossed (ECN).

4. **If completion timeout:**
   - Find the original request in the upstream waveform (`tl_tx_data`).
   - Was a completion ever received for that Tag? If no → endpoint issue. If yes late → latency budget exceeded.

5. **If poisoned TLP:**
   - EP bit set. Trace where the poison was inserted — usually AXI4 `xresp=SLVERR` converted to poison.

6. **Classify.**
   - Bad header from DUT → **RTL in TL transmit**.
   - Bad header received correctly and DUT flagged → **TB issue** (stimulus generating illegal TLP) OR link partner bug.
   - Completion never arrives → **external** (endpoint model / routing).

## Hypothesis examples

- "Malformed TLP: FMT=010 (3DW with data) paired with TYPE=00001 (reserved). Transmit-side TL bug; see `tl_tx_build.sv:187`."
- "Completion timeout on Tag=0x1A: request sent at 12us, no completion by 62us (50us timeout). Endpoint model unconfigured for this BDF."
