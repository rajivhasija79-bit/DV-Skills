# Domain Skill Contract — rtl-sim-debug-\<domain\>

This document specifies how a domain (subsystem) sub-skill plugs into `rtl-sim-debug`. The parent discovers and invokes such skills automatically; new skills require **no parent-side changes** to be picked up.

## Contract version

`contract_version: 1`

Domain skills MUST declare the `contract_version` they implement. The parent refuses to invoke a skill whose contract version is greater than its own.

## Naming and location

- Directory: `~/.claude/skills/rtl-sim-debug-<subsystem>/`
- `<subsystem>`: lowercase, hyphen-separated (`ddr`, `pcie`, `noc`, `cpu`, `eth-mac`, …).

## Required `SKILL.md` frontmatter

```yaml
---
name: rtl-sim-debug-<subsystem>
description: >
  One-line summary. Include the subsystem name and scope (controllers/PHY/etc.).
  Must include trigger keywords the runtime uses for fuzzy matching.
contract_version: 1
domain_triggers:
  interface_keywords:   [ "regex", ... ]   # e.g., ["\\bDDR[345]?\\b", "dfi_", "mrs"]
  hierarchy_tokens:     [ "regex", ... ]   # e.g., ["ddr_ctrl", "phy_ddr", "u_mc_"]
  rtl_module_prefixes:  [ "string", ... ]  # e.g., ["ddr4_", "ddrphy_", "mc_"]
  log_message_ids:      [ "string", ... ]  # e.g., ["DDR_TIMING_VIOL", "DFI_HS_ERR"]
required_context_fields:
  - failure_digest
  - interface
  - waveform_window
  - artifacts
---
```

A domain skill **matches** if any regex/prefix in any of the four trigger groups matches the Domain Signature the parent built.

## Inputs: Debug Context Package (parent → domain)

```json
{
  "contract_version": 1,
  "failure_digest": {
    "time": "<ns>",
    "phase": "run_phase",
    "hierarchy": "tb.u_soc.u_ddr.u_ctrl",
    "message_id": "DDR_TIMING_VIOL",
    "file_line": "ddr_ctrl.sv:412",
    "raw_excerpt": "..."
  },
  "classification": { "class": "RTL", "confidence": "medium", "evidence": "..." },
  "regression_context": { "newly_failing": false, "flakiness": 0.0, "broader_wave": false },
  "interface": {
    "name": "AXI_DDR_SLV",
    "type": "AXI4",
    "signals": ["tb.u_soc.u_ddr.awvalid", ...],
    "rc_file_entries": ["DDR_WR", "DDR_RD"]
  },
  "waveform_window": {
    "format": "vcd",
    "path": "/tmp/dump.vcd",
    "t0": 100000,
    "t1": 102000,
    "signals_extracted": ["..."]
  },
  "rtl_trace": [
    { "file": "ddr_ctrl.sv", "line": 412, "assignment": "...", "time": 100500 }
  ],
  "jira_hits": [
    { "id": "DDR-123", "similarity": 0.6, "root_cause": "...", "fix": "..." }
  ],
  "artifacts": {
    "log": "...", "rtl_root": "...", "dv_root": "...",
    "filelists": ["..."], "spec_refs": ["..."],
    "tc_understanding": "...", "reg_model": "..."
  }
}
```

## Output: Domain response (domain → parent)

```json
{
  "contract_version": 1,
  "protocol_hypotheses": [
    {
      "cause": "tRCD violated (<5 cycles) between ACT and RD",
      "evidence_refs": ["waveform row 42", "ddr_ctrl.sv:412"],
      "confidence": "high"
    }
  ],
  "extra_checks": [
    { "what": "Compare programmed tRCD to JEDEC minimum", "how": "Read MR1[3:0]", "expected": "tRCD >= spec" }
  ],
  "likely_fix_or_jira": {
    "kind": "jira_draft",
    "title": "DDR4 ctrl issues RD < tRCD after ACT",
    "body": "..."
  },
  "additional_signals": [
    "tb.u_soc.u_ddr.u_ctrl.tRCD_counter",
    "tb.u_soc.u_ddr.u_ctrl.cmd_state"
  ]
}
```

`additional_signals` can be fed back into `vcd_window.py` for a refined waveform trace if the parent wants to finalize evidence.

## Rules for domain skills

1. **Do not duplicate the parent's work.** The parent already provides digest, classification, JIRA hits, regression context, waveform, and initial trace. Domain skills add *protocol-specific* hypotheses only.
2. **Cite every hypothesis.** `evidence_refs` must point to the provided artifacts.
3. **No RTL edits.** Same rule as the parent.
4. **Be format-agnostic.** Never assume `.fsdb` or `.vcd`; consume whatever the parent gives.
5. **Internal structure is your choice.** Domain skills typically have their own `references/` with per-IP playbooks (e.g., `references/controller.md`, `references/phy.md`, `references/smmu.md` for DDR). The parent doesn't care.
6. **Return quickly.** Domain skills are invoked inline; keep hypothesis lists focused (≤ 5 entries).

## Versioning / evolution

- New fields can be added to the Context Package; old domain skills must ignore unknown fields.
- Removing or renaming existing fields requires a `contract_version` bump.
- Parent checks `contract_version` before dispatch and refuses incompatible skills cleanly (logged, not errored).

## Starter template for a new domain skill

```
~/.claude/skills/rtl-sim-debug-<subsystem>/
├── SKILL.md                              # frontmatter as above + workflow
├── references/
│   ├── protocol_spec_cheatsheet.md
│   ├── common_failure_modes.md
│   └── per_ip_playbooks/
│       ├── controller.md
│       ├── phy.md
│       └── ...
└── scripts/                              # optional
```

When starting a new domain skill, copy this structure and fill in the frontmatter, the protocol knowledge, and any per-IP playbooks.
