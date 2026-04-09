# PPT Generation Prompt — AI-Powered Subsystem Test Plan (ChipAgent)

Use this prompt with any agent that has access to **python-pptx** to regenerate
`AI_TestPlan_Skill.pptx` from scratch using the same design and content.

---

## HOW TO USE

1. Give this entire file to your agent (ChipAgent, Claude, GPT-4, etc.)
2. Make sure the agent has `python-pptx` available (`pip install python-pptx`)
3. The agent should write a `build_ppt.py` script and run it
4. Output file: `AI_TestPlan_Skill.pptx`

---

## PROMPT (copy everything below this line)

---

Create a professional PowerPoint presentation as a Python script using the
**python-pptx** library. Build everything from scratch — no template file.
Save the output as `AI_TestPlan_Skill.pptx`.

---

### DESIGN THEME — "Teal Innovation"

**Slide size:** 10.0 × 5.625 inches (widescreen 16:9)

**Colour palette:**

| Name       | Hex       | Usage                              |
|------------|-----------|------------------------------------|
| DARK       | `#0A3D47` | Title slide background, header bars |
| TEAL       | `#028090` | Primary accent, headers, pills     |
| SEAFOAM    | `#00A896` | Secondary accent                   |
| MINT       | `#02C39A` | Underline bars, highlights         |
| WHITE      | `#FFFFFF` | Text on dark backgrounds           |
| LIGHTBG    | `#F0F9FA` | Content slide backgrounds          |
| DARKTEXT   | `#1A2A3A` | Body text on light backgrounds     |
| MUTED      | `#5A7A85` | Subtitles, captions                |
| ACCENT     | `#FF6B35` | Orange accent (warnings, benchmark)|
| CODEBG     | `#0D1117` | Code block backgrounds             |
| CODEGRAY   | `#8B949E` | Code comments                      |
| CODEBLUE   | `#79C0FF` | Code keywords                      |
| CODELTBL   | `#A5D6FF` | Code values                        |
| CODEFG     | `#E6EDF3` | Code body text                     |
| RED        | `#C0392B` | Error / stop-on-error cards        |
| GREEN      | `#27AE60` | Success / venv cards               |
| ORANGE     | `#E67E22` | Warning / workspace cards          |
| PURPLE     | `#8E44AD` | Feedback / context cards           |

**Typography:**
- Body font: `Calibri`
- Code font: `Consolas`
- Slide titles: 20pt bold white (inside dark header bar)
- Section subtitles: 10pt italic muted (below header bar)
- Body text: 9.5–11pt
- Code text: 9.5pt Consolas

**Layout pattern for content slides:**
- Dark header bar (full width, 0.68 inches tall) at top, colour `#0A3D47`
- Thin mint underline bar (0.05 inch) below header bar
- Light background (`#F0F9FA`) for the rest of the slide
- Cards/boxes with white background, light border `#E0E0E0`, thin left accent bar

---

### SLIDES TO CREATE

---

#### SLIDE 1 — Title Slide

**Background:** `#0A3D47` (full dark)

**Layout:**
- Right side: three overlapping vertical rectangles in teal shades
  (`#028090`, `#016E7D`, `#015F6C`) creating a layered column effect
- Left side: thin vertical mint accent bar (`#02C39A`, 0.09" wide)

**Content:**
- Main title (large, bold, white, 34pt, Calibri):
  ```
  AI-Powered Subsystem
  Test Plan Generation
  ```
- Thin seafoam divider line below title
- Subtitle (13pt italic mint):
  ```
  Using ChipAgent  ·  From Design Specification to Structured Test Plan
  ```
- Four tag pills (teal fill, seafoam border) in a row:
  `ChipAgent` | `Test Automation` | `AI Skill` | `Design Spec`

---

#### SLIDE 2 — Planning the Skill

**Header:** "Planning the Skill"
**Subtitle:** "Init Prompt  ·  Key Questions  ·  Use Skill Creator"

**Left panel (card with teal left accent bar):**
- Title: "Sample Init Prompt"
- Code-style box (light background) containing this prompt text
  (use mixed bold/normal runs to highlight key phrases in teal):
  ```
  "I want to build a ChipAgent skill to automatically generate a
  subsystem test plan from a design specification document.

  What I know so far:
  • Input: Design spec (PDF / DOCX / structured text)
  • Output: Structured test plan in Excel / Word format
  • Skill must be modular, reusable, token-optimised
  • Benchmark against existing plans, MDA agent, prior versions

  Please ask me questions to fill any gaps, then use Skill Creator
  to create this skill."
  ```
  Highlight "ChipAgent skill", "subsystem test plan",
  "design specification document" in teal bold.
  Highlight "Skill Creator" in orange bold.

**Right panel — two stacked cards:**

Card 1 (seafoam accent): **"AI Will Ask About"**
- Document format (PDF, DOCX, plain text)
- Output format / Excel template columns
- Subsystem types & scope boundaries
- Benchmarking material availability

Card 2 (mint accent): **"Also Include in Your Init Prompt"**
- Existing test plan samples (reference)
- Expected sections: objectives, test cases, coverage
- Acceptance criteria / quality bar
- Known edge cases or special signal types
- Team conventions: naming, IDs, priority levels

---

#### SLIDE 3 — Skill Definition: Inputs · Outputs · Benchmarking

**Header:** "Skill Definition: Inputs · Outputs · Benchmarking"

Three equal-width columns with coloured headers and striped rows:

**Column 1 — Inputs to the Skill** (header colour: TEAL `#028090`)
- Design specification document (PDF / DOCX / structured text)
- Subsystem name & scope
- Output Excel/Word template
- Reference test plan (existing)
- Protocol / standard reference docs
- Parsing config: section headers, naming conventions

**Column 2 — Output & Format** (header colour: SEAFOAM `#00A896`)
- Structured test plan document
- Excel: Test ID, description, expected result, priority, tag
- Word: organised by feature / subsystem section
- Intermediate JSON/YAML (for downstream skills)
- Interface & protocol summary (reusable artefact)
- Parsing log / section map

**Column 3 — Benchmarking** (header colour: ACCENT `#FF6B35`)
- vs. Existing test plan (coverage %, section match)
- vs. MDA Agent output (quality & completeness)
- vs. Previous skill version (regression & improvement)
- Metrics: # test cases, coverage depth, missed requirements
- False-positive test cases flagged
- Manual review checklist

Each row alternates between white and very light teal (`#F5FEFF`).
Each row has a thin left accent bar matching the column colour.

---

#### SLIDE 4 — Structure of the Skill

**Header:** "Structure of the Skill"
**Subtitle:** "Modular · Reusable · Generic · Token-Optimised"

**Top row — 4 principle pills** (full-width, equal spacing):
- "Modular" (TEAL) — "Each step is an independent sub-skill"
- "Reusable" (SEAFOAM) — "Scripts shared across multiple skills"
- "Generic" (MINT) — "Works across different subsystem types"
- "Token-Optimised" (`#027080`) — "Compact context, no redundant steps"

**Left panel — Sub-Skills & Intermediate Outputs table:**
Card with teal left accent. Five rows:

| Sub-skill name (code pill) | Description | Downstream usage |
|---|---|---|
| `doc-parser` | Parses design spec → section map JSON | Reused by interface-extractor & VIP dev skill |
| `req-extractor` | Extracts requirements & features from sections | Feeds test-case-generator |
| `interface-extractor` | Pulls interface & protocol info | Used by Interface VIP Dev Skill |
| `testcase-generator` | Generates test cases per requirement | Core output of this skill |
| `xls-writer` | Writes test plan to Excel template | xls-reader script reused by other skills |

Each sub-skill name in a teal pill (Consolas font).
Arrow `→` between name and description.
Downstream usage in italic teal.

**Right panel — "What Else Belongs Here"** (seafoam accent card):
- Error-recovery scripts (retry logic, partial-result save)
- Context-reset utilities (/clear + /compact mid-task)
- Validation / QA scripts (coverage checker, diff vs reference)
- Shared Excel template (standard test-plan format)
- Glossary / abbreviation resolver (domain terms for LLM context)

---

#### SLIDE 5 — Good Practices

**Header:** "Good Practices"
**Subtitle:** "Quality · Monitoring · Environment · Infrastructure"

Six cards in a 3×2 grid, each with a coloured top accent bar:

| Card title | Top bar colour | Body |
|---|---|---|
| Stop on Error — Don't Improvise | RED `#C0392B` | "Instruct agent to halt & report immediately on any error. Do NOT find workarounds — they silently compromise output quality." |
| Monitor Processing Closely | TEAL `#028090` | "Watch for: errors, context approaching 100%, slow/looping steps. Embed repetitive non-core steps (e.g. doc parsing) as scripts to preserve token budget." |
| Use Local Virtual Environment | GREEN `#27AE60` | "Always use a Python venv for all dependencies. Never install globally — ensures reproducibility & isolation." |
| Keep Workspace Clean | ORANGE `#E67E22` | "Don't clutter workspace with intermediate docs not needed for the task. Remove temp files after each step to reduce noise & context usage." |
| Invest in Common Infrastructure | SEAFOAM `#00A896` | "Shared scripts (xls-reader, doc-parser), common templates & standard spec formats reduce AI pressure, cut tokens, improve consistency." |
| Use New / Clear / Compact Between Tasks | PURPLE `#8E44AD` | "Reset context between major task phases (/new, /clear, /compact). Use as transition points to keep context clean, fresh, and focused." |

Card backgrounds should be very light tinted versions of their accent colour.

---

#### SLIDE 6 — ChipAgent Configuration

**Header:** "ChipAgent Configuration"
**Subtitle:** "Skills · Automation · Rules · Session Triggers"

Three equal-width columns, each with a coloured header and a dark
code block (`#0D1117` background) below it:

**Column 1 — Enable Skills** (TEAL header)
```yaml
# Register in skills registry
skills:
  - name: subsystem-testplan
    path: ./skills/testplan
    version: 1.0
enable-skills: true
auto-load: true
```

**Column 2 — Automatic Commands** (SEAFOAM header)
```yaml
# Auto-run on session start
on_start:
  - /load-skill testplan
  - /set-context subsystem
# On trigger keyword
on_trigger: "generate testplan"
  - /run testplan-skill
```

**Column 3 — Rules (Always Applied)** (ACCENT/orange header)
```yaml
# Applied every session / trigger
rules:
  - stop_on_error: true
  - use_venv: ./venv
  - clear_workspace_after_task
  - context_limit: compact
  - output_format: excel+json
```

Render code lines with syntax colouring:
- Comments (`#`): `#8B949E`
- Keys/keywords: `#79C0FF`
- Values: `#A5D6FF`
- Plain text: `#E6EDF3`

**Footer note** (muted italic):
"💡 Rules defined in ChipAgent config persist across all sessions — no need to repeat instructions each time."

---

#### SLIDE 7 — Iteration to Improve the Skill

**Header:** "Iteration to Improve the Skill"
**Subtitle:** "Benchmark → Review → Feedback → Repeat"

**Top — 5-step cycle with circles and boxes:**

| Step | Label | Colour |
|---|---|---|
| 1 | Run Skill & Benchmark | TEAL |
| 2 | Compare vs Existing Plan | SEAFOAM |
| 3 | Identify Gaps & Issues | ACCENT (orange) |
| 4 | Give Feedback to Skill | PURPLE |
| 5 | Update Skill & Re-run | GREEN |

Each step: numbered circle above → labelled box below.
Thin grey arrows between boxes.

**Banner below steps** (dark `#0A3D47` background, mint italic text):
```
Repeat this cycle multiple times — each iteration makes the skill measurably better
```

**Two detail cards below the banner:**

Card 1 (teal accent) — **"What to Review in Each Iteration"**
- Coverage %: requirements with test cases
- Missing scenarios flagged by reviewer
- Incorrect or vague test descriptions
- Section structure match vs existing plan
- Delta improvement vs prior skill version

Card 2 (seafoam accent) — **"How to Give Effective Feedback"**
- Be specific: "Interrupt handling test missing"
- Annotate generated plan before feeding back
- Compare diff vs MDA output for systematic gaps
- Update skill prompt after each review cycle
- Track skill version history with benchmark scores

---

#### SLIDE 8 — Known Issues & Mitigations

**Header:** "Known Issues & Mitigations"
**Subtitle:** "Real challenges observed while running ChipAgent skills in production"

Two large issue cards side by side. Each card has:
- Coloured header bar with icon + title
- "Symptom" sub-section
- "Root Cause" sub-section
- "Mitigation Steps" bullet list

**Issue 1 — Context Stuck at Fixed %** (RED, icon: 🔒)
- Symptom: ChipAgent context meter freezes at a fixed % mid-task; agent loops without producing output
- Root cause: Large intermediate docs or repeated tool calls saturate the context window
- Mitigations:
  - Monitor context % continuously — set alert at 80%
  - Use /compact or /clear at natural task boundaries
  - Break large documents into chunks
  - Store intermediate outputs to disk, not in context
  - Embed heavy parsing steps as scripts

**Issue 2 — Agent Avoids Reporting Errors** (ORANGE, icon: ⚠️)
- Symptom: On errors (file not found, parse failure), agent silently tries alternatives, producing low-quality output
- Root cause: Default agent behaviour optimises for task completion, not quality
- Mitigations:
  - Add explicit rule: "stop_on_error: true" in ChipAgent config
  - State in skill prompt: "If you encounter any error, stop and report it clearly"
  - Review agent logs after each run for suppressed errors
  - Add a post-run validation script to check output integrity

---

#### SLIDE 9 — ChipAgent Session Metrics

**Header:** "ChipAgent Session Metrics"
**Subtitle:** "Input Analysis · Token Usage · Context · Timeline"

**Top section — Input Document Analysis table:**
Full-width table with columns:
`Document Name` | `Size (MB)` | `Pages` | `Lines` | `Total Docs` | `Total Queries` | `Registers`

Show 3 example rows with placeholder data:
- subsystem_spec_v2.pdf | 4.2 | 187 | 8,340 | 1 | 24 | 112
- interface_protocol.docx | 1.8 | 64 | 2,890 | 1 | 11 | 38
- design_overview.pdf | 2.5 | 98 | 4,120 | 1 | 16 | 74

**Bottom section — 4 metric cards in a row:**

Card 1 (TEAL) — **Token Usage Analysis**
- Input tokens: 48,320
- Output tokens: 12,840
- Total: 61,160
- Est. cost: $0.18
- Show a mini bar: Input █████████░ / Output ██░

Card 2 (SEAFOAM) — **Context Management**
- Peak context usage: 87%
- /compact used: 3×
- /clear used: 1×
- Context resets: 4 total
- ⚠ 1 near-saturation event

Card 3 (MINT) — **Session Timeline**
- Session start: 09:14
- Spec ingestion: 09:14–09:22 (8 min)
- Test generation: 09:22–09:51 (29 min)
- Excel formatting: 09:51–09:56 (5 min)
- Total: 42 min

Card 4 (ACCENT/orange) — **Quality Snapshot**
- Test cases generated: 247
- Requirements covered: 94%
- Benchmark score vs existing: 0.81
- Version: v1.2

---

### TECHNICAL REQUIREMENTS FOR THE SCRIPT

1. Use only `python-pptx` — no other layout libraries
2. All shapes drawn using `add_shape` / `add_textbox` — do NOT use
   placeholder-based layouts
3. Use `slide_layouts[6]` (blank layout) for all slides
4. All positions and sizes in `Inches()`
5. All font sizes in `Pt()`
6. No emoji in text boxes (python-pptx renders them as boxes on some systems)
   — use plain-text alternatives where needed
7. The script must be self-contained: run `python build_ppt.py` → produces
   `AI_TestPlan_Skill.pptx` in the same directory
8. Add a `if __name__ == "__main__":` block at the bottom that calls each
   slide function and saves the file

---

*Prompt file: `project-ppt/PPT_GENERATION_PROMPT.md`*
*Generated presentation: `project-ppt/AI_TestPlan_Skill.pptx`*
*Script: `project-ppt/build_ppt.py`*
*Created: 2026-04-09*
