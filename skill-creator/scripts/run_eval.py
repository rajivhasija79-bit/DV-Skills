#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes Claude to trigger (invoke the skill)
for a set of queries. Outputs results as JSON.

Backend selection via --backend flag or LLM_BACKEND env var (priority order):
  1. LLM_BACKEND=chipagent  → uses chipagent batch --prompt (needs chipagent CLI)
  2. LLM_BACKEND=anthropic  → uses anthropic Python SDK (needs ANTHROPIC_API_KEY)
  3. LLM_BACKEND=claude_cli → uses `claude -p` subprocess (needs Claude Code)
  4. Default/auto           → tries chipagent → anthropic SDK → claude CLI
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Allow running from any directory by adding skill-creator root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils import parse_skill_md


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def _get_model(model: str | None) -> str:
    return model or os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5-20251101")


def _call_chipagent(prompt: str, timeout: int = 60) -> str:
    """Call LLM via chipagent batch non-interactive mode.

    Uses --output to capture response via temp file, which is more reliable
    than stdout capture for long responses.
    Note: chipagent uses its own configured model; --model is not supported.
    """
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        output_file = f.name

    try:
        cmd = [
            "chipagents", "batch",
            "--prompt", prompt,
            "--output", output_file,
        ]
        working_dir = os.environ.get("CHIPAGENT_WORKING_DIR")
        if working_dir:
            cmd.extend(["--working-directory", working_dir])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"chipagents batch exited {result.returncode}\nstderr: {result.stderr}"
            )
        # Prefer output file; fall back to stdout
        out_path = Path(output_file)
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path.read_text(encoding="utf-8")
        return result.stdout
    finally:
        try:
            Path(output_file).unlink(missing_ok=True)
        except Exception:
            pass


def _call_anthropic_sdk(prompt: str, model: str | None, max_tokens: int = 16) -> str:
    """Call Claude via the Anthropic Python SDK."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        )
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),  # chipagent override if needed
    )
    message = client.messages.create(
        model=_get_model(model),
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_claude_cli(prompt: str, model: str | None, max_tokens: int = 16) -> str:
    """Call Claude via the claude CLI subprocess (Claude Code)."""
    import subprocess
    cmd = ["claude", "-p", prompt, "--output-format", "text"]
    if model:
        cmd.extend(["--model", model])
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"claude -p exited {result.returncode}: {result.stderr}")
    return result.stdout.strip()


def _call_llm(prompt: str, model: str | None, max_tokens: int = 16) -> str:
    """Call LLM using the configured backend."""
    backend = os.environ.get("LLM_BACKEND", "auto").lower()
    if backend == "chipagent":
        return _call_chipagent(prompt)
    elif backend == "claude_cli":
        return _call_claude_cli(prompt, model, max_tokens)
    elif backend == "anthropic":
        return _call_anthropic_sdk(prompt, model, max_tokens)
    else:
        # auto: try chipagent → anthropic SDK → claude CLI
        for fn in [
            lambda: _call_chipagent(prompt),
            lambda: _call_anthropic_sdk(prompt, model, max_tokens),
            lambda: _call_claude_cli(prompt, model, max_tokens),
        ]:
            try:
                return fn()
            except Exception:
                continue
        raise RuntimeError("All LLM backends failed. Set LLM_BACKEND explicitly.")


# ---------------------------------------------------------------------------
# Project root (kept for backward compat with run_loop.py)
# ---------------------------------------------------------------------------

def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


# ---------------------------------------------------------------------------
# Core eval logic
# ---------------------------------------------------------------------------

def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,         # kept for API compat, unused in SDK path
    model: str | None = None,
) -> bool:
    """Return True if Claude would invoke this skill for the given query.

    Asks Claude directly via the SDK: given the skill name + description,
    would you invoke this skill to handle the user query?
    This replaces the previous approach of injecting a command file and
    watching Claude Code's stream output for tool calls.
    """
    prompt = (
        f'You are Claude. You have exactly one skill available:\n\n'
        f'  Skill name: {skill_name}\n'
        f'  Skill description: {skill_description}\n\n'
        f'A user sends you this query: "{query}"\n\n'
        f'Would you invoke this skill to handle the query?\n'
        f'Reply with exactly one word: YES or NO.'
    )
    try:
        response = _call_llm(prompt, model, max_tokens=10)
        return response.strip().upper().startswith("YES")
    except Exception as e:
        print(f"Warning: query failed ({e})", file=sys.stderr)
        return False


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        did_pass = (
            trigger_rate >= trigger_threshold if should_trigger
            else trigger_rate < trigger_threshold
        )
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set",          required=True,          help="Path to eval set JSON file")
    parser.add_argument("--skill-path",        required=True,          help="Path to skill directory")
    parser.add_argument("--description",       default=None,           help="Override description to test")
    parser.add_argument("--num-workers",       type=int, default=10,   help="Number of parallel workers")
    parser.add_argument("--timeout",           type=int, default=30,   help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query",    type=int, default=3,    help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5,help="Trigger rate threshold")
    parser.add_argument("--model",             default=None,           help="Model to use")
    parser.add_argument("--verbose",           action="store_true",    help="Print progress to stderr")
    parser.add_argument("--backend",           default=None,
                        help="LLM backend: chipagent | anthropic | claude_cli (overrides LLM_BACKEND env var)")
    args = parser.parse_args()

    if args.backend:
        os.environ["LLM_BACKEND"] = args.backend

    eval_set   = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, _ = parse_skill_md(skill_path)
    description  = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Backend : {os.environ.get('LLM_BACKEND', 'auto')}", file=sys.stderr)
        print(f"Model   : {_get_model(args.model)}", file=sys.stderr)
        print(f"Eval    : {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results : {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status   = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}",
                  file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
