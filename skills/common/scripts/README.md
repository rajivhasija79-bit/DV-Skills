# DV Skills — Common Scripts

Shared Python utilities used across all DV skills.
All skills reference these scripts via the relative path `../../common/scripts/`.

## Scripts

| Script | Used by | Purpose |
|---|---|---|
| `check_environment.py` | S1, S2, S3+ | Check and auto-install Python dependencies |
| `write_spec_summary.py` | S1 | Write `dv_spec_summary.md` + `dv_spec_summary.json` from parsed spec data |
| `generate_testplan_excel.py` | S2 | Generate 2-sheet `testplan.xlsx` from testplan row data |

## Usage

### Environment check (run before any skill)
```bash
python3 skills/common/scripts/check_environment.py --skill s1
python3 skills/common/scripts/check_environment.py --skill s2
python3 skills/common/scripts/check_environment.py --skill all --install
```

### S1 — Write spec summary outputs
```bash
python3 skills/common/scripts/write_spec_summary.py \
  --data    /tmp/<project>_spec_data.json \
  --output  <output_dir> \
  --project <project_name>
```

### S2 — Generate testplan Excel
```bash
python3 skills/common/scripts/generate_testplan_excel.py \
  --data    /tmp/<project>_testplan_data.json \
  --output  <output_dir>/testplan.xlsx \
  --project <project_name>
```

## Adding a new script

1. Place it here in `skills/common/scripts/`
2. Add a row to the table above
3. Add its dependency to `check_environment.py` DEPS map
4. Reference it from the skill's SKILL.md using `../../common/scripts/<script>.py`
