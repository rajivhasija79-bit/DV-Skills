# DV Plan Skill — Architecture & Development Plan

## Overview

A set of Claude skills to automatically generate two key DV documents from design specifications:
1. **Verification Strategy Document** (`.docx`)
2. **DV Testplan** (`.xlsx`)

Supports three DV project types: **IP**, **SS (Sub-System)**, **SoC** — each with fundamentally different verification philosophies, TB structures, and testplan content.

---

## Problem Statement

### Input Non-Uniformity
Every axis of input varies across projects:

| Axis | Variations |
|---|---|
| Project type | IP / SS / SoC |
| Input format | PDF, DOCX, XLSX, or mixed |
| Input file count | 1 file to N files |
| Document naming | design_spec, MAS, HLS, HAS, datasheet, user manual, PRD |
| PRD/FID presence | Separate doc / embedded in spec / absent entirely |
| Spec completeness | Full register maps ↔ high-level functional only |
| Output format | XLSX (testplan) + DOCX (verification strategy) |

### DV-Type Verification Philosophy Differences

**IP DV:**
- Exhaustive block-level feature verification
- Register access testing (R/W/RO/WO/W1C, reset values, field interactions)
- Interface protocol compliance (AXI/APB/AHB/custom)
- Clock/reset/power domain coverage
- Corner cases, error injection, boundary conditions
- PRD/FID may or may not be present — features inferred from spec directly
- TB: Single IP TB with one or few interface variants (e.g. AHB vs AXI builds)
- Deliverable to SS DV: functional model, coverage results

**SS DV:**
- PRD → FID → Testcase mapping is the backbone
- Multi-block integration scenarios
- Datapath, control flow, interrupt routing
- Multiple SS flavours (e.g. 3-block SS vs 4-block SS configurations)
- TB: Multiple SS configurations as separate compilation builds
- Receivables: IP RTL + IP DV functional models
- Deliverable to SoC DV: SS functional model, sign-off coverage

**SoC DV:**
- System use-cases, boot sequences, end-to-end flows
- Multi-subsystem interactions
- Power management, security, memory map validation
- Boot sequences, multi-power-domain coverage
- TB: Full SoC or partial SoC, emulation model handoff
- Receivables: All SS RTL + SS DV environments
- Deliverable: Final sign-off, emulation handoff

---

## Output Documents

### 1. Verification Strategy Document (DOCX)

Sections (not all present in every existing doc — generated with best-effort):

| # | Section | Content |
|---|---|---|
| 1 | DUT Overview | Brief overview of DUT — name, type, key interfaces |
| 2 | DV Planning | Collaterals (receivables + deliverables), Strategy (methodology, TB flavours, reuse), DV Phases (milestones, flowchart, schedule) |
| 3 | Testbench Architecture | TB block diagram (ASCII), component interconnect |
| 4 | Testbench Components | VIPs (in-house + third-party), reference model, scoreboard, monitors, coverage collector |
| 5 | Features and How They Are Tested | Feature-level test approach, test types, key scenarios |
| 6 | DV KPIs | Goals, sign-off criteria, coverage targets |
| 7 | Assumptions | Known assumptions, open items |
| 8 | Feature Verification Table | FID \| Feature Name \| Description \| Verification Criteria |
| 9 | DV Infra | Directory structure, scripts, how to run (wave/coverage/debug switches), logfiles, waveform, coverage database |

### 2. DV Testplan (XLSX)

11-column schema:

| # | Column | Description |
|---|---|---|
| 1 | PRD Number | PRD reference number if available |
| 2 | Feature | Main DUT feature name + FID if from PRD-FID mapping |
| 3 | Sub Feature | Sub-division of feature if applicable |
| 4 | Description | Feature description |
| 5 | Test Type | `Testcase` / `Coverpoint` / `Check` or combination e.g. `Random Testcase + Coverpoint + Checker` |
| 6 | Test Sequence | 4 sub-aspects: (a) Config sequence, (b) Stimulus flow, (c) Checks/monitors, (d) Pass and end criteria |
| 7 | Testcase Name | Name of directed or random testcase (if Test Type includes testcase) |
| 8 | Coverpoint | Coverpoint name + SystemVerilog code (if Test Type includes coverpoint) |
| 9 | Checker | Checker name / Checker ID (if Test Type includes checker) |
| 10 | Checker Implementation | Where checker lives: `scoreboard` / `monitor` / `interface` / `testcase` |
| 11 | Simulation Switches | Plusargs, valueplusargs, or other switches to run this test |

---

## Skill Architecture

### 3-Layer Design

```
┌─────────────────────────────────────────────────────────────────────┐
│   LAYER 1 — USER-FACING ENTRY SKILLS (3)                            │
│                                                                     │
│   /dv-ip              /dv-ss              /dv-soc                   │
│                                                                     │
│   Flags on each:                                                    │
│   --testplan-only  |  --verstrat-only  |  (default: both)           │
│   --benchmark      |  --existing-testplan <file>                    │
│                    |  --existing-verstrat <file>                    │
└────────┬───────────────────┬──────────────────┬─────────────────────┘
         │                   │                  │
         └───────────────────┼──────────────────┘
                             │
         ┌───────────────────▼─────────────────────────────────────────┐
         │   LAYER 2 — SHARED PROCESSING (runs once, output cached)    │
         │                                                             │
         │   spec-ingester       →   .dv_ir/spec_ir.json              │
         │   prd-fid-extractor   →   .dv_ir/fid_prd_map.json          │
         │                                                             │
         │   Skips re-processing if IR files exist and spec unchanged  │
         └───────────────────┬─────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
   ┌────────────────────────┐  ┌─────────────────────────────┐
   │  LAYER 3A              │  │  LAYER 3B                   │
   │  testplan-generator    │  │  verstrat-generator         │
   │  (mode-aware)          │  │  (mode-aware)               │
   │                        │  │                             │
   │  IP:                   │  │  IP:                        │
   │  register + interface  │  │  block TB, AHB/AXI builds   │
   │  + feature tests       │  │  IP reuse as VIP for SS     │
   │                        │  │                             │
   │  SS:                   │  │  SS:                        │
   │  FID-mapped +          │  │  multi-block TB, SS         │
   │  integration tests     │  │  flavours, IP model reuse   │
   │                        │  │                             │
   │  SoC:                  │  │  SoC:                       │
   │  use-case + boot +     │  │  system TB, boot/power/sec  │
   │  e2e + power tests     │  │  phases, SS model reuse     │
   └──────────┬─────────────┘  └────────────────┬────────────┘
              │                                  │
              ▼                                  ▼
       xlsx-formatter                     docx-formatter
              │                                  │
              ▼                                  ▼
       testplan.xlsx                   verstrat.docx
              │
              ▼  (if --benchmark flag)
         benchmarker
              │
              ▼
       benchmark_report.md
```

---

## Intermediate Representation (IR) Files

All sub-skills communicate via compact JSON files written to `.dv_ir/` in the workspace — raw spec text is never passed between skills.

### `spec_ir.json`
```json
{
  "meta": {
    "project_type": "IP|SS|SoC",
    "dut_name": "uart_ctrl",
    "spec_version": "1.2",
    "source_files": ["design_spec.pdf", "regmap.xlsx"]
  },
  "dut_overview": "...",
  "features": [
    { "id": "F001", "name": "UART TX", "description": "...", "source_section": "3.2" }
  ],
  "registers": [
    { "name": "CTRL_REG", "offset": "0x00", "fields": [
      { "name": "TX_EN", "bits": "0", "access": "RW", "reset": "0x0", "desc": "..." }
    ]}
  ],
  "interfaces":    [ { "type": "APB", "role": "slave", "data_width": 32 } ],
  "clocks":        [ { "name": "clk_sys", "freq": "100MHz", "domain": "sys" } ],
  "resets":        [ { "name": "rst_n", "type": "async", "active": "low" } ],
  "interrupts":    [ { "name": "rx_full", "type": "level", "bit": 3 } ],
  "memory_map":    [],
  "power_domains": [ { "name": "VDD_CORE", "rails": ["vdd1p0"] } ],
  "gpio":          [],
  "protocols":     [ { "name": "UART", "standard": "16550" } ],
  "prd_items":     [],
  "assumptions":   [],
  "open_items":    []
}
```

### `fid_prd_map.json`
```json
{
  "fid_list": [
    {
      "fid": "F001",
      "prd_ref": "PRD-12",
      "feature_name": "UART TX",
      "description": "...",
      "source": "extracted|inferred",
      "sub_features": [
        { "sfid": "F001.1", "name": "TX FIFO fill", "description": "..." }
      ]
    }
  ],
  "prd_fid_map":       [ { "prd": "PRD-12", "fid": "F001", "title": "UART Transmit" } ],
  "unmapped_features": [],
  "inferred_fids":     ["F007", "F008"],
  "prd_source":        "separate_doc|embedded_in_spec|not_found"
}
```

### `testplan_ir.json`
Array of row objects matching the 11-column testplan schema — used by xlsx-formatter and optionally by verstrat-generator for the "Features & How Tested" section.

---

## Sub-Skill Details

### spec-ingester

**Input:** List of spec file paths (PDF / DOCX / XLSX, any mix)

**Per-format strategy:**

| Format | Library | Approach |
|---|---|---|
| PDF | `pdfplumber` / `pymupdf` | Two-pass: TOC scan → DV-relevant section extraction |
| DOCX | `python-docx` | Heading-based section extraction |
| XLSX | `openpyxl` / `pandas` | Sheet-by-sheet: detect register map / GPIO / memory map by column headers |

**Two-pass approach (token efficiency):**
1. Pass 1: Extract document structure only (headings, section names, table headers)
2. Claude identifies which sections are DV-relevant from structure
3. Pass 2: Extract content from identified sections only

**Output:** `spec_ir.json`

---

### prd-fid-extractor

**Three scenarios:**

| Scenario | Detection | Action |
|---|---|---|
| PRD in separate file | Filename contains "PRD", "FID", "requirements" | Parse directly |
| PRD embedded in spec | Section titled "requirements", "product requirements", "feature list" | Extract from spec_ir |
| PRD absent | No PRD content found | Infer FID list from `features[]` using DV taxonomy |

**Output:** `fid_prd_map.json`

---

### testplan-generator (mode-aware)

**Generation approach:** Batched by feature group (10-15 FIDs per LLM call) with carry-forward context for checker ID and testcase name uniqueness.

**Test type decision logic:**

| Feature type | Test Type assigned |
|---|---|
| Register access | Directed Testcase + Checker |
| Protocol compliance | Random Testcase + Coverpoint + Checker |
| Error / exception handling | Directed Testcase + Checker |
| Normal operation / datapath | Random Testcase + Coverpoint |
| Passive monitoring / all-test | Checker only |
| Configuration modes | Directed Testcase + Coverpoint |

**Mode differences:**

| Aspect | IP | SS | SoC |
|---|---|---|---|
| Primary test driver | Features + register map | PRD → FID mapping | System use-cases |
| Coverpoints | Register fields, interface states, error flags | FID coverage, integration paths, control flow | Use-case coverage, power states, boot phases |
| Checkers | Register reset values, interface protocol, data integrity | Datapath correctness, IRQ routing, config propagation | Memory map, system integrity, security policy |
| Testcase naming | `<ip>_<feature>_<type>` | `<ss>_fid<N>_<scenario>` | `<soc>_uc<N>_<flow>` |

**Output:** `testplan_ir.json`

---

### verstrat-generator (mode-aware)

Generated section by section to manage token load.

**Section generation sources:**

| Section | Source | IP specifics | SS specifics | SoC specifics |
|---|---|---|---|---|
| DUT Overview | spec_ir.meta + dut_overview | Block-level desc | Sub-system desc | Full chip desc |
| DV Planning — Collaterals | spec_ir.interfaces + project_type | Recv: RTL+spec; Del: model to SS | Recv: IP models+SS spec; Del: SS model to SoC | Recv: all SS envs; Del: final sign-off |
| DV Planning — Strategy | interfaces, protocols, project_type | AHB/AXI TB variants | SS config flavours | Full/partial SoC |
| DV Planning — Phases | project_type + milestone hints | IP milestones | SS + IP dependency milestones | SoC + SS dependency milestones |
| TB Architecture | interfaces, clocks, resets | IP TB ASCII diagram | SS TB ASCII diagram | SoC TB ASCII diagram |
| TB Components | interfaces, protocols | Protocol VIPs, refmodel | IP functional models as VIPs | SS models as VIPs |
| Features & How Tested | fid_prd_map + testplan_ir (optional) | Feature-level test approach | FID-mapped test approach | Use-case test approach |
| DV KPIs | project_type | Block coverage targets | Integration coverage targets | System coverage targets |
| Assumptions | spec_ir.open_items | — | — | — |
| Feature Verification Table | fid_prd_map | All features + verification criteria | FID-mapped features | Use-case mapped features |
| DV Infra | project_type | IP TB run guide | SS TB run guide | SoC TB run guide |

**Output:** `vstrat_ir.json` (section-by-section content)

---

### benchmarker

**Scope:** Features and how they are tested only (testcases, test flow, coverage, checks). Other VerStrat sections not benchmarked in this phase.

**Algorithm:**
1. Extract feature list from existing docs (any format)
2. Extract test coverage from existing docs
3. Compare with `testplan_ir.json`
4. Compute metrics:
   - `feature_recall`    = |generated ∩ existing| / |existing|
   - `feature_precision` = |generated ∩ existing| / |generated|
   - `missing_features`  = existing − generated
   - `new_features`      = generated − existing (newly identified gaps)
   - `tc_coverage_delta` = test scenarios in generated vs existing

**Output:** `benchmark_report.md` with scores and gap list

---

## Token Efficiency Strategy

| Problem | Strategy |
|---|---|
| Large PDF spec (100+ pages) | Two-pass: structure scan first, then targeted section extraction |
| Multiple input files | Merge into single `spec_ir.json` before any generation |
| Repeated context across sub-skills | Pass only IR JSON (compact), never raw spec text |
| Large register maps in XLSX | Extract: name, offset, fields, access, reset only — drop verbose descriptions under token pressure |
| Long testplan generation | Batch by feature group (10-15 FIDs per call), carry-forward checker/TC name registry |
| Both outputs requested | Run shared processing once, feed IR to both generators |
| Re-running after spec update | Cache invalidation: compare spec file mtime vs IR file mtime, re-ingest only if spec changed |

---

## Skill Inventory

| Layer | Skill Name | Type | Reused by |
|---|---|---|---|
| Entry | `dv-ip` | User-facing | IP projects |
| Entry | `dv-ss` | User-facing | SS projects |
| Entry | `dv-soc` | User-facing | SoC projects |
| Processing | `spec-ingester` | Shared util | All 3 entry skills |
| Processing | `prd-fid-extractor` | Shared util | All 3 entry skills |
| Generation | `testplan-generator` | Shared, mode-aware | All 3 entry skills |
| Generation | `verstrat-generator` | Shared, mode-aware | All 3 entry skills |
| Formatting | `xlsx-formatter` | Shared util | All 3 entry skills |
| Formatting | `docx-formatter` | Shared util | All 3 entry skills |
| Optional | `benchmarker` | Standalone / pipeline | Any entry skill with --benchmark |
| **Total** | | | **10 skills** |

---

## Usage Examples

```bash
# IP — generate both testplan and verstrat
/dv-ip

# SS — testplan only (user already has VerStrat)
/dv-ss --testplan-only

# SoC — verstrat only, pass existing testplan to enrich "Features & How Tested" section
/dv-soc --verstrat-only --existing-testplan soc_testplan.xlsx

# IP — both outputs, benchmark generated testplan against existing
/dv-ip --benchmark --existing-testplan uart_tp.xlsx --existing-verstrat uart_vs.docx

# SS — full generation with PRD from separate file
/dv-ss --prd prd_fid_mapping.xlsx
```

---

## Benchmarking Plan (5 Existing Projects)

Use the 5 existing project pairs (spec + testplan + verstrat) in phases:

### Phase 1 — Extraction Accuracy
- Run `spec-ingester` on each spec
- Compare extracted features/FIDs against known testplan
- Metric: % features captured, % registers captured

### Phase 2 — Generation Coverage
- Run full pipeline
- Compare generated testplan rows vs existing testplan rows
- Metric: feature recall, feature precision, TC coverage overlap

### Phase 3 — Format Fidelity
- Run `xlsx-formatter` + `docx-formatter`
- Compare column schema match with org's existing format

### Scoring
```
skill_score = (feature_recall × 0.4) + (tc_coverage × 0.4) + (format_match × 0.2)
```

---

## Development Phases

```
Phase 1 — Validate extraction schema           (run on all 5 projects, iterate)
  └─ Run validation prompt on internal agent
  └─ Adjust spec_ir.json schema from feedback

Phase 2 — Build spec-ingester + prd-fid-extractor
  └─ PDF + DOCX + XLSX readers
  └─ Claude prompt for DV-relevant section identification
  └─ Test on all 5 project specs

Phase 3 — Build testplan-generator (IP mode first)
  └─ Most structured, register maps, well-defined
  └─ Validate 11-column output against IP testplan
  └─ Tune with benchmarker

Phase 4 — Build verstrat-generator (IP mode first)
  └─ Section by section, DUT Overview + Feature Table first
  └─ Full doc generation and review

Phase 5 — Add SS mode to both generators
  └─ FID-mapped testplan generation
  └─ SS-specific verstrat sections

Phase 6 — Add SoC mode to both generators
  └─ Use-case + boot + power testplan generation
  └─ SoC-specific verstrat sections

Phase 7 — Output formatters
  └─ xlsx-formatter: 11 columns, freeze row, auto-filter, priority color coding
  └─ docx-formatter: standard headings, numbered sections, ASCII diagrams as code blocks

Phase 8 — Benchmarker + full pipeline
  └─ End-to-end on all 5 projects
  └─ Iterate based on benchmark scores
```

---

## Validation Prompt (Phase 1)

Run this on your internal agent against any spec to validate extraction schema without sharing proprietary content:

```
You are a DV spec extraction agent. Given the attached design specification
document(s), extract the following and return as structured JSON ONLY
(no prose, no explanation):

{
  "dut_name": "<name of IP/SS/SoC>",
  "project_type": "<IP|SS|SoC>",
  "features": [
    { "id": "<F00N or inferred>", "name": "<feature name>",
      "description": "<1-2 sentence description>",
      "has_prd_ref": <true|false> }
  ],
  "registers": [
    { "name": "<reg name>", "offset": "<hex>",
      "field_count": <N>, "has_rw_fields": <true|false> }
  ],
  "interfaces": [
    { "type": "<AXI|APB|AHB|custom|...>", "role": "<master|slave>" }
  ],
  "clocks":   [ { "name": "<clk name>", "freq": "<if mentioned>" } ],
  "resets":   [ { "name": "<rst name>", "type": "<sync|async>" } ],
  "interrupts": [ { "name": "<irq name>" } ],
  "prd_items":  [ { "prd_ref": "<PRD-N>", "title": "<title>" } ],
  "prd_source": "<separate_doc|embedded_in_spec|not_found>",
  "extraction_confidence": "<high|medium|low>",
  "gaps": ["<anything important that could not be extracted and why>"]
}

Attached files: [your spec files here]
```

Share the JSON output (no spec content) and we can validate the schema is capturing the right things.

---

*Last updated: 2026-04-04*
*Status: Planning complete — ready for Phase 1*
