# UVM Error Patterns — message id catalog

Lookup table for common UVM `[TAG]` ids seen in sim logs. Use this during Phase 2 (log triage) and Phase 3 (classification) to accelerate diagnosis.

## Configuration / build

| Tag | Typical cause | First question |
|-----|---------------|----------------|
| `CFGNTS` | `uvm_config_db::get` found nothing | Which component+field? Was `set` called before `get`'s phase? |
| `NOMATCHC` | Config get had wrong inst path | Does the hierarchy in the `get` match the `set` glob? |
| `ILLBRDCST` | Wildcard `set` collided with another | Two sets for the same field at the same level? |
| `BDTYP` | Config type mismatch | `set` type vs `get` type must match exactly. |

## Factory / overrides

| Tag | Typical cause | First question |
|-----|---------------|----------------|
| `OVRDFAIL` | Factory override for wrong type/inst | Did override happen before `create()`? |
| `TYPNOTREG` | Type not registered with factory | Missing `` `uvm_object_utils `` ? |
| `INSTOVRD` | Instance override shadowed by type | Expected override applied? |

## Phases / objections

| Tag | Typical cause | First question |
|-----|---------------|----------------|
| `OBJTN_CLEAR` | All objections dropped before run complete | Who lowered the last objection? Drain time? |
| `PH_TIMEOUT` | Phase exceeded timeout | What held the phase? Check objection trace. |
| `PHSEQ` | Phase ordering error | Access before the phase it's valid in? |
| `OBJTN_LOCKED` | Objection count stuck | Which component holds it? |

## Sequencer / driver

| Tag | Typical cause | First question |
|-----|---------------|----------------|
| `SQRBUSY` | Sequence requested while another active | Priority? Parallel sequences using same sequencer? |
| `NOMATCHU` | `uvm_resource_db::read_by_name` miss | Name typo? Scope? |
| `NORSP` | Driver never returned response item | Driver forgot `item_done()` / `put_response()`. |
| `SEQITEMTO` | Seq waited too long for item | Driver stalled; check `get_next_item` loop. |

## Reporting / verbosity

| Tag | Typical cause | First question |
|-----|---------------|----------------|
| `RCVPH` | Report called from wrong phase | Message sourced after `check_phase`. |
| `REPORT_MSG` | Plain UVM_ERROR with custom id | Inspect the message body for domain tag. |

## Common VIP-side tags (check the VIP package)

AMBA AXI VIP commonly emits:
- `AXI4_ERRS_AWVALID_STABLE`
- `AXI4_ERRS_ARVALID_STABLE`
- `AXI4_ERRS_RLAST`
- `AXI4_ERRS_WDATA_NUM`
- `AXI4_ERRS_BRESP_SLVERR` / `AXI4_ERRS_BRESP_DECERR`
- `AXI4_ERRS_RRESP_SLVERR` / `AXI4_ERRS_RRESP_DECERR`

These point to DUT protocol violations — strong RTL bias unless the TB is generating illegal stimulus.

## Custom / project-specific tags

When an unknown tag appears, search the DV directory:
```
grep -rn "\"<TAG>\"" <dv_root>/
```
The literal usually sits in a `uvm_error` / `uvm_fatal` call with a descriptive message. Read that call site and the enclosing method to understand intent.
