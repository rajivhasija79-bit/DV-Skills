# PCIe Protocol Cheat-Sheet (DEMO — minimal)

A real domain skill has a full reference here. This file is a stub to show the structure.

## LTSSM states (PCIe base spec)

```
Detect → Polling → Configuration → L0 (active)
                                    ├→ L0s
                                    ├→ L1 → L2
                                    └→ Recovery → L0 | Hot Reset | Disabled
```

Each state has sub-states (`.Active`, `.Quiet`, `.Speed`, `.Idle`, …). The full state table is in PCIe base spec chapter 4.2; in a real skill, copy the relevant subset here.

## TLP header quick format (32b fields, 3DW/4DW)

| Field | DW 0 | Notes |
|-------|------|-------|
| FMT[2:0] | `[31:29]` | 000=3DW no-data, 001=4DW no-data, 010=3DW with data, 011=4DW with data |
| TYPE[4:0] | `[28:24]` | MRd=0, MWr=0, CplD=0xA, etc. |
| Length[9:0] | `[9:0]` | DW count |

Real skill: full table from PCIe base spec ch. 2.2.

## Flow control credits

- **Posted, Non-Posted, Completion** — three credit pools.
- Header credits and data credits counted separately.
- UpdateFC DLLPs transmit credit updates.
- Underflow = sender transmitted a TLP with insufficient credit = protocol violation.

## Common symptom → IP map

| Symptom | Likely IP |
|---------|-----------|
| Link training hangs | LTSSM / PIPE PHY |
| Malformed TLP | TL layer / link partner |
| CRC errors | DLL layer / physical |
| Completion timeout | Upper-stack / endpoint |
| Credit underflow | DLL flow-control |
| 8b/10b or 128b/130b errors | PIPE / SerDes |
