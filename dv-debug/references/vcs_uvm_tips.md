# VCS + UVM Tips — plusargs, flags, backtrace reading

Quick reference for VCS-specific knobs and how to read what they produce.

## Runtime plusargs (for rerun with richer info)

| Plusarg | Effect | When to use |
|---------|--------|-------------|
| `+UVM_VERBOSITY=UVM_HIGH` | Globally raise verbosity | Too little info in the log to classify |
| `+uvm_set_verbosity=uvm_test_top.env.u_sb,_ALL_,UVM_FULL,run` | Per-component verbosity | Narrow noise; get detail only where needed |
| `+UVM_MAX_QUIT_COUNT=1` | Quit on first UVM_ERROR | Stop after first failure for clean sig |
| `+UVM_OBJECTION_TRACE` | Dump objection raise/drop | Hang debug — always add this on rerun |
| `+UVM_PHASE_TRACE` | Dump phase transitions | Phase-order bugs |
| `+UVM_CONFIG_DB_TRACE` | Dump `config_db` set/get | `CFGNTS` / `NOMATCHC` |
| `+UVM_RESOURCE_DB_TRACE` | Dump resource set/get | Resource-db misses |
| `+UVM_NO_RELNOTES` | Suppress the banner | Small log cleanup |

## Compile flags (VCS)

| Flag | Effect | When |
|------|--------|------|
| `-debug_access+all` | Enables read/write/force for Verdi | Always for debug builds |
| `-kdb` | Emits the Knowledge Database for Verdi-native RTL debug | Required for modern Verdi debug |
| `-fsdb` / use `pli=novas.tab` | Enable FSDB dumping | When producing `.fsdb` |
| `+define+UVM_NO_DEPRECATED` | Strict mode | Catch deprecated-API misuse early |
| `-assert svaext` | SVA extensions | For concurrent assertion features |
| `-cm line+cond+fsm+branch+tgl+assert` | Coverage | If coverage triage needed |

## Reading a UVM backtrace

```
UVM_ERROR @ 123456 ns: reporter [UVM/REPORT/FATAL] Fatal message here
    uvm_pkg::uvm_report_object::uvm_report (uvm_report_object.svh:120)
    my_env::my_driver::drive_item (my_driver.sv:78)
    my_env::my_driver::run_phase (my_driver.sv:52)
```

- Top line: the report call. Extract `message_id` from the bracketed tag.
- Each subsequent line is a stack frame. The *first line outside UVM source files* is the component method that triggered the error — that's your starting `file:line`.
- If the stack is truncated, rerun with `+UVM_VERBOSITY=UVM_FULL` or capture a core dump.

## Common VCS error prefixes

| Prefix | Meaning |
|--------|---------|
| `Error-[<TAG>]` | VCS tool-level error (compile/elab/runtime) |
| `Warning-[<TAG>]` | VCS warning |
| `TFIPC-L` | Timing violation (when `-timing` used) |

`Error-[...]` near the start of the log is usually **elaboration-time** — suspect Config/Env, not RTL/TB.

## Reproducing a run

Record (for the Phase 7 JIRA draft):
- Exact `simv` path + command line
- `+seed=<value>` (always capture)
- All plusargs
- Commit / build id
- Tool version (`simv -version`)
- Host OS / arch

Without the seed, a failure is not reproducible and the JIRA is weak.
