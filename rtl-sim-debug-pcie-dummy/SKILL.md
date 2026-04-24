---
name: rtl-sim-debug-pcie-dummy
description: >
  DEMO/TEMPLATE domain sub-skill for PCIe subsystem RTL debug. Plugs into
  the parent rtl-sim-debug skill. Triggers on PCIe LTSSM, TLP, DLLP, flow
  control, PIPE, controller/PHY messages. Scope covers PCIe controller,
  PIPE PHY, link training, TLP layer. Not a real PCIe debug skill — built
  to teach how to author rtl-sim-debug-<subsystem> skills. Rename/flesh out
  to productize.
contract_version: 1
domain_triggers:
  interface_keywords:
    - "\\bPCIe\\b"
    - "\\bPCI[_ ]?Express\\b"
    - "\\bLTSSM\\b"
    - "\\bTLP\\b"
    - "\\bDLLP\\b"
    - "\\bPIPE\\b"
    - "\\bGen[1-6]\\b"
  hierarchy_tokens:
    - "pcie_ctrl"
    - "pcie_phy"
    - "u_pcie"
    - "pcie_x\\d+"
    - "dll_"
    - "tl_"
    - "ltssm"
  rtl_module_prefixes:
    - "pcie_"
    - "ltssm_"
    - "tl_"
    - "dll_"
    - "pipe_"
  log_message_ids:
    - "PCIE_LTSSM_STUCK"
    - "PCIE_TLP_MALFORMED"
    - "PCIE_FC_CREDIT_UNDERFLOW"
    - "PCIE_CRC_ERR"
    - "PCIE_POISONED_TLP"
    - "PCIE_COMPLETION_TIMEOUT"
required_context_fields:
  - failure_digest
  - interface
  - waveform_window
  - artifacts
---

# rtl-sim-debug-pcie-dummy — domain sub-skill (DEMO)

This is a **teaching template** for how to write a domain sub-skill that plugs into the parent `rtl-sim-debug`. It is intentionally small. Every line is annotated so you can see what is required vs. what is customization.

## How you are invoked

The parent `rtl-sim-debug` builds a **Domain Signature** from the failure and checks it against every installed sibling's `domain_triggers` frontmatter. If any regex / prefix / keyword here matches the signature, the parent invokes this skill and hands you a **Debug Context Package** (JSON, shape documented in the parent's `domain_skill_contract.md`).

You do not run standalone. You are a callee.

## Contract — what you receive

Expect a JSON object with at least these fields (enforced by `required_context_fields` above):

- `failure_digest` — where/when/what failed, plus the raw log excerpt.
- `interface` — which interface the parent thinks is involved, with a curated signal list (already pulled from the user's Verdi `.rc`).
- `waveform_window` — the window the parent already extracted (`.vcd` or `.fsdb`). Do NOT re-extract the whole dump.
- `artifacts` — paths to log, RTL root, DV root, filelists, specs, testcase-understanding, register model.

Optional but usually present:
- `classification`, `regression_context`, `rtl_trace`, `jira_hits`.

## Workflow (the part you customize per domain)

### Step 1 — Locate the IP within the subsystem
PCIe subsystem has multiple IPs: **controller, PIPE PHY, link-training FSM (LTSSM), TLP layer, DLLP layer, flow-control**. Figure out which one owns the failure:

1. Walk the failure's hierarchy. Tokens like `ltssm`, `tl_`, `dll_`, `phy_`, `pipe_` tell you which IP.
2. Check the `message_id` against the IP playbooks in `references/per_ip_playbooks/`.
3. Pick one playbook and follow it; if ambiguous, pick two and run both.

Available playbooks in this demo:
- `references/per_ip_playbooks/ltssm.md`
- `references/per_ip_playbooks/tlp_layer.md`

### Step 2 — Apply protocol knowledge
Use `references/protocol_spec_cheatsheet.md` (states, packet formats, timing) to answer protocol-specific questions the parent's generic checklist could not:

- LTSSM: which state sequence was expected? which was observed? where did it diverge?
- TLP: parse header bytes from waveform; identify FMT/TYPE; validate against spec.
- Flow control: compute credit balance from waveform; detect underflow/overflow.

### Step 3 — Form protocol hypotheses
Produce **at most 5** hypotheses. Each must cite evidence from the provided artifacts (`waveform_window.changes[i]`, `rtl_trace[j].file:line`, `failure_digest.raw_excerpt` line N). Do NOT invent evidence.

### Step 4 — Propose extra checks
List the smallest additional observations that would confirm or deny each hypothesis. These go back to the parent, which may re-extract more waveform signals (via `additional_signals`) and hand back a refined context.

### Step 5 — Produce fix-or-JIRA
- If the root cause is **RTL**: emit a JIRA-ready block (title, signature, repro, observed vs. expected, waveform evidence, suggested owner).
- If **config/plusarg**: emit a concrete edit.
- You do NOT modify RTL. Same rule as the parent.

## Output — what you return

Emit EXACTLY this JSON shape (schema lives in the parent's `domain_skill_contract.md`):

```json
{
  "contract_version": 1,
  "protocol_hypotheses": [
    {
      "cause":         "LTSSM stuck in Polling.Active because RX did not see 8 consecutive TS1s",
      "evidence_refs": ["waveform rows 12-34 (rx_valid, rx_data)", "ltssm.sv:245"],
      "confidence":    "medium"
    }
  ],
  "extra_checks": [
    {
      "what":     "Check PIPE interface rx_valid continuity for 4us before failure",
      "how":      "Re-extract pipe_rx_valid, pipe_rx_data over [fail_time-4us, fail_time]",
      "expected": "rx_valid asserted at least 8 times with TS1 SOS pattern"
    }
  ],
  "likely_fix_or_jira": {
    "kind":  "jira_draft",
    "title": "DEMO: LTSSM stuck in Polling.Active - rx_valid gaps",
    "body":  "<fill in with real evidence>"
  },
  "additional_signals": [
    "tb.u_dut.u_pcie.u_phy.pipe_rx_valid",
    "tb.u_dut.u_pcie.u_phy.pipe_rx_data",
    "tb.u_dut.u_pcie.u_ltssm.state"
  ]
}
```

The parent merges your output into its final exit summary, tagging each hypothesis with the domain name.

---

## Anatomy of this skill — annotated checklist

Use this as a copy-template when writing a real domain skill (DDR, NoC, CPU, etc.):

1. **Frontmatter `name`** — MUST start with `rtl-sim-debug-`. This is the discovery prefix.
2. **`description`** — first line is the key one; the runtime may rank skills by it during fuzzy matching.
3. **`contract_version`** — match the parent's contract. Parent refuses skills whose version is newer than its own.
4. **`domain_triggers`** — the four categories are ORed. Put broad regexes here; false-positives on trigger are cheap, false-negatives silently skip you.
5. **`required_context_fields`** — list every context field you actually read. The parent refuses to dispatch if any are missing (fail-fast).
6. **References directory** — this is where your domain *knowledge* lives. The main SKILL.md only orchestrates.
7. **Per-IP playbooks** — a subsystem has many IPs (PCIe has controller, PHY, LTSSM, TL, DLL...). One playbook per IP, indexed by Step 1 of the workflow.
8. **Scripts directory (optional)** — only if you have format-specific parsing (e.g., TLP packet decoder). Must be stdlib-only Python 3.
9. **Output schema adherence** — parent merges outputs from multiple domain skills; any deviation silently drops your contribution.

## To promote this demo into a real skill

1. Rename directory to `rtl-sim-debug-pcie`.
2. Rewrite `references/protocol_spec_cheatsheet.md` with actual PCIe 4.0/5.0/6.0 content you care about.
3. Expand `references/per_ip_playbooks/` with all IPs your PCIe subsystem has (controller, PIPE PHY, LTSSM, TL layer, DLL layer, flow-control, AER, SR-IOV, …).
4. Add a `scripts/tlp_decode.py` if you want to parse TLP headers from waveform hex blobs.
5. Tighten `domain_triggers` once you have false-match data.
6. Bump `contract_version` if/when the parent's contract changes.
