"""Tests for tests/gates.py."""

from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates  # noqa: E402


def outcome(group: str, condition: bool, required: str | None) -> unittest.TestResult:
    env = {key: value for key, value in os.environ.items() if key != "REQUIRED_TEST_GROUPS"}
    if required is not None:
        env["REQUIRED_TEST_GROUPS"] = required
    with mock.patch.dict(os.environ, env, clear=True):
        @gates.requires(group, condition, "needs something")
        class Sample(unittest.TestCase):
            def test_one(self) -> None:
                pass

            def test_two(self) -> None:
                pass

        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromTestCase(Sample).run(result)
    result.stream = io.StringIO()
    return result


class GateTests(unittest.TestCase):
    def test_not_required_and_available_runs(self) -> None:
        result = outcome("shell", True, None)
        self.assertEqual((result.testsRun, len(result.skipped), len(result.failures)), (2, 0, 0))

    def test_not_required_and_unavailable_skips_with_the_reason(self) -> None:
        result = outcome("shell", False, "other")
        self.assertEqual((len(result.skipped), len(result.failures)), (2, 0))
        self.assertEqual(result.skipped[0][1], "needs something")

    def test_required_and_available_runs(self) -> None:
        result = outcome("shell", True, "shell")
        self.assertEqual((result.testsRun, len(result.skipped), len(result.failures)), (2, 0, 0))

    def test_required_and_unavailable_fails_every_test(self) -> None:
        result = outcome("shell", False, "other, shell")
        self.assertEqual((len(result.skipped), len(result.failures)), (0, 2))
        self.assertIn("shell", result.failures[0][1])

    def test_empty_setting_requires_nothing(self) -> None:
        self.assertEqual(len(outcome("shell", False, "").skipped), 2)

    def test_decorated_function_fails_when_required(self) -> None:
        with mock.patch.dict(os.environ, {"REQUIRED_TEST_GROUPS": "shell"}):
            class Sample(unittest.TestCase):
                @gates.requires("shell", False, "needs something")
                def test_one(self) -> None:
                    pass

            result = unittest.TestResult()
            unittest.defaultTestLoader.loadTestsFromTestCase(Sample).run(result)
        self.assertEqual(len(result.failures), 1)


if __name__ == "__main__":
    unittest.main()
