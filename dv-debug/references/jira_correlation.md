# JIRA Corpus Correlation — incremental index + query

The JIRA bug-report corpus is append-only and grows continuously. Never re-parse the whole corpus each run.

## Index

### Location
Default: `<corpus_dir>/.rtl-sim-debug.jira.idx.json` (override with `--index-file`).

### Shape
```json
{
  "contract_version": 1,
  "format": "mixed",
  "last_indexed_mtime": "2026-04-24T12:00:00Z",
  "file_digests": {
    "<relative_path>": "<sha1>"
  },
  "records": [
    {
      "id": "PROJ-1234",
      "source_file": "<path>",
      "summary": "...",
      "components": ["..."],
      "description_excerpt": "...",
      "resolution": "Fixed",
      "signature_hints": ["UVM_ERROR", "AXI4_ERRS_BRESP_SLVERR", "u_ddr.u_ctrl"]
    }
  ]
}
```

### Refresh flow
```
scripts/jira_parse.py --corpus <dir_or_files> --index-file <path>
```

1. Walk the corpus (dir or explicit file list).
2. For each file, compute sha1 → compare against `file_digests`.
3. Parse only new/changed files:
   - **Structured JSON/XML**: detect by extension + schema sniff (`fields.summary`, `issue/key`). Extract canonical fields.
   - **Plain text / markdown**: extract ticket id from filename (regex `[A-Z]+-\d+`) or first line; extract `Summary:` / `Description:` / `Resolution:` sections; fall back to first 500-char excerpt for description.
4. `signature_hints` are built from the parsed record by regex-extracting: UVM tags, known protocol message ids, module names matching common IP prefixes, and file-paths mentioned inside.
5. Acquire a `fcntl.flock` on the index file before writing.

## Query

```
scripts/jira_parse.py --query \
    --index-file <path> \
    --signature '{"message_id":"...","component_tail":"...","file_line":"...","assertion_name":"..."}' \
    --top 5
```

### Ranking
Compute overlap score against each record's `signature_hints`:
- `+3` per exact match.
- `+1` per substring match of normalized component tail.
- `+2` per matching message id.
- `+2` per matching assertion name.
- `+1` per matching file basename.
- Normalize by record's hint count (avoid favoring verbose tickets).

### Output
```json
[
  {
    "id": "PROJ-1234",
    "similarity": 0.82,
    "summary": "...",
    "components": ["..."],
    "resolution": "Fixed",
    "root_cause": "<first sentence of resolution or description>",
    "fix": "<commit or phrase mentioning 'Fix' / 'Resolution'>",
    "source_file": "<path>"
  }
]
```

### Classification of the current failure
- Top hit similarity ≥ 0.75 → current failure is **same** as a known issue. Surface it prominently in the exit summary.
- 0.4–0.75 → **similar**; cite as a hint but continue RCA.
- < 0.4 → **new**; no related prior ticket.

## Manual fallback (no scripts)

If scripts can't run, the agent can do a degraded version inline:
1. Grep the corpus dir for the literal `message_id` or `assertion_name`.
2. For each match, read ±30 lines of context.
3. Rank by whether `component_tail` also appears nearby.

This is slower but works for small corpora.
