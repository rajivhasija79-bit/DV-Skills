#!/bin/bash
# Quick end-to-end test for run_eval.py using chipagents backend
# Can be run from anywhere — paths are resolved relative to this script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_CREATOR_DIR="$SCRIPT_DIR/../skill-creator"
EVAL_FILE="$SCRIPT_DIR/test_eval.json"

python3 "$SKILL_CREATOR_DIR/scripts/run_eval.py" \
  --skill-path "$SKILL_CREATOR_DIR" \
  --eval-set "$EVAL_FILE" \
  --runs-per-query 1 \
  --backend chipagents \
  --verbose
