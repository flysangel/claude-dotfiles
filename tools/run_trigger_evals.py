#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run each skill's trigger cases through `claude -p` in a throwaway project.

This calls the model and costs money, so it runs only when asked to.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_TOOLS = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Agent"
TIMEOUT_SECONDS = 180


@dataclass
class Outcome:
    invoked: list[str]
    cost: float
    error: str = ""


def parse_stream(lines: list[str]) -> Outcome:
    invoked: list[str] = []
    cost = 0.0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    invoked.append(str(block.get("input", {}).get("skill", "")))
        elif event.get("type") == "result":
            cost = float(event.get("total_cost_usd") or 0.0)
    return Outcome(invoked, cost)


def was_invoked(skill: str, outcome: Outcome) -> bool:
    return any(name == skill or name.endswith(f":{skill}") for name in outcome.invoked)


def run_prompt(prompt: str, project: Path, model: str) -> Outcome:
    command = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        "--max-turns",
        "1",
        "--disallowedTools",
        BLOCKED_TOOLS,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Outcome([], 0.0, str(error))
    return parse_stream(result.stdout.splitlines())


def eval_skill(skill: str, model: str) -> tuple[int, int, float]:
    cases = json.loads((ROOT / "tests" / "skills" / skill / "triggers.json").read_text(encoding="utf-8"))
    passed = failed = 0
    cost = 0.0
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        shutil.copytree(ROOT / "home" / "skills" / skill, project / ".claude" / "skills" / skill)
        for expected, key in ((True, "should_trigger"), (False, "should_not_trigger")):
            for prompt in cases.get(key, []):
                outcome = run_prompt(prompt, project, model)
                cost += outcome.cost
                ok = not outcome.error and was_invoked(skill, outcome) == expected
                passed += ok
                failed += not ok
                label = "PASS" if ok else "FAIL"
                suffix = f" ({outcome.error})" if outcome.error else ""
                print(f"{label} {skill} {key}: {prompt}{suffix}")
    return passed, failed, cost


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", nargs="?", help="只執行這個 skill，預設全部")
    parser.add_argument("--model", default="haiku", help="使用的模型，預設 haiku")
    parser.add_argument("--yes", action="store_true", help="略過費用確認")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

    available = sorted(path.parent.name for path in (ROOT / "tests" / "skills").glob("*/triggers.json"))
    skills = [args.skill] if args.skill else available
    missing = [skill for skill in skills if skill not in available]
    if missing:
        print(f"找不到觸發案例：{', '.join(missing)}", file=sys.stderr)
        return 2
    if not skills:
        print("沒有任何觸發案例。")
        return 0
    if not args.yes:
        print(f"即將用模型 {args.model} 執行 {', '.join(skills)} 的觸發案例，這會產生費用。")
        if input("繼續嗎？(y/N) ").strip().lower() != "y":
            print("已取消。")
            return 2

    total_passed = total_failed = 0
    total_cost = 0.0
    for skill in skills:
        passed, failed, cost = eval_skill(skill, args.model)
        total_passed += passed
        total_failed += failed
        total_cost += cost
    print(f"通過 {total_passed}，失敗 {total_failed}，費用約 ${total_cost:.4f}")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main())
