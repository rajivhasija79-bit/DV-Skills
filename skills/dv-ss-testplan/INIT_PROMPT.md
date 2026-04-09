# dv-ss-testplan — PPT Briefing Prompt

This is the original prompt used to generate the PowerPoint presentation
showcasing the `dv-ss-testplan` AI skill work to management.

---

## PPT PROMPT (verbatim)

This is an AI project using **ChipAgent** to generate the **Subsystem Testplan**
from a Design Specification.

Structure the slide deck to cover the following sections:

---

### Slide Section 1 — Planning the Skill

Write an init prompt describing all we know on how to generate the testplan,
and ask the AI to help plan it by asking questions if any info is missing.
Then ask it to use **Skill Creator** to create the skill.

Clearly mention the following in the init prompt:

- **Inputs to the skill**
- **Output and its format**
- **Benchmark** — against existing human testplan, against MDA (another agent),
  against a previous version of the skill
- Suggest what other info must go in the initial prompt to create the skill

---

### Slide Section 2 — Structure of the Skill

The skill must be: **modular, reusable, generic, optimised for token and context usage**.

Key things to cover:

- Dividing the skill into **sub-skills, scripts, and intermediate outputs** which
  can be reused by other downstream skills, e.g.:
  - Extracting interfaces and protocol info → reused by the Interface VIP
    Development skill
  - Common scripts (e.g. XLS reader) reused by other skills
- Suggest what else can go in the Skill Structure section

---

### Slide Section 3 — Good Practices

- Ask the agent to **stop if it encounters any error** rather than looking for
  an alternative which might compromise quality
- **Closely monitor processing** for errors, context getting close to 100%, etc.
  — this can degrade output quality, or help identify steps which can be
  embedded as scripts to avoid repetitive steps not relevant to the main task
  (e.g. parsing the document during testplan generation)
- Use a **local virtual environment** for Python packages
- **Do not clutter the agent workspace** with extra documents not needed for
  the task
- **Need for common infrastructure** — shared scripts / templates, common
  document/specification formats to ease pressure on AI and reduce token usage
- **New, clear, compact context** — use it in between tasks

---

### Slide Section 4 — ChipAgent Configuration

- `enable-skills`
- Automatic / trusted commands
- **Rules** — to be applied every time a session is invoked, or when a
  specific trigger / command is called
- Any other relevant ChipAgent config settings

---

### Slide Section 5 — Iteration to Improve the Skill

- Review benchmarking results
- Review generated testplan vs existing human testplan
- Give structured feedback to improve the skill
- This loop must be **repeated multiple times** until quality is acceptable

---

### Slide Section 6 — ChipAgent Session Metrics

- **Input Document Analysis** — table with columns:
  Size (MB) | Pages | Lines | Total Number of Documents | Total Queries | Number of Registers
- **Token Usage Analysis**
- **Context Management**
- **Session Timeline**

---

*File: `skills/dv-ss-testplan/INIT_PROMPT.md`*
*Repo: DV-Skills-1*
*Created: 2026-04-09*
