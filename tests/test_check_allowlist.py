"""Tests for tools/check_allowlist.py. Violation samples are assembled at runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "check_allowlist.py"
AT = "@"
NOREPLY = f"noreply{AT}example.com"
FAKE_TOKEN = "gh" + "p_" + "a1" * 18
HOME_PATH = "/ho" + "me/someone/project"
WINDOWS_PATH = "C:" + "\\Us" + "ers\\someone\\project"


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.global_config = base / "gitconfig"
        self.global_config.write_text("", encoding="utf-8")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=str(self.global_config), GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q")
        self.git("config", "user.name", "Tester")
        self.git("config", "user.email", NOREPLY)
        self.write(".repo-allowlist", "allowed/**\n.repo-allowlist\ntests/**\n")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.repo, env=self.env, text=True, capture_output=True, check=True
        )

    def write(self, name: str, content: str) -> None:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def stage(self, name: str, content: str) -> None:
        self.write(name, content)
        self.git("add", "-f", name)

    def check(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            env=self.env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )


class AllowlistTests(RepoTestCase):
    def test_file_outside_allowlist_fails(self) -> None:
        self.stage("outside/file.txt", "hello\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside/file.txt", result.stderr)

    def test_file_inside_allowlist_passes(self) -> None:
        self.stage("allowed/deep/file.txt", "hello\n")
        self.assertEqual(self.check().returncode, 0)

    def test_single_star_does_not_cross_directories(self) -> None:
        self.write(".repo-allowlist", "one/*.txt\n")
        self.stage("one/two/file.txt", "hello\n")
        self.assertEqual(self.check().returncode, 1)

    def test_deleted_file_is_not_checked(self) -> None:
        self.stage("outside/file.txt", "hello\n")
        self.git("commit", "-qm", "seed", "--no-verify")
        self.git("rm", "-q", "outside/file.txt")
        self.assertEqual(self.check().returncode, 0)

    def test_missing_allowlist_is_incomplete(self) -> None:
        (self.repo / ".repo-allowlist").unlink()
        self.stage("allowed/file.txt", "hello\n")
        self.assertEqual(self.check().returncode, 3)

    def test_all_checks_tracked_files(self) -> None:
        self.stage("outside/file.txt", "hello\n")
        self.git("commit", "-qm", "seed", "--no-verify")
        self.assertEqual(self.check("--all").returncode, 1)

    def test_binary_file_fails(self) -> None:
        path = self.repo / "allowed/file.bin"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"a\0b")
        self.git("add", "allowed/file.bin")
        self.assertEqual(self.check().returncode, 1)

    def test_staged_content_wins_over_working_tree(self) -> None:
        self.stage("allowed/file.txt", f"{HOME_PATH}\n")
        self.write("allowed/file.txt", "clean\n")
        self.assertEqual(self.check().returncode, 1)


class ContentTests(RepoTestCase):
    def test_home_paths_fail(self) -> None:
        for sample in (HOME_PATH, WINDOWS_PATH):
            with self.subTest(sample=sample):
                self.stage("allowed/file.txt", f"path = {sample}\n")
                self.assertEqual(self.check().returncode, 1)

    def test_relative_home_notation_passes(self) -> None:
        self.stage("allowed/file.txt", "use ~/.claude/skills and tests/home/data\n")
        self.assertEqual(self.check().returncode, 0)

    def test_global_git_email_fails_even_on_reserved_domain(self) -> None:
        address = f"me{AT}personal.example"
        self.global_config.write_text(f"[user]\n\temail = {address}\n", encoding="utf-8")
        self.stage("allowed/file.txt", f"contact {address}\n")
        self.assertEqual(self.check().returncode, 1)

    def test_other_email_fails(self) -> None:
        self.stage("allowed/file.txt", f"contact alice{AT}corp-mail.net\n")
        self.assertEqual(self.check().returncode, 1)

    def test_public_safe_emails_pass(self) -> None:
        samples = (
            f"noreply{AT}anthropic.com",
            f"1+name{AT}users.noreply.github.com",
            f"x{AT}example.com",
            f"x{AT}site.test",
        )
        self.stage("allowed/file.txt", "\n".join(samples) + "\n")
        self.assertEqual(self.check().returncode, 0)

    def test_fake_token_fails_and_is_not_printed(self) -> None:
        self.stage("allowed/file.txt", f"token {FAKE_TOKEN}\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("allowed/file.txt:1", result.stderr)
        self.assertNotIn(FAKE_TOKEN, result.stdout + result.stderr)

    def test_fixture_allows_fake_token_only(self) -> None:
        name = "tests/fixtures/sample-project/config.txt"
        self.stage(name, f"token {FAKE_TOKEN}\n")
        self.assertEqual(self.check().returncode, 0)
        self.stage(name, f"path {HOME_PATH}\n")
        self.assertEqual(self.check().returncode, 1)


class IdentityTests(RepoTestCase):
    def test_noreply_identity_passes(self) -> None:
        self.git("config", "user.email", f"1+name{AT}users.noreply.github.com")
        self.assertEqual(self.check().returncode, 0)

    def test_personal_author_fails(self) -> None:
        self.git("config", "user.email", f"me{AT}personal.example")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("user.email", result.stderr)

    def test_personal_committer_fails(self) -> None:
        self.env["GIT_COMMITTER_EMAIL"] = f"me{AT}personal.example"
        self.assertEqual(self.check().returncode, 1)

    def test_all_does_not_check_identity(self) -> None:
        self.git("config", "user.email", f"me{AT}personal.example")
        self.assertEqual(self.check("--all").returncode, 0)


class HookTests(RepoTestCase):
    @property
    def hook(self) -> Path:
        return self.repo / ".git" / "hooks" / "pre-commit"

    def test_install_is_idempotent_and_has_no_absolute_path(self) -> None:
        self.assertEqual(self.check("--install-hook").returncode, 0)
        first = self.hook.read_bytes()
        self.assertEqual(self.check("--install-hook").returncode, 0)
        self.assertEqual(self.hook.read_bytes(), first)
        self.assertNotIn(str(self.repo).encode(), first)
        self.assertNotIn(b"\r", first)

    def test_install_ignores_shared_hooks_path(self) -> None:
        shared = self.repo.parent / "shared-hooks"
        shared.mkdir()
        self.global_config.write_text(f"[core]\n\thooksPath = {shared.as_posix()}\n", encoding="utf-8")
        result = self.check("--install-hook")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.hook.exists())
        self.assertEqual(list(shared.iterdir()), [])
        self.assertIn("core.hooksPath", result.stdout)

    def test_install_keeps_other_hook(self) -> None:
        self.hook.parent.mkdir(parents=True, exist_ok=True)
        self.hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
        self.assertEqual(self.check("--install-hook").returncode, 1)
        self.assertIn("mine", self.hook.read_text(encoding="utf-8"))

    def test_uninstall_removes_only_own_hook(self) -> None:
        self.check("--install-hook")
        self.assertEqual(self.check("--uninstall-hook").returncode, 0)
        self.assertFalse(self.hook.exists())
        self.hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
        self.assertEqual(self.check("--uninstall-hook").returncode, 1)
        self.assertTrue(self.hook.exists())

    @unittest.skipUnless(shutil.which("uv"), "needs uv")
    def test_hook_blocks_real_commit(self) -> None:
        tools = self.repo / "tools"
        tools.mkdir()
        shutil.copy(SCRIPT, tools / "check_allowlist.py")
        self.check("--install-hook")
        self.stage("outside/file.txt", "hello\n")
        result = subprocess.run(
            ["git", "commit", "-qm", "blocked"],
            cwd=self.repo,
            env=self.env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside/file.txt", result.stderr)


if __name__ == "__main__":
    unittest.main()
