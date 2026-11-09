"""Static checks of .github/workflows/ci.yml, which can only really be exercised on GitHub."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def jobs(text: str) -> dict[str, str]:
    body = text[text.index("\njobs:\n") :]
    parts = re.split(r"^  ([\w-]+):\n", body, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.jobs = jobs(cls.text)

    def test_runs_on_every_push_and_on_demand(self) -> None:
        self.assertRegex(self.text, r"(?m)^on:\n  push:\n  workflow_dispatch:\n")

    def test_new_pushes_cancel_old_runs(self) -> None:
        self.assertIn("group: ci-${{ github.ref }}", self.text)
        self.assertIn("cancel-in-progress: true", self.text)

    def test_permissions_are_read_only(self) -> None:
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: read\n\n")

    def test_uses_no_secrets(self) -> None:
        self.assertNotIn("secrets.", self.text)

    def test_actions_are_pinned_and_limited(self) -> None:
        uses = re.findall(r"uses: (\S+)", self.text)
        self.assertTrue(uses)
        for action in uses:
            name, _, version = action.partition("@")
            self.assertIn(name, ("actions/checkout", "astral-sh/setup-uv"))
            self.assertRegex(version, r"^[0-9a-f]{40}$")

    def test_checkout_never_keeps_credentials(self) -> None:
        checkouts = re.findall(r"uses: actions/checkout@\S+[^\n]*\n\s+with:\n(?:\s+[\w-]+: \S+\n)+", self.text)
        self.assertEqual(len(checkouts), self.text.count("uses: actions/checkout@"))
        for block in checkouts:
            self.assertIn("persist-credentials: false", block)

    def test_paid_model_evaluations_stay_out(self) -> None:
        self.assertNotIn("run_trigger_evals", self.text)

    def test_linux_tests(self) -> None:
        job = self.jobs["unit-linux"]
        self.assertIn("runs-on: ubuntu-latest", job)
        self.assertIn("REQUIRED_TEST_GROUPS: setup-sh,powershell", job)
        self.assertIn('SETUP_PS1_TESTS: "1"', job)
        self.assertIn("SETUP_PS1_SHELL: pwsh", job)
        self.assertIn('RUN_NETWORK_TESTS: "1"', job)
        self.assertIn("unittest discover -s tests -v", job)
        self.assertIn("fetch-depth: 0", job)

    def test_windows_tests_cover_both_powershells(self) -> None:
        job = self.jobs["unit-windows"]
        self.assertIn("runs-on: windows-latest", job)
        self.assertIn("REQUIRED_TEST_GROUPS: powershell", job)
        self.assertIn("SETUP_PS1_SHELL: powershell", job)
        self.assertIn("SETUP_PS1_SHELL: pwsh", job)
        self.assertIn("unittest discover -s tests -v", job)
        self.assertIn("unittest tests.test_setup_scripts_windows -v", job)

    def test_both_test_jobs_write_a_summary_even_after_failure(self) -> None:
        for name in ("unit-linux", "unit-windows"):
            self.assertRegex(self.jobs[name], r"if: always\(\)\n\s+shell: bash\n\s+run: \|?\s*\n?\s*bash tests/ci_summary\.sh")

    def test_linux_e2e_matrix(self) -> None:
        job = self.jobs["e2e-linux"]
        for environment, image in (
            ("ubuntu", "ubuntu:24.04"),
            ("fedora", "fedora:latest"),
            ("arch", "archlinux:latest"),
            ("minimum", "debian:10"),
        ):
            self.assertRegex(job, rf"environment: {environment}\n\s+image: {re.escape(image)}\n")
        self.assertIn("fail-fast: false", job)

    def test_linux_e2e_mounts_only_what_it_needs(self) -> None:
        job = self.jobs["e2e-linux"]
        self.assertEqual(set(re.findall(r'-v "([^"]+)"', job)), {"$RUNNER_TEMP/e2e:/e2e:ro"})

    def test_windows_e2e_builds_the_source_before_git_goes_away(self) -> None:
        job = self.jobs["e2e-windows"]
        self.assertIn("runs-on: windows-latest", job)
        self.assertLess(job.index("git clone --quiet --bare"), job.index("tests\\e2e\\windows.ps1"))
        self.assertEqual(job[job.index("tests\\e2e\\windows.ps1") :].count("git "), 0)

    def test_public_address_only_runs_for_a_public_main(self) -> None:
        condition = "!github.event.repository.private && github.ref == 'refs/heads/main'"
        self.assertIn(condition, self.jobs["e2e-linux"])
        self.assertIn(condition, self.jobs["e2e-windows-public"])
        self.assertIn("raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.sh", self.jobs["e2e-linux"])
        self.assertIn("raw.githubusercontent.com/flysangel/claude-dotfiles/main/tools/setup.ps1", self.jobs["e2e-windows-public"])

    def test_guard_checks_the_full_history_without_the_identity_list(self) -> None:
        job = self.jobs["guard"]
        self.assertIn("repo_guard.py --history --without-identity", job)
        self.assertIn("fetch-depth: 0", job)


if __name__ == "__main__":
    unittest.main()
