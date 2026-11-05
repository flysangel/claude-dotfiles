"""Tests for the offline parts of tools/run_trigger_evals.py. Nothing here calls the model."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_trigger_evals", ROOT / "tools" / "run_trigger_evals.py")
evals = importlib.util.module_from_spec(spec)
sys.modules["run_trigger_evals"] = evals
spec.loader.exec_module(evals)


def tool_event(name: str, skill: str) -> str:
    content = [{"type": "tool_use", "name": name, "input": {"skill": skill}}]
    return json.dumps({"type": "assistant", "message": {"content": content}})


class ParseStreamTests(unittest.TestCase):
    def test_finds_skill_and_cost(self) -> None:
        lines = [tool_event("Skill", "sdd-grill"), json.dumps({"type": "result", "total_cost_usd": 0.5})]
        outcome = evals.parse_stream(lines)
        self.assertEqual(outcome.invoked, ["sdd-grill"])
        self.assertEqual(outcome.cost, 0.5)

    def test_ignores_other_tools_and_bad_lines(self) -> None:
        outcome = evals.parse_stream([tool_event("Read", "sdd-grill"), "not json"])
        self.assertEqual(outcome.invoked, [])

    def test_was_invoked_accepts_namespaced_name_only_when_exact(self) -> None:
        outcome = evals.Outcome(["plugin:sdd-grill"], 0.0)
        self.assertTrue(evals.was_invoked("sdd-grill", outcome))
        self.assertFalse(evals.was_invoked("grill", outcome))


if __name__ == "__main__":
    unittest.main()
