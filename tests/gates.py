"""Skip tests that cannot run here, unless CI says they must.

Contract: specs/004-ci-e2e-tests/contracts/test-gates.md
"""

from __future__ import annotations

import functools
import os
import unittest


def required_groups() -> set[str]:
    return {group.strip() for group in os.environ.get("REQUIRED_TEST_GROUPS", "").split(",") if group.strip()}


def requires(group: str, condition: object, reason: str):
    """Like unittest.skipUnless, but a required group fails instead of being skipped."""
    if condition:
        return lambda target: target
    if group not in required_groups():
        return unittest.skip(reason)
    message = f"test group {group} is required here, but cannot run: {reason}"

    def fail_instead(target):
        if isinstance(target, type):
            def set_up(self: unittest.TestCase) -> None:
                self.fail(message)

            target.setUp = set_up
            return target

        @functools.wraps(target)
        def failing(self: unittest.TestCase, *args: object, **kwargs: object) -> None:
            self.fail(message)

        return failing

    return fail_instead
