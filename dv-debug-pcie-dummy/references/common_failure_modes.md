# PCIe Common Failure Modes (DEMO)

Map from observable symptom to candidate root cause. In a real skill, this is the cross-reference you load before forming hypotheses.

## Link won't reach L0

| Observed | Candidate causes |
|----------|------------------|
| Stuck in `Detect.Quiet` | Receiver detection never triggered — PIPE `rx_detect` stuck, or `rx_valid` never asserts |
| Stuck in `Polling.Active` | < 8 consecutive TS1s seen; bit-lock or symbol-lock issue |
| Stuck in `Polling.Configuration` | TS1 seen but TS2 exchange not completed |
| Drops to `Recovery.RcvrLock` repeatedly | Margin / EQ issue; PRBS BER too high |
| `Disabled` after attempts | LTSSM reached max retries |

## Once in L0

| Observed | Candidate causes |
|----------|------------------|
| Completion timeout | Endpoint not responding; ID mismatch; routing wrong |
| Malformed TLP error | FMT/TYPE illegal combo; length mismatch; reserved bits set |
| Credit underflow | Flow-control init miss; UpdateFC DLLPs dropped |
| Poisoned TLP | EP bit set — upstream signaled corrupt data |
| CRC error on TLP | ECRC wrong, or LCRC from DLL mismatched |

## Signal probes to start with (DEMO)

Minimum signal set for LTSSM debug:
- `ltssm_state`
- `pipe_rx_valid`, `pipe_rx_data`, `pipe_rx_k`
- `pipe_tx_valid`, `pipe_tx_data`, `pipe_tx_k`
- `pipe_phy_status`, `pipe_reset_n`
- `link_up`
