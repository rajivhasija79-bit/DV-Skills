---
name: dv-env-setup
description: |
  Design Verification skill that sets up the complete DV project environment for
  a hardware verification project. Generates directory scaffold, VCS Makefile with
  all switches, compilation flow, UVM testbench skeleton files, environment scripts,
  and synopsys_sim.setup. Output dv_env_data.json feeds downstream TB scaffold (S5).

  Use this skill whenever a user wants to:
  - Set up a new DV project directory and simulation environment
  - Generate a VCS Makefile with wave/coverage/log/plusarg switches
  - Create UVM testbench skeleton files (env, scoreboard, coverage, sequences, tests)
  - Generate proj.cshrc / proj.bashrc / .env environment setup scripts
  - Create synopsys_sim.setup, compile.f, regression.sh for VCS
  - Initialize the DV directory structure for a new IP or block
  - Run /dv-env-setup or S4 in the DV end-to-end flow

  Trigger on: "setup DV environment", "create DV project", "generate Makefile",
  "dv-env-setup", "/dv-env-setup", "S4", "set up simulation", "VCS Makefile",
  "create TB skeleton", "setup UVM environment", "initialize DV repo"
---

# DV Environment Setup — S4

You are acting as a senior DV infrastructure engineer setting up a complete UVM
verification environment from scratch. Your output is the foundation on which the
entire DV team will work. Correctness and completeness of the Makefile, environment
scripts, and UVM skeletons are critical.

---

## Step 0 — Check Environment (ALWAYS run first)

Run the shared environment checker before any other work:

```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s4 --install
```

**If Bash is not available in this session:**
- Inform the user: *"Note: Bash is not available. I will prepare all environment
  data interactively and write files using the Write tool. For automated generation,
  please grant Bash permission and re-run."*
- Continue with all steps — collect all data, then write files directly with the
  Write tool using the fallback path described in Step 7.

**Common scripts location:**
```
<REPO_ROOT>/skills/common/scripts/
  ├── check_environment.py      # dependency checker (run in Step 0)
  └── generate_env_setup.py     # environment file generator (run in Step 7)
```

---

## Step 1 — Scan for Existing Resources

Before gathering inputs, scan for files that may already exist and can be reused:

**Search for:**
- `dv_spec_summary.json` (S1 output) — provides interfaces, clocks, parameters
- `testplan.xlsx` or `dv_testplan_data.json` (S2 output) — provides test list
- `dv_verif_plan_data.json` (S3 output) — provides TB architecture info
- Any existing `Makefile`, `compile.f`, `synopsys_sim.setup`
- Any coding guidelines document (`.md`, `.docx`, `.pdf`)
- Any existing `proj.cshrc` or `proj.bashrc`

**For each file found, ask the user before using it:**
> "I found `<path>`. Would you like me to use this as a reference? [y/n]"

Do NOT use any found file without explicit user confirmation.
Ask about all found files in a **single message**.

---

## Step 2 — Gather Required Inputs

After scanning, confirm all required inputs. Ask for missing ones in a
**single message** — never one at a time.

### Required inputs

| Input | Description | If Missing |
|---|---|---|
| `PROJECT_NAME` | Block/IP name in lowercase with underscores (e.g. `apb_uart`, `axi_dma`) | Ask user |
| `PROJECT_ROOT` | Absolute path where the DV directory will be created | Ask: *"Where should the project be created? Provide full path."* |
| `VCS_HOME` | Path to VCS installation (e.g. `/tools/synopsys/vcs/T-2022.06`) | Ask user. If not known: `<VCS_HOME>` placeholder |
| `VERDI_HOME` | Path to Verdi installation | Ask user. Default to `<VERDI_HOME>` placeholder |
| `UVM_HOME` | Path to UVM source library | Ask user. Default to `<UVM_HOME>` placeholder |
| `UVM_VERSION` | UVM version string for VCS `-ntb_opts` (e.g. `1.2`, `1800.2-2020`) | Default: `1.2` |
| `LICENSE_SERVER` | License server string (e.g. `7280@licserver`) | Ask user. Default: `<LICENSE_SERVER>` |

### Optional inputs (ask user, proceed with defaults if not provided)

| Input | Description | Default |
|---|---|---|
| `RTL_ROOT` | Path to RTL source files | `<PROJECT_ROOT>/rtl` |
| `RTL_FILES` | List of RTL files to add to `rtl.f` | Empty (user fills later) |
| `EXTRA_COMPILE_FLAGS` | Any project-specific VCS compile flags | Empty |
| `EXTRA_SIM_FLAGS` | Any project-specific simv flags | Empty |
| `REGRESSION_TESTS` | Initial list of test names for regression | `[sanity]` |
| `REGRESSION_SEEDS` | Seeds for regression runs | `[1, 2, 3, 4, 5]` |
| `DV_REPO_URL` | Git repo URL for the DV project | Empty |

---

## Step 3 — Gather Team and Resource Info (Interactive)

Ask the user for additional information to populate environment files.
Ask all questions in a **single message**:

1. **Interfaces from S1**: If `dv_spec_summary.json` is available, list the interfaces found.
   Ask: *"I found these interfaces: [list]. Should I create placeholder agents for each? [y/n per interface]"*

2. **Additional VCS options**: Ask: *"Are there any project-specific compile or
   simulation options you always use? (e.g. PLI, DPI libraries, special defines)"*

3. **Tool versions**: Ask: *"What VCS and Verdi version are you using? (e.g. VCS T-2022.06,
   Verdi T-2022.06) — needed for correct flag compatibility"*

4. **Coverage model**: Ask: *"Which coverage types should be collected by default?
   - line+cond+branch+tgl+fsm (recommended — full coverage)
   - line+cond+branch only
   - Custom — specify"*
   Default: `line+cond+branch+tgl+fsm`

5. **Timescale**: Ask: *"What timescale should the TB use? Default: `1ns/1ps`"*

6. **Default timeout**: Ask: *"What should the default UVM_TIMEOUT be? Default: `1ms`"*

---

## Step 4 — Confirm Directory Structure

Present the directory structure that will be created and ask for confirmation:

```
<PROJECT_ROOT>/
├── rtl/                          ← RTL sources (you add files here)
├── dv/
│   ├── tb/                       ← TB top, interfaces
│   ├── env/                      ← UVM env, scoreboard, coverage
│   ├── seq_lib/                  ← Sequences, tests
│   ├── agents/                   ← Agent subdirectories (one per protocol)
│   ├── sim/                      ← Simulation scripts
│   │   ├── Makefile              ← Main Makefile (all targets + switches)
│   │   ├── compile.f             ← TB file list for vlogan
│   │   ├── rtl.f                 ← RTL file list for vlogan
│   │   ├── synopsys_sim.setup    ← VCS library mapping
│   │   ├── waves.tcl             ← Verdi waveform capture TCL
│   │   ├── regression.sh         ← Regression runner script
│   │   ├── build/                ← Shared compiled simv (created at compile time)
│   │   ├── run/                  ← Per-test run dirs: run/<TEST>_<SEED>/
│   │   └── cov/                  ← Per-test coverage VDBs
│   ├── scripts/                  ← DV utility scripts
│   └── cov/                      ← Coverage closure workarea
├── proj.cshrc                    ← C-shell environment setup
├── proj.bashrc                   ← Bash environment setup
└── .env                          ← Dotenv (for CI/containerized flows)
```

Ask: *"Does this structure look correct? Any modifications needed?"*
Apply any requested changes before proceeding.

---

## Step 5 — Assemble Environment Data JSON

Write all gathered information to `/tmp/<project_name>_env_config.json`:

```json
{
  "project_name":        "<PROJECT_NAME>",
  "project_root":        "<PROJECT_ROOT>",
  "generated_by":        "dv-env-setup",
  "date":                "<YYYY-MM-DD>",
  "vcs_home":            "<VCS_HOME>",
  "verdi_home":          "<VERDI_HOME>",
  "uvm_home":            "<UVM_HOME>",
  "uvm_version":         "1.2",
  "license_server":      "<LICENSE_SERVER>",
  "vcs_version":         "<VCS_VERSION>",
  "verdi_version":       "<VERDI_VERSION>",
  "timescale":           "1ns/1ps",
  "default_timeout":     "1ms",
  "coverage_types":      "line+cond+branch+tgl+fsm",
  "rtl_files":           [],
  "extra_compile_flags": "",
  "extra_sim_flags":     "",
  "regression_tests":    ["sanity"],
  "regression_seeds":    [1, 2, 3, 4, 5],
  "interfaces":          [],
  "dv_repo_url":         "",
  "sources_used":        []
}
```

If S1/S2/S3 JSON was provided, populate `interfaces` from spec data and
`regression_tests` from testplan tests (DV-I tests only for initial regression).

---

## Step 6 — Interactive Debug & Sign-off Section

Before generating files, ask for project-specific customizations:

**Debug hints to add to Makefile help:**
Ask: *"Any project-specific debug tips to add to the Makefile help text?
(e.g. 'always run with +UVM_VERBOSITY=UVM_HIGH when debugging X')"*

**Custom plusargs:**
Ask: *"Are there any project-specific plusargs or value-plusargs your team
always uses? I can add them as commented examples in the Makefile."*

**Waveform scope:**
Ask: *"Should the waves.tcl dump ALL signals from tb_top (can be large),
or limit to specific scopes? Default: dump all from tb_top"*

---

## Step 7 — Generate All Files via Common Script

Run the shared environment generation script:

```bash
python3 <REPO_ROOT>/skills/common/scripts/generate_env_setup.py \
  --config /tmp/<project_name>_env_config.json
```

This generates all files listed in Step 4 plus `dv_env_data.json` for S5+.

**If Bash is unavailable**, write each file directly using the Write tool.
Generate the following files in order (use exact content from the templates
embedded in `generate_env_setup.py` as a reference):

1. `<PROJECT_ROOT>/proj.cshrc` — setenv for VCS_HOME, VERDI_HOME, UVM_HOME,
   PROJECT_ROOT, DV_ROOT, RTL_ROOT, SIM_ROOT, PATH, LD_LIBRARY_PATH, aliases
2. `<PROJECT_ROOT>/proj.bashrc` — export equivalents of above
3. `<PROJECT_ROOT>/.env` — KEY=VALUE pairs for CI/docker
4. `<PROJECT_ROOT>/dv/sim/synopsys_sim.setup` — WORK library mapping
5. `<PROJECT_ROOT>/dv/sim/rtl.f` — stub with +incdir+${RTL_ROOT}
6. `<PROJECT_ROOT>/dv/sim/compile.f` — UVM + TB file list
7. `<PROJECT_ROOT>/dv/sim/Makefile` — full Makefile (see Makefile Spec below)
8. `<PROJECT_ROOT>/dv/sim/waves.tcl` — fsdbDumpfile + fsdbDumpvars
9. `<PROJECT_ROOT>/dv/sim/regression.sh` — bash runner with PASS/FAIL tracking
10. `<PROJECT_ROOT>/dv/tb/<project>_tb_top.sv` — UVM module with run_test()
11. `<PROJECT_ROOT>/dv/tb/<project>_if.sv` — interface placeholder
12. `<PROJECT_ROOT>/dv/env/<project>_env_pkg.sv` — package with `include chain
13. `<PROJECT_ROOT>/dv/env/<project>_env_cfg.sv` — uvm_object config
14. `<PROJECT_ROOT>/dv/env/<project>_scoreboard.sv` — uvm_scoreboard skeleton
15. `<PROJECT_ROOT>/dv/env/<project>_coverage.sv` — uvm_subscriber skeleton
16. `<PROJECT_ROOT>/dv/env/<project>_env.sv` — uvm_env with build/connect
17. `<PROJECT_ROOT>/dv/seq_lib/<project>_base_seq.sv` — base sequence
18. `<PROJECT_ROOT>/dv/seq_lib/<project>_base_test.sv` — base test with report_phase
19. `<PROJECT_ROOT>/dv/seq_lib/<project>_sanity_test.sv` — first DV-I test

**NEVER overwrite an existing file.** Skip with a warning if file already exists.

---

## Makefile Specification

The Makefile MUST implement all of the following. This is the core deliverable.

### Variables (all overridable from command line)

```makefile
PROJECT    := <project_name>
SIM_ROOT   := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BUILD_DIR  ?= $(SIM_ROOT)/build       # shared build — NOT per-test
RUN_BASE   ?= $(SIM_ROOT)/run
COV_BASE   ?= $(SIM_ROOT)/cov
TEST       ?= sanity
SEED       ?= 1
RUN_DIR    := $(RUN_BASE)/$(TEST)_$(SEED)
COV_DIR    := $(COV_BASE)/$(TEST)_$(SEED).vdb
VCS_HOME   ?= <path>
VERDI_HOME ?= <path>
UVM_HOME   ?= <path>
UVM_VER    ?= 1.2
WAVES      ?= 0    # 0=off, 1=dump FSDB via waves.tcl
COV        ?= 0    # 0=off, 1=collect line+cond+branch+tgl+fsm
LOG        ?= 1    # 0=off, 1=write simv.log in RUN_DIR
TCL        ?= $(SIM_ROOT)/waves.tcl
PLUSARGS   ?=      # extra plusargs:        +arg1+arg2
VPLUSARGS  ?=      # extra value-plusargs:  +key1+val1
DEFINES    ?=      # extra defines:         +define+MACRO
SIM_OPTS   ?=      # extra simv options
COMP_OPTS  ?=      # extra compile options
VERBOSITY  ?= UVM_MEDIUM
TIMEOUT    ?= 1ms
```

### Compile flags

```makefile
VCS_COMMON_FLAGS := -full64 -sverilog -sv -timescale=$(TIMESCALE) -kdb -lca \
                    +incdir+$(UVM_HOME)/src \
                    -ntb_opts uvm-$(UVM_VER) $(COMP_OPTS)
VLOGAN_RTL_FLAGS := $(VCS_COMMON_FLAGS) $(DEFINES) -f $(SIM_ROOT)/rtl.f
VLOGAN_TB_FLAGS  := $(VCS_COMMON_FLAGS) $(DEFINES) -f $(SIM_ROOT)/compile.f
ELAB_FLAGS       := -full64 -kdb -lca -o $(BUILD_DIR)/simv \
                    -Mdir=$(BUILD_DIR)/csrc -debug_access+all
```

### Conditional flags

```makefile
# WAVES=1 → add -ucli -do $(TCL) +fsdb+delta +vcs+vcdpluson
# COV=1   → add -cm line+cond+branch+tgl+fsm at elab + simv
# LOG=1   → add -l $(RUN_DIR)/simv.log
```

### Targets (all required)

| Target | Description |
|---|---|
| `help` | Box-formatted help listing ALL targets and ALL options with examples |
| `show_config` | Print current values of all Makefile variables |
| `compile_rtl` | `vlogan` RTL files only ($(VLOGAN_RTL_FLAGS)) |
| `compile_tb` | `vlogan` TB files, depends on compile_rtl |
| `elab` | `vcs` elaborate → `$(BUILD_DIR)/simv`, depends on compile_tb |
| `compile` | Full: compile_rtl + compile_tb + elab |
| `sim` | Run `$(BUILD_DIR)/simv $(SIM_FLAGS)` in `$(RUN_DIR)`. Error if simv missing |
| `run` | `compile` then `sim` |
| `regress` | Run `regression.sh` |
| `cov_merge` | `urg -dir $(COV_BASE)/*.vdb -report urgReport -format both` |
| `cov_report` | Open Verdi coverage viewer with merged VDB |
| `verdi` | Open Verdi with FSDB for TEST/SEED. Warn if FSDB missing |
| `clean_logs` | `find $(RUN_BASE) -name "*.log" -delete` |
| `clean_run` | `rm -rf $(RUN_BASE)` |
| `clean_cov` | `rm -rf $(COV_BASE)` |
| `clean_build` | `rm -rf $(BUILD_DIR)` |
| `clean` | clean_run + clean_cov + clean_build + remove *.fsdb *.vpd ucli.key |

**Critical:** `BUILD_DIR` is shared. Multiple `make sim TEST=x` calls after one
`make compile` all use the same `$(BUILD_DIR)/simv`. Never put build artifacts
inside `$(RUN_DIR)`.

---

## Step 8 — Write dv_env_data.json

Write `/tmp/<project_name>_env_data_output.json` with the output schema
consumed by S5 (dv-tb-scaffold) and all later skills:

```json
{
  "project_name":     "<name>",
  "project_root":     "<path>",
  "generated_by":     "dv-env-setup",
  "date":             "<YYYY-MM-DD>",
  "tool":             "vcs",
  "vcs_home":         "<path>",
  "verdi_home":       "<path>",
  "uvm_home":         "<path>",
  "uvm_version":      "1.2",
  "license_server":   "<server>",
  "directory_structure": {
    "dv_root":      "<proj>/dv",
    "tb_root":      "<proj>/dv/tb",
    "env_root":     "<proj>/dv/env",
    "seq_root":     "<proj>/dv/seq_lib",
    "agents_root":  "<proj>/dv/agents",
    "sim_root":     "<proj>/dv/sim",
    "scripts_root": "<proj>/dv/scripts",
    "build_dir":    "<proj>/dv/sim/build",
    "run_base":     "<proj>/dv/sim/run",
    "cov_base":     "<proj>/dv/sim/cov"
  },
  "key_files": {
    "makefile":           "<proj>/dv/sim/Makefile",
    "compile_f":          "<proj>/dv/sim/compile.f",
    "rtl_f":              "<proj>/dv/sim/rtl.f",
    "synopsys_sim_setup": "<proj>/dv/sim/synopsys_sim.setup",
    "waves_tcl":          "<proj>/dv/sim/waves.tcl",
    "regression_sh":      "<proj>/dv/sim/regression.sh",
    "proj_cshrc":         "<proj>/proj.cshrc",
    "proj_bashrc":        "<proj>/proj.bashrc"
  },
  "tb_skeleton_files": ["<list of all generated .sv files>"],
  "compile_command":    "make -C <proj>/dv/sim compile",
  "sim_command":        "make -C <proj>/dv/sim sim TEST=sanity SEED=1",
  "regression_command": "make -C <proj>/dv/sim regress",
  "env_vars": {
    "PROJECT_ROOT": "<path>",
    "PROJECT_NAME": "<name>",
    "DV_ROOT":      "<path>",
    "RTL_ROOT":     "<path>",
    "SIM_ROOT":     "<path>",
    "VCS_HOME":     "<path>",
    "VERDI_HOME":   "<path>",
    "UVM_HOME":     "<path>",
    "UVM_VERSION":  "1.2"
  }
}
```

---

## Step 9 — Print Terminal Summary

```
============================================================
  DV Environment Setup — Complete
  Project   : <PROJECT_NAME>
  Root      : <PROJECT_ROOT>
------------------------------------------------------------
  Generated:
    Directories      : N
    Env files        : 3  (proj.cshrc, proj.bashrc, .env)
    VCS sim files    : 6  (Makefile, compile.f, rtl.f,
                           synopsys_sim.setup, waves.tcl,
                           regression.sh)
    UVM TB skeletons : 10
------------------------------------------------------------
  Quick start:
    source <PROJECT_ROOT>/proj.cshrc        [or proj.bashrc]
    cd <PROJECT_ROOT>/dv/sim
    make compile                            [after adding RTL to rtl.f]
    make sim TEST=sanity SEED=1 WAVES=1
    make verdi TEST=sanity SEED=1
    make regress
    make cov_merge && make cov_report
------------------------------------------------------------
  Key Makefile options:
    TEST=<name>  SEED=<N>  WAVES=0/1  COV=0/1  LOG=0/1
    VERBOSITY=UVM_MEDIUM  TIMEOUT=1ms
    PLUSARGS="+arg"  VPLUSARGS="+k+v"  DEFINES="+define+M"
------------------------------------------------------------
  Next step: run /dv-tb-scaffold (S5) to generate agents
             and sequences for each interface
============================================================
```

---

## Important Notes

- **Shared build is mandatory**: `BUILD_DIR` must be outside `RUN_DIR`.
  One compile → many test runs. This is non-negotiable for DV efficiency.
- **VCS two-step compile**: `vlogan` (compile) + `vcs` (elaborate) is the
  correct flow for projects. `make compile_rtl` and `make compile_tb` use
  `vlogan`; `make elab` uses `vcs`.
- **`make help` must be the default goal** — running `make` with no args should
  print help, not start compilation.
- **Never overwrite existing files** — check with `if p.exists()` and skip.
- **Skeleton files are placeholders** — mark all TODOs clearly so engineers
  know exactly what to fill in.
- **Makefile tab indentation**: All recipe lines MUST start with a real TAB,
  not spaces. This is a hard Make requirement.
- If any inputs are still unknown after asking, use `<PLACEHOLDER>` values
  with clear comments marking them for replacement.
