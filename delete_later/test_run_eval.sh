#!/bin/bash
# Quick end-to-end test for run_eval.py using chipagents backend
# Run from the skill-creator directory:
#   cd /path/to/DV-Skills/skill-creator
#   bash ../delete_later/test_run_eval.sh

python3 scripts/run_eval.py \
  --skill-path . \
  --eval-set ../delete_later/test_eval.json \
  --runs-per-query 1 \
  --backend chipagents \
  --verbose
