# DV-Skills Session Prompts — 2026-03-22

## Prompt 1 — S5 Design Decisions (Group A/B/C/D/E)

> Register detail is fine as show by you for S1 update
>
> Group A
> - a1. It should be single VIP with parameterised classes — so if two TileLink interfaces have different DATA_WIDTH, they share one VIP class instantiated with different parameters, not two separate VIPs
> - a2. It should extract protocol, signal, timing information from the specification in skill 1 (S1 dv-spec-parse) — proprietary/non-standard interface signal lists, timing, handshake description
> - a3. Yes for all 3 questions (protocol-aware signal generation, clocking blocks, modports)
>
> Group B
> - B1. Only uvm_reg_block (not uvm_reg_map or uvm_reg_file) as the RAL top-level class
> - B2. Generate RAL adapter for the protocol which is used for register access (the register bus VIP)
> - B3. Both front door and backdoor access — configure_backdoor() with HDL paths
>
> Group C
> - C1 and C2. For reference model, ask user if it exists, what form (SV/C/Python/none), and where it is
>
> Group D
> - D1. Come up with a simple DUT stub yourself (don't ask user for DUT source)
> - D2. Yes there must be a DUT stub generated
>
> Group E
> - E1. Foundational sequences should have base sequence and reset sequence
> - Yes, sequences should have access to vif and cfg via uvm_declare_p_sequencer
> - Also there is going to be a top-level environment: DUT instantiating different agents, scoreboard, reference model, top-level config, virtual sequencer — generate all these

---

## Prompt 2 — S4 (dv-sim-setup) Decisions

> Which one is skill 4 and what do you know about it from my previous prompt?
>
> - A. No, skill shouldn't clone git repos
> - B. Add all options in Makefile (compile, sim, clean, regress, coverage, debug targets)
> - C. Use VCS and its switches, generate synopsys_sim.setup
> - Let's use skill creator to generate this skill adding above requirements
> - F. Add all placeholders whatever is needed for standard UVM testbench (compile.f, sim options, coverage options)
> - H. Define all environment variables whatever is needed (REPO_ROOT, DV_ROOT, VCS_HOME, etc.)
> - I. Use previous skill output if available, otherwise do your best

---

## Prompt 3 — Update S2/S3 and S5 Evals

> Go ahead and update S2 and S3, also did you evaluate S5, I didn't see your evaluation prompts for S5

---

## Prompt 4 — Status Check

> Are you doing something or done?

---

## Prompt 5 — S5 Missing Files

> Does S5 generate top-level DUT environment, base test and top_tb (where DUT is instantiated)? If not, upgrade Skill 5 to add all these also

---

## Prompt 6 — Write Session Prompts to File

> Can you write all my previous prompts from this session to a file in my documents folder

---

## Prompt 7 — Skill 6: dv-sequences

> Let's start with Skill 6 dv-sequences — let this be an interactive session to create a generic reusable agent-agnostic self-sufficient (scripts etc.) skill to generate all the tests as per the given testplan and existing testbench generated in previous skill or existing testbench already present and generate all the sequences needed in those testcases. Output is sequence code, testcase code with exist. Keep asking me questions if there is any doubt

---

## S6 Design Q&A

### Claude's Questions and User Answers

---

**Group A — Inputs**

**Q-A1.** When `dv_tb_data.json` is not available (pre-existing testbench), how should S6 discover TB structure?
Options: auto-scan dv/ / provide JSON / ask targeted questions / combination

> **Answer:** If existing testbench code is not available then stop and prompt user to provide it.

**Q-A2.** For testplan input — read Excel directly / accept JSON export / accept either?

> **Answer:** Accept either whichever gives best result, try testplan.xlsx first and if not found JSON.

**Q-A3.** Should S6 accept a natural-language testcase description as an alternative to a full testplan?

> **Answer:** Yes, it should generate individual testcases when prompted by user to do so with description of the testcase in the prompt. This can be interactive task if there are any confusion or doubt on the testcase flow, configuration, intent or any other aspect of testcase.

---

**Group B — Sequence Hierarchy**

**Q-B1.** Sequence hierarchy proposal:
`uvm_sequence → base_vseq → reset_vseq / feature_vseq → testcase_vseq / rand_vseq`
Use it or change?

> **Answer:** Sequence hierarchy shown is good, use it.

**Q-B2.** For random testcases: randomize virtual sequence using `std::randomize()` on seq_item, or something else?

> **Answer:** Yes generate randomized sequence for random test but randomness comes from sequence as well configuration, so you need to consider both for random test.

---

**Group C — Test Class Hierarchy**

**Q-C1.** Each testcase from testplan maps to exactly one UVM test class?

> **Answer:** Yes, each testcase to map to one UVM test class, but for each test we must specify plusargs, value plusargs, defines which gives it different flavour.

**Q-C2.** Test `run_phase`: start vseq and drop objection, or also control scoreboard/coverage?

> **Answer:** For configuration which could be DUT configuration or testbench configuration like scoreboard enable/disable or agent active/passive, we should have control in test via randomizing configuration with new constraint with base configuration defining default constraints.

**Q-C3.** Generate a `tests_pkg.sv`?

> **Answer:** Yes, generate tests_pkg.sv.

---

**Group D — Output File Layout**

**Q-D1.** Proposed layout: `dv/sequences/<protocol>/` for agent seqs,
`dv/sequences/<proj>/` for virtual sequences, `dv/tests/` for test classes?

> **Answer:** Not need to have separate directory for each feature, all sequences can be clubbed together on agent-wise like AXI/sequences/*sequence. Virtual sequences at DUT top calling multiple agent sequences can be saved in `dv/sequences/<proj>/*seq.sv`.

**Q-D2.** Combine sequences_pkg and tests_pkg into one, or keep separate?

> **Answer:** No don't combine sequence pkg and test pkg, have two different files.

---

**Group E — Checker Integration**

**Q-E1.** How to embed checker IDs?
Options: SVA in interface / separate bind file / scoreboard checker class / leave to S8?

> **Answer:** Just embed the checker ID wherever the checker is implemented. I want a display message displaying checker ID and message whenever checker passes — either in scoreboard or as assertion or as illegal coverage bin or in monitor or testcase.

**Q-E2.** Generate placeholder `check_<feature>()` tasks in scoreboard now, or leave entirely to S8?

> **Answer:** Leave scoreboard checker implementation for S8.

---

**Group F — Script / Tool**

**Q-F1.** Python helper script (like S5's `generate_tb_scaffold.py`) or inline Write tool only?

> **Answer:** Please have whatever makes it more generic, reusable to generate code. If script like S5 is needed generate it and keep it in common scripts directory.

**Q-F2.** Script parses testplan Excel directly (openpyxl), or skill converts to JSON first then passes to script?

> **Answer:** Do whatever makes it faster, reusable, generic for F2.

---

## Prompt 8 — Check in to Git

> Check in all in git with the prompt for this skill as well my answers to your question in the
