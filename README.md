# DV-Skills — ChipAgent

End-to-end verification skills (S1–S10) with a web GUI.

---

## Quick Start (Linux / macOS)

### 1. Clone the repo
```bash
git clone https://github.com/rajivhasija79-bit/DV-Skills.git
cd DV-Skills
```

### 2. Install Python dependencies
```bash
cd dv-gui
pip3 install -r requirements.txt
```

> Requires **Python 3.10+**. Use a virtualenv if you prefer:
> ```bash
> python3 -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> ```

### 3. Run the GUI
```bash
python3 app.py
```

Then open your browser at **http://localhost:7437**

---

## What's inside

| Directory | Purpose |
|-----------|---------|
| `dv-gui/` | Flask web app — Project Settings + 10-skill wizard |
| `dv-gui/scripts/` | Bash scripts executed by Project Settings section buttons |
| `skills/common/scripts/` | Python scripts for S6–S10 skill execution |
| `skills/dv-*/` | Per-skill prompt and eval data |

## Skill pipeline

```
S1 Spec Extraction → S2 Testplan → S3 TB Architecture → S4 RAL → S5 TB Scaffold
                                                                        ↓
                                         S6 Sequences → S9 Regression → S10 Coverage
                                         S7 Assertions → S8 Scoreboard ↗
```

S1–S5 are AI-driven (demo mode in the GUI).  
S6–S10 run real Python scripts when upstream data files exist, and fall back to demo mode otherwise.
