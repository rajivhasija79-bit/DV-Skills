# Playbook — LTSSM (Link Training State Machine)

IP triggers: hierarchy contains `ltssm`, module name begins `ltssm_`, message id contains `PCIE_LTSSM_STUCK`.

## Steps

1. **Identify the stuck state.** From waveform, read `ltssm_state` at `fail_time`. Decode the enum using the RTL's state-param file (search RTL for `localparam LTSSM_POLLING_ACTIVE` etc.).

2. **Identify the expected next state.** From `references/protocol_spec_cheatsheet.md`, the next state depends on current state:
   - `Detect.Quiet → Detect.Active` when `rx_detect` asserts.
   - `Polling.Active → Polling.Configuration` after 8 consecutive TS1 OS received.
   - `Polling.Configuration → Configuration.Linkwidth.Start` after TS2 exchange.
   - …

3. **Find the missing condition.** Look at the signal the FSM is *waiting on* and check whether it ever asserted in the window. Typical culprits:
   - `pipe_rx_valid` gaps (PHY bit-lock issue).
   - `ts1_detected` never fires (pattern recognizer bug).
   - Timer expiry before condition seen (`timeout_counter` check).

4. **Classify.**
   - Waiting signal never asserted + `pipe_phy_status` says bad → **RTL in PHY**.
   - Waiting signal asserted but LTSSM didn't advance → **RTL in LTSSM**.
   - FSM timed out legitimately because partner didn't respond → **TB config** (link partner model not configured).

5. **Hypothesis examples**
   - "LTSSM stuck in Polling.Active: only 3 TS1 OS received (rows 42–78), needs 8. PHY `rx_valid` had a 400ns gap at 120us."
   - "LTSSM advanced to Recovery repeatedly: `EI` detected at 3us cadence → receiver EQ settings off."

## Evidence to collect

- `ltssm_state` transitions with timestamps.
- `pipe_rx_valid` duty cycle over the training window.
- `ts1_count`, `ts2_count` if exposed.
- `timeout_counter` value at entry to stuck state.
