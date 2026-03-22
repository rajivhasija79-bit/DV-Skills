---
name: dv-spec-parse
description: |
  Design Verification skill that parses a hardware design specification document
  (PDF, DOCX, TXT, or Markdown) and extracts all structured information needed to
  kick off a DV project — features, interfaces, signals, parameters, clocks, resets,
  operating modes, and compliance standards.

  Use this skill whenever a user wants to:
  - Start a DV project from a spec or design document
  - Extract features, interfaces, or signals from a hardware spec
  - Generate a structured DV spec summary from a PDF, Word doc, or text file
  - Prepare inputs for testplan generation (S2/dv-testplan)
  - Parse or analyse a design spec for verification planning purposes

  Trigger on phrases like: "parse my spec", "read the design doc", "extract features from spec",
  "start DV from this spec", "analyse this design document", "what are the interfaces in this spec",
  "generate spec summary", "dv-spec-parse", "/dv-spec-parse"
---

# DV Spec Parse — S1

You are acting as a senior DV engineer parsing a hardware design specification to
extract all information needed to plan a verification effort. Your output feeds
directly into downstream DV skills (testplan, verification plan, TB scaffold, etc.),
so completeness and structure are critical.

---

## Step 1 — Gather Inputs

Before doing anything, confirm you have all required inputs. Check the user's message
and conversation history first. Only ask for what is genuinely missing.

### Required inputs

| Input | Description | Action if missing |
|---|---|---|
| `SPEC_FILE` | Path to design spec (PDF / DOCX / TXT / MD) | Ask user: *"Please provide the path to your design spec file."* |
| `PROJECT_NAME` | Name of the block or project being verified | Ask user: *"What is the name of the block/project? (e.g. apb_uart, axi_dma)"* |
| `OUTPUT_DIR` | Directory to save output files | Default to the spec file's directory. Confirm: *"I'll save outputs to `<dir>` — is that OK, or would you prefer a different location?"* |

Ask for all missing inputs in a **single message** — do not ask one at a time.
Once all inputs are confirmed, proceed immediately without waiting for further instruction.

---

## Step 2 — Read the Spec

Read the spec file using the available file reading tools. If it is a PDF, read all pages.
If it is very large (>100 pages), focus on:
- Executive summary / introduction
- Block diagram sections
- Interface descriptions
- Register maps or signal tables
- Functional description sections
- Appendices with signal/parameter lists

---

## Step 3 — Extract Information

Extract the following sections. For each section:
- If information is clearly present → extract it accurately
- If information is partially present or ambiguous → extract what you can and mark with `⚠️ NEEDS_REVIEW`
- If information is completely absent → use placeholder `TBD` and mark with `⚠️ NEEDS_REVIEW`

### Sections to extract

1. **Block Overview** — Purpose of the block, key use cases, position in system
2. **Feature List** — All top-level design features (numbered)
3. **Sub-feature List** — Sub-features under each parent feature
4. **Interface List** — All interfaces with: name, type (input/output/bidir), protocol, width
5. **Signal List** — Key signals per interface: name, direction, width, description
6. **Parameters** — Configurable parameters: name, default value, description
7. **Clock Domains** — Each clock: name, source, typical frequency, affected logic
8. **Reset Strategy** — Each reset: name, type (sync/async), polarity, affected domains
9. **Operating Modes** — All modes the DUT can be configured into
10. **Compliance Standards** — Protocols/standards the block must comply with (AXI4, APB, USB, etc.)
11. **Known Constraints** — Design constraints, timing requirements, or limitations explicitly stated
12. **Register Map** — For every register in the DUT, extract:
    - Register name (as it appears in spec)
    - Byte offset (hex)
    - Reset value (hex)
    - Register description (1–2 sentences)
    - Whether it is a shadowed register (yes/no)
    - Whether it is an interrupt status/mask/enable register (yes/no)
    - For each field within the register:
      - Field name
      - Bit range (e.g. `[7:4]`)
      - Width (bits)
      - Access type: `RW` / `RO` / `WO` / `W1C` / `W1S` / `RC` / `RS` / `RSVD`
      - Reset value (per-field, hex or binary)
      - Description
    If no registers are present (e.g. no memory-mapped registers in spec), set `register_map` to `[]`
    and add a `⚠️ NEEDS_REVIEW` note.

13. **Proprietary / Non-standard Interfaces** — For any interface whose protocol does NOT match a
    standard (AXI4, AXI4-Lite, AXI4-Stream, AHB, APB, SPI, I2C, UART, PCIe, USB, TileLink, CHI,
    ACE), extract the full protocol detail needed to generate a VIP:
    - Signal-by-signal list: signal name, direction, width, description
    - Clock/reset relationships (which clock drives this interface)
    - Protocol phases: describe each phase (e.g. arbitration, address, data, response)
    - Timing diagram in prose form (e.g. "addr valid on rising edge, data captured 2 cycles later")
    - Handshake mechanism (req/ack, valid/ready, or other)
    - Ordering rules (in-order, out-of-order, pipelined?)
    - Error signaling mechanism
    If all interfaces are standard protocols, set `proprietary_interfaces` to `[]`.

---

## Step 4 — Check Environment

Before writing any output, verify that the common scripts and Python are available.
Run the environment check using the shared script:

```bash
python3 <SKILL_DIR>/../../common/scripts/check_environment.py --skill s1
```

Where `<SKILL_DIR>` is the directory containing this SKILL.md file
(i.e. `skills/dv-spec-parse/`), so the common scripts path resolves to
`skills/common/scripts/`.

**If Bash is not available:** Write the spec data JSON to
`/tmp/<project_name>_spec_data.json` manually (Step 5), then inform the user:
> "Bash is not available in this session. Please run the following command
> to generate the output files:
> `python3 <path_to_common>/write_spec_summary.py --data /tmp/<project>_spec_data.json --output <OUTPUT_DIR> --project <PROJECT_NAME>`"
> Then stop — do not attempt to write output files manually.

**If Python is not available at all:** Write both output files directly using
the Write tool as described in the fallback section below.

---

## Step 5 — Build Spec Data JSON

Assemble all extracted information into a structured JSON object matching
this schema exactly (this is the canonical downstream-compatible format):

```json
{
  "project_name": "<PROJECT_NAME>",
  "source_spec":  "<SPEC_FILE>",
  "generated_by": "dv-spec-parse",
  "date":         "<YYYY-MM-DD>",
  "block_overview": "<paragraph>",
  "features": [
    { "id": 1, "name": "", "description": "", "subfeatures": [
      { "id": "1.1", "name": "", "description": "" }
    ]}
  ],
  "interfaces": [
    { "name": "", "type": "", "protocol": "", "width": "", "direction": "",
      "signals": [
        { "name": "", "direction": "", "width": "", "description": "" }
      ]
    }
  ],
  "parameters":         [{ "name": "", "default": "", "description": "" }],
  "clock_domains":      [{ "name": "", "source": "", "frequency": "", "affected_logic": "" }],
  "reset_strategy":     [{ "name": "", "type": "", "polarity": "", "affected_domains": "" }],
  "operating_modes":    [{ "name": "", "description": "", "configuration": "" }],
  "compliance_standards": [{ "standard": "", "version": "", "notes": "" }],
  "known_constraints":  [],
  "register_map": [
    {
      "name":        "REG_NAME",
      "offset":      "0x00",
      "reset_value": "0x00000000",
      "description": "",
      "is_shadowed":    false,
      "is_interrupt_reg": false,
      "fields": [
        {
          "name":        "FIELD_NAME",
          "bits":        "[7:0]",
          "width":       8,
          "access":      "RW",
          "reset_value": "0x00",
          "description": ""
        }
      ]
    }
  ],
  "proprietary_interfaces": [
    {
      "name":       "if_name",
      "description": "",
      "signals": [
        { "name": "", "direction": "", "width": "", "description": "" }
      ],
      "clock":        "clk_name",
      "reset":        "rst_name",
      "phases": [
        { "name": "", "description": "", "timing": "" }
      ],
      "handshake":    "req/ack | valid/ready | other — describe",
      "ordering":     "in-order | out-of-order | pipelined",
      "error_signal": ""
    }
  ],
  "needs_review":       []
}
```

Write this to `/tmp/<project_name>_spec_data.json`.

---

## Step 6 — Generate Output Files via Common Script

Run the shared output writer:

```bash
python3 <SKILL_DIR>/../../common/scripts/write_spec_summary.py \
  --data    /tmp/<project_name>_spec_data.json \
  --output  <OUTPUT_DIR> \
  --project <PROJECT_NAME>
```

This script generates both `dv_spec_summary.md` and `dv_spec_summary.json`
in `OUTPUT_DIR` and prints the terminal summary automatically.

### Fallback — if Bash unavailable

If Bash cannot be executed, write both files directly using the Write tool:
- `<OUTPUT_DIR>/dv_spec_summary.md` — use the 11-section markdown structure
- `<OUTPUT_DIR>/dv_spec_summary.json` — write the JSON from Step 5 directly

Then print the terminal summary manually:

```
============================================================
  DV Spec Parse — Complete
  Project  : <PROJECT_NAME>
  Source   : <SPEC_FILE>
  Output   : <OUTPUT_DIR>
------------------------------------------------------------
  Extracted:
    Features          : <N>
    Sub-features      : <N>
    Interfaces        : <N>
    Signals           : <N>
    Parameters        : <N>
    Clock Domains     : <N>
    Operating Modes   : <N>
    Compliance Stds   : <N>
    Registers         : <N>  (fields: <N>)
    Proprietary IFs   : <N>
------------------------------------------------------------
  ⚠️  Items needing review : <N>
  Output files:
    → <OUTPUT_DIR>/dv_spec_summary.md
    → <OUTPUT_DIR>/dv_spec_summary.json
------------------------------------------------------------
  Next step: run /dv-testplan to generate the testplan
  Note: Register map (Registers: <N>) feeds /dv-tb-scaffold (S5) RAL generation
============================================================
```

---

## Important Notes

- Be thorough — missing a feature or interface here means it will be missing from the
  entire downstream DV flow (testplan, coverage, TB)
- When in doubt, include the item and mark it `⚠️ NEEDS_REVIEW` rather than omitting it
- Use precise, hardware-accurate language (e.g. "active-low asynchronous reset" not just "reset")
- Interface and signal names should match the spec exactly (preserve case and underscores)
- The JSON output must be valid — validate mentally before writing
- Do NOT invent features or signals that are not in the spec
