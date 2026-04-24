# Regression-History Correlation — incremental index

Regression runs append new data every time they execute. Maintain an incremental index; never re-parse the full history.

## Canonical schema

Every row in the source must be mapped to:

```
{ testcase, seed, result, commit, timestamp, duration, log_path }
```

- `testcase`: string, unique testcase name.
- `seed`: int or string.
- `result`: one of `pass | fail | timeout | error | unknown`.
- `commit`: VCS commit hash or build id (may be empty).
- `timestamp`: ISO 8601.
- `duration`: seconds (may be null).
- `log_path`: absolute path to that run's log (may be null).

## Format sniffing

`regression_parse.py` inspects the source and picks a parser:

| Source | Detect | Parser |
|--------|--------|--------|
| `*.csv` | first byte `{` rejected, has commas, has header row | csv.DictReader |
| `*.tsv` | tabs in first line | csv.DictReader tab |
| `*.json` | starts with `[` or `{` | json |
| `*.ndjson` / `*.jsonl` | one JSON object per line | stream |
| Dashboard export (HTML/CSV hybrid) | detect `<table>` | basic HTML table scrape |
| Unknown | — | print headers and ask user |

## Column mapping cache

Once columns are confirmed for a source, cache them at `<source>.rtl-sim-debug.mapping.json`:

```json
{
  "format": "csv",
  "column_map": {
    "testcase": "tc_name",
    "seed":     "seed",
    "result":   "status",
    "commit":   "build_hash",
    "timestamp":"started_at",
    "duration": "elapsed_s",
    "log_path": "log"
  },
  "result_normalize": {
    "PASSED": "pass", "FAILED": "fail", "TIMED_OUT": "timeout", "ERROR": "error"
  }
}
```

On next run, the mapping is applied automatically. Re-prompt only if the source's header changes.

## Index

### Location
Default: `<source_path>.rtl-sim-debug.reg.idx.json` (override with `--index-file`).

### Shape
```json
{
  "contract_version": 1,
  "last_ingested_row_key": "<testcase>|<seed>|<timestamp>",
  "testcases": {
    "<testcase>": {
      "runs": [ { "seed": ..., "result": ..., "commit": ..., "timestamp": ... } ],
      "rolling_fail_rate_30d": 0.12,
      "first_seen_fail": "2026-04-12T00:00:00Z",
      "last_pass_commit": "abcdef01",
      "last_fail_commit": "1234abcd"
    }
  },
  "daily_totals": {
    "2026-04-24": { "runs": 4821, "fails": 129, "new_fails": 17 }
  }
}
```

### Refresh flow
1. Determine the last-ingested row key from the existing index.
2. Stream-parse the source; skip rows with key ≤ last key.
3. For each new row, upsert into `testcases[tc]`; update rolling stats and `daily_totals`.
4. Acquire file lock, write new index, release.

## Queries

```
scripts/regression_parse.py --query <testcase> --index-file <path>
```
Returns:

```json
{
  "testcase": "...",
  "classification": "newly_failing|chronic|flaky|passing",
  "flakiness": 0.0,
  "rolling_fail_rate_30d": 0.0,
  "last_pass_commit": "...",
  "first_seen_fail": "...",
  "daily_context": { "broader_wave_today": true, "today_fails": 129, "today_avg_fails_30d": 45 }
}
```

### Classification rules
- **newly_failing**: `first_seen_fail` within last 24h AND `rolling_fail_rate_30d` > prior-week baseline * 2.
- **chronic**: same testcase fails consistently for >7 days.
- **flaky**: pass/fail mix on the same commit, varying seeds.
- **passing**: no fails in window.
- **broader_wave_today**: `daily_totals[today].fails` > 3 * `average(last 7 days excluding today)`.

## Impact on classification

Feed the query result into Phase 3:
- `broader_wave_today = true` → push toward **Env** or **Config**, even if the message looks RTL-ish.
- `flaky` on a stable commit → look for races: CDC, arbitration, TB sampling.
- `newly_failing` tied to a specific commit → bisect candidate; ask the user if they want a git-bisect plan.
