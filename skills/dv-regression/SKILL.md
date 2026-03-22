---
name: dv-regression
description: |
  Design Verification skill (S9) that generates a complete regression
  infrastructure: milestone test lists, parallel regression runner with
  grid support, VCS log parser, HTML regression report, and VCS/Verdi
  coverage merge. Reads test inventory from S6 dv_sequences_data.json
  and build/sim commands from S4/S5.

  Use this skill whenever a user wants to:
  - Generate DV regression test lists (DV-I / DV-C / DV-F)
  - Run regression with keyword-based test selection
  - Set up parallel regression on a compute grid (LSF/SGE/Slurm/custom)
  - Generate an HTML regression report with CHK_ID failure details
  - Merge VCS coverage databases and generate coverage report
  - Run /dv-regression or S9 in the DV end-to-end flow

  Trigger on: "run regression", "generate testlist", "dv-regression",
  "/dv-regression", "S9", "regression runner", "run all tests",
  "coverage merge", "regression report", "failing tests"
---

# DV Regression Infrastructure Generator — S9

You are acting as a senior DV engineer with extensive regression automation
experience. The regression system must be robust, grid-aware, and produce
clear actionable reports. It must handle partial failures gracefully and
never stop collecting results just because some tests fail.

---

## Generated File Layout

```
dv/
  sim/
    regression/
      dv_i_reglist.f          ← DV-I milestone test list
      dv_c_reglist.f          ← DV-C milestone test list
      dv_f_reglist.f          ← DV-F milestone test list (complete)
      full_reglist.f          ← all tests across all milestones
    results/                  ← created at runtime per regression run
      <YYYYMMDD_HHMMSS>/
        <test>_s<seed>/
          sim.log
          result.json
        regression_summary.html
        regression_summary.txt
        coverage/             ← merged VCS coverage

<REPO_ROOT>/skills/common/scripts/
  run_regression.py           ← parallel regression runner
  parse_sim_log.py            ← VCS log parser
  gen_regression_report.py    ← HTML report generator
  merge_coverage.py           ← VCS urg + Verdi coverage merge
```

---

## Step 0 — Check Environment

```bash
python3 <REPO_ROOT>/skills/common/scripts/check_environment.py --skill s9 --install
```

---

## Step 1 — Gather Inputs

| Input | Location | Required? |
|---|---|---|
| `dv_sequences_data.json` | `<PROJECT_ROOT>/dv/` | **Required** — test inventory |
| `dv_tb_data.json` | `<PROJECT_ROOT>/dv/` | Required — project name, paths |
| `Makefile` | `<PROJECT_ROOT>/dv/sim/` | Required — sim/compile commands |
| `dv_scoreboard_data.json` | `<PROJECT_ROOT>/dv/` | Optional — CHK_ID list for report |

If `dv_sequences_data.json` missing — STOP:
```
⛔  S9 STOPPED — dv_sequences_data.json not found.
    Run /dv-sequences (S6) first to generate the test inventory.
```

---

## Step 2 — Grid Configuration (INTERACTIVE — always ask)

```
============================================================
  Grid Configuration
============================================================
  S9 generates a regression runner that can submit jobs to a
  compute grid. Please provide your grid setup:

  [G1] Grid type: LSF / SGE (GridEngine) / Slurm / PBS / Local / Other
       Enter: ___

  [G2] Job submission command template.
       Provide your bsub/qsub/sbatch command with placeholders:
       {job_name}  = test name + seed
       {log_file}  = path to sim.log
       {cmd}       = the actual sim command to run
       {queue}     = queue/partition name

       Example (LSF):
         bsub -J {job_name} -o {log_file} -e {log_file} -q {queue} "{cmd}"
       Example (SGE):
         qsub -N {job_name} -o {log_file} -e {log_file} -q {queue} -b y "{cmd}"
       Example (Slurm):
         sbatch --job-name={job_name} --output={log_file} --partition={queue} --wrap="{cmd}"

       Your template: ___

  [G3] Default queue/partition name: ___

  [G4] Job status check command (to poll if job is done):
       Example (LSF): bjobs -noheader {job_id}
       Example (SGE): qstat -j {job_id}
       Example (Slurm): squeue --job={job_id}
       Your command: ___

  [G5] Job kill command (for cleanup on Ctrl+C):
       Example (LSF): bkill {job_id}
       Example (SGE): qdel {job_id}
       Example (Slurm): scancel {job_id}
       Your command: ___

  [G6] Max parallel jobs: [default: 16] ___

  [G7] For LOCAL runs (no grid), max parallel processes: [default: 4] ___

  Type SKIP to run locally only (no grid support).
============================================================
```

Wait for answers. Store in `grid_config` dict. If SKIP, set `grid_type = "local"`.

---

## Step 3 — Seed Configuration

```
============================================================
  Seed Configuration for Random Tests
============================================================
  Random tests (test names ending in _rand_test) will be run
  with multiple random seeds. Directed tests always use SEED=1.

  [S1] Default number of seeds for random tests: [default: 5] ___

  [S2] Seeds per milestone:
       DV-I random tests : [default: 1 — sanity only] ___
       DV-C random tests : [default: 5] ___
       DV-F random tests : [default: 20] ___

  [S3] Seed generation: pure random (new seeds each run) [Y/N, default: Y] ___

  Type OK to accept all defaults.
============================================================
```

---

## Step 4 — Generate Test Lists

Parse `dv_sequences_data.json` → extract all tests with their milestones and plusargs.

### Test list file format (`dv_i_reglist.f`):

```
# =============================================================================
# DV-I Regression Test List — <PROJECT_NAME>
# Generated by S9 dv-regression — <date>
# Usage: python3 run_regression.py --reglist dv_i_reglist.f [--jobs N] [--seeds N]
# =============================================================================
# FORMAT: TEST=<name> SEEDS=<N> [PLUSARGS=<+arg1 +arg2 ...>] [MILESTONE=<DV-I|C|F>]
# Lines starting with # are comments. Blank lines are ignored.

# ── Directed tests (SEEDS=1) ─────────────────────────────────────────────────
TEST=<proj>_sanity_test             SEEDS=1  MILESTONE=DV-I
TEST=<proj>_apb_reg_write_test      SEEDS=1  MILESTONE=DV-I  PLUSARGS=+SB_ENABLE
TEST=<proj>_apb_reg_read_test       SEEDS=1  MILESTONE=DV-I
# ... one line per directed DV-I test

# ── Random tests (SEEDS=<milestone_default>) ──────────────────────────────────
TEST=<proj>_uart_tx_rand_test       SEEDS=1  MILESTONE=DV-I  PLUSARGS=+NUM_TXNS=50
```

Generate four files:
- `dv_i_reglist.f` — only DV-I tests
- `dv_c_reglist.f` — DV-I + DV-C tests
- `dv_f_reglist.f` — DV-I + DV-C + DV-F tests (full regression)
- `full_reglist.f` — symlink or copy of `dv_f_reglist.f`

**Keyword matching:** The runner supports `--test KEYWORD` which filters any
test list to lines where TEST name contains KEYWORD (case-insensitive).

---

## Step 5 — Generate Regression Runner

Script: `skills/common/scripts/run_regression.py`

Key behaviours:
- Reads `--reglist` file OR builds list dynamically with `--test KEYWORD` from dv_sequences_data.json
- Expands each SEEDS=N entry into N individual jobs with random seeds
- Submits jobs in parallel (grid or local subprocess pool)
- Never stops on failure — always runs all jobs (`--stop-on-fail` flag available but default OFF)
- Real-time progress bar: `[=====>    ] 45/100 PASS=40 FAIL=5 RUNNING=10`
- Per-test result stored in `results/<timestamp>/<test>_s<seed>/result.json`
- Calls `parse_sim_log.py` after each job completes
- Calls `gen_regression_report.py` at end
- Calls `merge_coverage.py` if `--cov` flag passed

### CLI:
```
run_regression.py
  --reglist   FILE          reglist .f file (mutually exclusive with --test)
  --test      KEYWORD       run all tests matching keyword (substring, case-insensitive)
  --seeds     N             override SEEDS for all tests [default: from reglist]
  --jobs      N             max parallel jobs [default: 16 grid / 4 local]
  --grid                    submit to grid (uses grid_config.json)
  --local                   force local execution
  --cov                     merge coverage after run
  --stop-on-fail            stop after first failure [default: OFF]
  --results   DIR           results directory [default: results/<timestamp>]
  --project   NAME          project name (for report header)
  --dv-root   DIR           path to dv/ root
  --tb-data   FILE          dv_tb_data.json path
  --seq-data  FILE          dv_sequences_data.json path
  --grid-cfg  FILE          grid_config.json path
```

### Runtime output format:
```
============================================================
  Regression Run: <PROJECT_NAME>
  Reglist      : dv_c_reglist.f
  Total jobs   : 47  (40 directed × 1 seed + 7 random × 1 seed)
  Grid         : LSF  queue=<queue>  max-jobs=16
  Results dir  : results/20260322_143022
============================================================
  [=========>        ] 47/47  PASS=43  FAIL=4  RUNNING=0
============================================================
  FAILED TESTS:
    uart_tx_rand_test SEED=7832641  → results/20260322_143022/uart_tx_rand_test_s7832641/sim.log
    apb_reg_write_test SEED=1       → results/20260322_143022/apb_reg_write_test_s1/sim.log
  ...
============================================================
  Coverage merge: urg running...
  Report: results/20260322_143022/regression_summary.html
============================================================
```

---

## Step 6 — Log Parser

Script: `skills/common/scripts/parse_sim_log.py`

Parses one VCS simulation log. Returns structured result JSON:

```json
{
  "test":          "<test_name>",
  "seed":          12345,
  "status":        "PASS",
  "uvm_fatal":     0,
  "uvm_error":     0,
  "uvm_warning":   3,
  "sim_time_ns":   1500.0,
  "chk_passes":    ["CHK_UART_APB_PROTOCOL_001", "CHK_UART_REG_CTRL_WRITE_001"],
  "chk_fails":     [],
  "sva_fails":     [],
  "exit_code":     0,
  "log_path":      "results/20260322_143022/uart_tx_test_s1/sim.log",
  "parse_errors":  []
}
```

Detection rules:
| Pattern | Action |
|---|---|
| `UVM_FATAL` | `uvm_fatal++`, status=FAIL |
| `UVM_ERROR` | `uvm_error++`, status=FAIL |
| `[PASS] CHK_` | extract CHK_ID → `chk_passes` |
| `[FAIL] CHK_` | extract CHK_ID → `chk_fails`, status=FAIL |
| `[FAIL] CHK_` in SVA `$error` | extract → `sva_fails`, status=FAIL |
| `UVM_TEST_DONE` | simulation completed normally |
| `$finish` called | simulation completed |
| No finish in log | status=FAIL (crashed/timeout) |

---

## Step 7 — HTML Regression Report Generator

Script: `skills/common/scripts/gen_regression_report.py`

Generates a self-contained single-file HTML report (inline CSS, no external deps).

### Report structure:
```
┌─────────────────────────────────────────────────────────┐
│  DV Regression Report — <PROJECT>  <timestamp>          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  TOTAL: 47 tests │ PASS: 43 (91.5%) │ FAIL: 4           │
│  Milestone: DV-I=10/10 ✓  DV-C=33/37 ✗  DV-F=0/0 -    │
├─────────────────────────────────────────────────────────┤
│  Failing Tests                                          │
│  ┌────────────────────┬──────┬──────┬───────────────┐  │
│  │ Test               │ Seed │ Errs │ Failed CHK_IDs │  │
│  ├────────────────────┼──────┼──────┼───────────────┤  │
│  │ uart_tx_rand_test  │78326 │  2   │ CHK_TX_001    │  │
│  └────────────────────┴──────┴──────┴───────────────┘  │
├─────────────────────────────────────────────────────────┤
│  All Tests (sortable table)                              │
│  ┌──────────────────┬──────┬────────┬──────┬────────┐  │
│  │ Test             │ Seed │ Status │ Errs │ Time   │  │
│  ├──────────────────┼──────┼────────┼──────┼────────┤  │
│  │ sanity_test      │  1   │ ✓ PASS │  0   │ 1.2ms  │  │
│  │ uart_tx_rand_test│78326 │ ✗ FAIL │  2   │ 45.3ms │  │
│  └──────────────────┴──────┴────────┴──────┴────────┘  │
├─────────────────────────────────────────────────────────┤
│  Rerun Commands                                          │
│  make sim TEST=uart_tx_rand_test SEED=78326             │
└─────────────────────────────────────────────────────────┘
```

Features:
- Self-contained HTML (no external CDN — works offline)
- Colour-coded: green=PASS, red=FAIL
- Sortable columns (JavaScript, inline)
- Expandable CHK_ID failure details per test (click to expand)
- "Rerun Commands" section: `make sim TEST=<name> SEED=<seed>` per failing test
- Milestone progress bars
- Coverage summary section (if `--cov-report` path provided)

---

## Step 8 — Coverage Merge Script

Script: `skills/common/scripts/merge_coverage.py`

```
merge_coverage.py
  --results   DIR           results directory from regression run
  --output    DIR           coverage output directory [default: results/coverage]
  --format    urg|verdi|both  coverage viewer [default: both]
  --dv-root   DIR           dv/ root (for compile.f and TB hierarchy)
```

Steps:
1. Find all `*.vdb` directories under `--results`
2. Build `urg` merge command:
   ```bash
   urg -full64 -dir <vdb1> -dir <vdb2> ... \
       -dbname merged_coverage \
       -report <output>/urg_report \
       -format both \
       -show summary
   ```
3. Run merge and capture output
4. Print coverage summary (line/toggle/branch/FSM/functional)
5. If `--format verdi` or `both`:
   ```bash
   verdi -cov -workdir merged_coverage &
   ```
6. Print:
   ```
   Coverage Summary:
     Line     : XX.X%
     Toggle   : XX.X%
     Branch   : XX.X%
     FSM      : XX.X%
     Functional: XX.X%
   ```

---

## Step 9 — Update Makefile

Append to `dv/sim/Makefile` (do NOT overwrite existing targets):

```makefile
# =============================================================================
# S9 Regression targets
# =============================================================================
SCRIPTS    ?= $(REPO_ROOT)/skills/common/scripts
RESULTS    ?= $(DV_ROOT)/sim/results
JOBS       ?= 16
SEEDS      ?= 5
DV_ROOT    ?= $(REPO_ROOT)/dv

## Run DV-I regression (basic milestone)
regress_dvi:
	python3 $(SCRIPTS)/run_regression.py \
	  --reglist $(DV_ROOT)/sim/regression/dv_i_reglist.f \
	  --jobs $(JOBS) --results $(RESULTS) \
	  --dv-root $(DV_ROOT) --project $(PROJECT)

## Run DV-C regression (intermediate milestone)
regress_dvc:
	python3 $(SCRIPTS)/run_regression.py \
	  --reglist $(DV_ROOT)/sim/regression/dv_c_reglist.f \
	  --jobs $(JOBS) --results $(RESULTS) \
	  --dv-root $(DV_ROOT) --project $(PROJECT)

## Run full DV-F regression
regress_full:
	python3 $(SCRIPTS)/run_regression.py \
	  --reglist $(DV_ROOT)/sim/regression/dv_f_reglist.f \
	  --jobs $(JOBS) --results $(RESULTS) \
	  --dv-root $(DV_ROOT) --project $(PROJECT)

## Run tests matching keyword: make regress_test TEST=DMA SEEDS=10
regress_test:
	python3 $(SCRIPTS)/run_regression.py \
	  --test $(TEST) --seeds $(SEEDS) --jobs $(JOBS) \
	  --results $(RESULTS) --dv-root $(DV_ROOT) --project $(PROJECT) \
	  --seq-data $(DV_ROOT)/dv_sequences_data.json

## Run on grid: make regress_grid REGLIST=dv_c_reglist.f
regress_grid:
	python3 $(SCRIPTS)/run_regression.py \
	  --reglist $(DV_ROOT)/sim/regression/$(REGLIST) \
	  --grid --grid-cfg $(DV_ROOT)/sim/grid_config.json \
	  --jobs $(JOBS) --results $(RESULTS) \
	  --dv-root $(DV_ROOT) --project $(PROJECT)

## Rerun single failing test: make rerun TEST=uart_tx_rand_test SEED=78326
rerun:
	$(MAKE) sim TEST=$(TEST) SEED=$(SEED) WAVES=1

## Generate HTML regression report from latest results
report:
	python3 $(SCRIPTS)/gen_regression_report.py \
	  --results $(shell ls -td $(RESULTS)/*/ | head -1) \
	  --output  $(shell ls -td $(RESULTS)/*/ | head -1)/regression_summary.html \
	  --project $(PROJECT)
	@echo "Report: $(shell ls -td $(RESULTS)/*/ | head -1)/regression_summary.html"

## Merge VCS coverage databases
cov_merge:
	python3 $(SCRIPTS)/merge_coverage.py \
	  --results $(shell ls -td $(RESULTS)/*/ | head -1) \
	  --output  $(shell ls -td $(RESULTS)/*/ | head -1)/coverage \
	  --format both

## Run regression + coverage in one command
regress_cov: regress_dvc cov_merge report
```

---

## Step 10 — Generate grid_config.json

Write `dv/sim/grid_config.json` with the user's grid answers from Step 2:

```json
{
  "grid_type":    "LSF",
  "submit_cmd":   "bsub -J {job_name} -o {log_file} -e {log_file} -q {queue} \"{cmd}\"",
  "status_cmd":   "bjobs -noheader {job_id}",
  "kill_cmd":     "bkill {job_id}",
  "default_queue":"<queue_from_user>",
  "max_jobs":     16,
  "local_max_jobs": 4,
  "poll_interval_sec": 10
}
```

If user typed SKIP → write with `"grid_type": "local"` and null for grid fields.

---

## Step 11 — Write dv_regression_data.json

```json
{
  "skill":          "dv-regression",
  "version":        "1.0",
  "project_name":   "<proj>",
  "generated_date": "<ISO date>",
  "test_lists": {
    "dv_i": "dv/sim/regression/dv_i_reglist.f",
    "dv_c": "dv/sim/regression/dv_c_reglist.f",
    "dv_f": "dv/sim/regression/dv_f_reglist.f",
    "full": "dv/sim/regression/full_reglist.f"
  },
  "test_counts": {
    "dv_i_directed": 0, "dv_i_random": 0,
    "dv_c_directed": 0, "dv_c_random": 0,
    "dv_f_directed": 0, "dv_f_random": 0,
    "total_tests":   0
  },
  "seed_config": {
    "directed_seeds": 1,
    "random_seeds_dvi": 1,
    "random_seeds_dvc": 5,
    "random_seeds_dvf": 20
  },
  "grid": { "<grid_config from Step 2>" },
  "scripts": {
    "runner":    "skills/common/scripts/run_regression.py",
    "parser":    "skills/common/scripts/parse_sim_log.py",
    "reporter":  "skills/common/scripts/gen_regression_report.py",
    "cov_merge": "skills/common/scripts/merge_coverage.py"
  }
}
```

---

## Step 12 — Terminal Summary

```
============================================================
  DV Regression Infrastructure — Complete
  Project : <PROJECT_NAME>
============================================================
  Test lists:
    DV-I   : regression/dv_i_reglist.f    (N tests)
    DV-C   : regression/dv_c_reglist.f    (N tests)
    DV-F   : regression/dv_f_reglist.f    (N tests)
    Full   : regression/full_reglist.f    (N tests)
------------------------------------------------------------
  Seed config:
    Directed    : 1 seed always
    Random DV-I : N seeds   DV-C: N seeds   DV-F: N seeds
------------------------------------------------------------
  Grid: <type>   queue=<queue>   max-jobs=N
    grid_config.json written to dv/sim/
------------------------------------------------------------
  Scripts:
    runner   : skills/common/scripts/run_regression.py
    parser   : skills/common/scripts/parse_sim_log.py
    reporter : skills/common/scripts/gen_regression_report.py
    cov_merge: skills/common/scripts/merge_coverage.py
------------------------------------------------------------
  Makefile targets added:
    make regress_dvi   make regress_dvc   make regress_full
    make regress_test TEST=<keyword> SEEDS=N
    make regress_grid  make rerun TEST=X SEED=N
    make report        make cov_merge     make regress_cov
------------------------------------------------------------
  Quick start:
    cd <PROJECT_ROOT>/dv/sim
    make regress_dvi                        # local DV-I
    make regress_grid REGLIST=dv_c_reglist.f  # grid DV-C
    make regress_test TEST=UART SEEDS=10    # keyword run
------------------------------------------------------------
  Next step: /dv-coverage-closure (S10)
============================================================
```

---

## Important Notes

- **Never stop on failure** — default is `--continue-on-fail`; all jobs always run
- **Keyword matching is case-insensitive substring** — `TEST=DMA` matches `dma_read_test`, `DMA_burst_rand_test`, etc.
- **SEEDS expansion** — a test with `SEEDS=5` generates 5 jobs with 5 different random seeds; seeds are generated with `random.randint(1, 2**31-1)` at job dispatch time
- **Directed tests always SEEDS=1** — test names NOT ending in `_rand_test` are always single seed
- **Grid job IDs** — store in `results/<timestamp>/jobs.json` for monitoring and cleanup
- **HTML report is self-contained** — no internet required; use inline CSS + JavaScript only
- **`make rerun` always adds WAVES=1** — makes it easy to debug failing tests
- **grid_config.json is a template** — the `{job_name}`, `{log_file}`, `{cmd}`, `{queue}` placeholders are replaced at runtime by `run_regression.py`
