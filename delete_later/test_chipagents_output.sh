#!/bin/bash
# Quick test to verify chipagents --output writes response to file correctly
# Run this before running run_eval.py to confirm chipagents batch mode works

chipagents batch --prompt "say the word HELLO only" --output ./test_out.txt && cat ./test_out.txt
