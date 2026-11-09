"""Tests for tools/repo_guard.py. Violation samples are assembled at runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "repo_guard.py"
spec = importlib.util.spec_from_file_location("repo_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
sys.modules["repo_guard"] = guard
spec.loader.exec_module(guard)

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
        self.identity_file = base / "identity.txt"
        self.env.update(
            GIT_CONFIG_GLOBAL=str(self.global_config),
            GIT_CONFIG_NOSYSTEM="1",
            REPO_GUARD_IDENTITY_FILE=str(self.identity_file),
        )
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

    def hook_files(self) -> dict[str, bytes]:
        hooks = self.repo / ".git" / "hooks"
        return {name: (hooks / name).read_bytes() for name in ("pre-commit", "commit-msg", "pre-push")}

    def test_install_is_idempotent_and_has_no_absolute_path(self) -> None:
        self.assertEqual(self.check("--install-hook").returncode, 0)
        first = self.hook_files()
        self.assertEqual(self.check("--install-hook").returncode, 0)
        self.assertEqual(self.hook_files(), first)
        for body in first.values():
            self.assertNotIn(str(self.repo).encode(), body)
            self.assertNotIn(b"\r", body)

    def test_foreign_hook_blocks_whole_install(self) -> None:
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "pre-push").write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
        self.assertEqual(self.check("--install-hook").returncode, 1)
        self.assertFalse((hooks / "pre-commit").exists())
        self.assertFalse((hooks / "commit-msg").exists())

    def test_legacy_hook_is_upgraded_and_removable(self) -> None:
        self.hook.parent.mkdir(parents=True, exist_ok=True)
        legacy = "#!/bin/sh\n# managed-by: tools/check_allowlist.py\nexec x\n"
        self.hook.write_text(legacy, encoding="utf-8")
        self.assertEqual(self.check("--install-hook").returncode, 0)
        self.assertIn(b"repo_guard", self.hook.read_bytes())
        self.hook.write_text(legacy, encoding="utf-8")
        self.assertEqual(self.check("--uninstall-hook").returncode, 0)
        self.assertFalse(self.hook.exists())

    def test_status(self) -> None:
        self.assertEqual(self.check("--status").stdout.splitlines()[0], "not-installed")
        self.check("--install-hook")
        result = self.check("--status")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "enabled")
        self.git("config", "core.hooksPath", "shared-hooks")
        self.assertEqual(self.check("--status").stdout.splitlines()[0], "unverified")

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
        shutil.copy(SCRIPT, tools / "repo_guard.py")
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


class ViolationFormatTests(RepoTestCase):
    def test_kind_fix_and_fingerprint(self) -> None:
        line = f"token {FAKE_TOKEN}"
        self.stage("allowed/file.txt", line + "\n")
        result = self.check()
        self.assertIn("secret", result.stderr)
        self.assertIn(hashlib.sha256(line.encode()).hexdigest(), result.stderr)
        self.assertIn("更換", result.stderr)

    def test_allowlist_has_no_fingerprint(self) -> None:
        self.stage("outside/file.txt", "hello\n")
        result = self.check()
        self.assertIn("allowlist", result.stderr)
        self.assertNotIn("指紋 ", result.stderr)

    def test_identity_kinds_have_no_fingerprint(self) -> None:
        self.git("config", "user.email", f"me{AT}personal.example")
        result = self.check()
        self.assertIn("author", result.stderr)
        self.assertIn("committer", result.stderr)
        self.assertNotIn("指紋 ", result.stderr)


class ExceptionTests(RepoTestCase):
    def add_exception(self, path: str, kind: str, line: str, reason: str = "fake sample") -> None:
        digest = hashlib.sha256(line.encode()).hexdigest()
        item = {"path": path, "kind": kind, "line_sha256": digest, "reason": reason}
        self.write(".repo-guard-exceptions.json", json.dumps({"exceptions": [item]}))

    def test_matching_exception_passes_and_line_change_invalidates(self) -> None:
        line = f"token {FAKE_TOKEN}"
        self.stage("allowed/file.txt", line + "\n")
        self.add_exception("allowed/file.txt", "secret", line)
        self.assertEqual(self.check().returncode, 0)
        self.stage("allowed/file.txt", line + " changed\n")
        self.assertEqual(self.check().returncode, 1)

    def test_does_not_apply_to_other_file_or_kind(self) -> None:
        line = f"token {FAKE_TOKEN}"
        self.stage("allowed/other.txt", line + "\n")
        self.add_exception("allowed/file.txt", "secret", line)
        self.assertEqual(self.check().returncode, 1)
        self.stage("allowed/file.txt", f"{HOME_PATH}\n")
        self.add_exception("allowed/file.txt", "secret", HOME_PATH)
        self.git("rm", "-qf", "--cached", "allowed/other.txt")
        self.assertEqual(self.check().returncode, 1)

    def test_invalid_entries_are_incomplete(self) -> None:
        good = {"path": "a.txt", "kind": "secret", "line_sha256": "a" * 64, "reason": "x"}
        bad_items = [
            {**good, "path": "allowed/*"},
            {**good, "reason": "  "},
            {**good, "line_sha256": "abc"},
            {**good, "kind": "unknown"},
            {**good, "kind": "allowlist"},
            {**good, "kind": "identity"},
            {**good, "kind": "author"},
        ]
        for item in bad_items:
            with self.subTest(item=item):
                self.write(".repo-guard-exceptions.json", json.dumps({"exceptions": [item]}))
                self.assertEqual(self.check().returncode, 3)
        self.write(".repo-guard-exceptions.json", "{not json")
        self.assertEqual(self.check().returncode, 3)

    def test_binary_uses_whole_file_hash(self) -> None:
        content = b"a\0b"
        path = self.repo / "allowed/file.bin"
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        self.git("add", "allowed/file.bin")
        self.assertEqual(self.check().returncode, 1)
        item = {
            "path": "allowed/file.bin",
            "kind": "binary",
            "line_sha256": hashlib.sha256(content).hexdigest(),
            "reason": "known asset",
        }
        self.write(".repo-guard-exceptions.json", json.dumps({"exceptions": [item]}))
        self.assertEqual(self.check().returncode, 0)


class LocalIdentityTests(RepoTestCase):
    SECRET_NAME = "Unusual Person"

    def set_list(self) -> None:
        self.identity_file.write_text(f"# comment\n\n{self.SECRET_NAME}\n", encoding="utf-8")

    def test_content_matches_case_insensitively_and_is_not_printed(self) -> None:
        self.set_list()
        self.stage("allowed/file.txt", "by UNUSUAL PERSON\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("identity", result.stderr)
        self.assertNotIn("unusual", (result.stdout + result.stderr).lower())

    def test_comment_lines_are_not_entries(self) -> None:
        self.set_list()
        self.stage("allowed/file.txt", "a comment here\n")
        self.assertEqual(self.check().returncode, 0)

    def test_author_name_matches(self) -> None:
        self.set_list()
        self.git("config", "user.name", self.SECRET_NAME)
        self.assertEqual(self.check().returncode, 1)

    def test_missing_or_empty_list_only_warns(self) -> None:
        self.stage("allowed/file.txt", "hello\n")
        message = self.repo.parent / "msg"
        message.write_text("clean\n", encoding="utf-8")
        for setup in (lambda: None, lambda: self.identity_file.write_text("# only comment\n", encoding="utf-8")):
            setup()
            for args in ((), ("--all",), ("--commit-msg", str(message))):
                result = self.check(*args)
                self.assertEqual(result.returncode, 0, args)
                self.assertIn("本機識別清單", result.stderr)

    def test_identity_env_is_required_to_override_default(self) -> None:
        self.set_list()
        self.stage("allowed/file.txt", "unusual person\n")
        self.env["REPO_GUARD_IDENTITY_FILE"] = str(self.repo.parent / "absent.txt")
        self.assertEqual(self.check().returncode, 0)


class CommitMessageTests(RepoTestCase):
    def check_message(self, text: str) -> subprocess.CompletedProcess[str]:
        path = self.repo.parent / "msg"
        path.write_text(text, encoding="utf-8")
        return self.check("--commit-msg", str(path))

    def test_violations_fail(self) -> None:
        for sample in (HOME_PATH, f"alice{AT}corp-mail.net", FAKE_TOKEN):
            with self.subTest(sample=sample):
                result = self.check_message(f"subject\n\nsee {sample}\n")
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(FAKE_TOKEN, result.stdout + result.stderr)

    def test_clean_message_and_coauthor_pass(self) -> None:
        text = f"subject\n\nCo-Authored-By: Claude <noreply{AT}anthropic.com>\n"
        self.assertEqual(self.check_message(text).returncode, 0)

    def test_comment_lines_are_skipped(self) -> None:
        self.assertEqual(self.check_message(f"subject\n# {HOME_PATH}\n").returncode, 0)

    def test_unreadable_message_is_incomplete(self) -> None:
        self.assertEqual(self.check("--commit-msg", str(self.repo.parent / "absent")).returncode, 3)


class AllowlistEdgeTests(RepoTestCase):
    def test_force_added_ignored_file_fails(self) -> None:
        self.write(".gitignore", "secret.txt\n")
        self.stage("secret.txt", "hello\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("secret.txt", result.stderr)

    def test_rename_outside_allowlist_fails(self) -> None:
        self.stage("allowed/file.txt", "hello\n")
        self.git("commit", "-qm", "seed")
        (self.repo / "outside").mkdir()
        self.git("mv", "allowed/file.txt", "outside/file.txt")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside/file.txt", result.stderr)

    def test_real_allowlist_excludes_private_files(self) -> None:
        text = (SCRIPT.parents[1] / ".repo-allowlist").read_text(encoding="utf-8").splitlines()
        rules = [line.strip() for line in text if line.strip() and not line.startswith("#")]
        self.assertNotIn("**", rules)
        self.assertNotIn("*", rules)
        patterns = [guard.glob_to_regex(rule) for rule in rules]
        for path in (".credentials.json", "history.jsonl", "settings.json", "projects/x.jsonl"):
            self.assertFalse(guard.is_allowed(path, patterns), path)


class HistoryTests(RepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.identity_file.write_text("unusual person\n", encoding="utf-8")

    def commit(self, name: str, content: str, message: str = "change") -> str:
        self.stage(name, content)
        self.git("commit", "-qm", message, "--no-verify")
        return self.git("rev-parse", "HEAD").stdout.strip()

    def test_without_identity_checks_the_other_rules(self) -> None:
        self.identity_file.unlink(missing_ok=True)
        self.commit("allowed/clean.txt", "clean\n")
        result = self.check("--history", "--without-identity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("沒有比對本機識別清單", result.stdout.splitlines()[0])

    def test_without_identity_still_finds_violations(self) -> None:
        self.identity_file.unlink(missing_ok=True)
        self.commit("allowed/secret.txt", f"token = {FAKE_TOKEN}\n")
        result = self.check("--history", "--without-identity")
        self.assertEqual(result.returncode, 1)
        self.assertIn("secret", result.stderr)
        self.assertNotIn(FAKE_TOKEN, result.stdout + result.stderr)

    def test_without_identity_ignores_an_existing_list(self) -> None:
        self.identity_file.write_text("uniquemarker\n", encoding="utf-8")
        self.commit("allowed/name.txt", "uniquemarker\n")
        self.assertEqual(self.check("--history").returncode, 1)
        self.assertEqual(self.check("--history", "--without-identity").returncode, 0)

    def test_without_identity_needs_history(self) -> None:
        self.assertEqual(self.check("--all", "--without-identity").returncode, 3)

    def test_history_without_a_list_is_still_incomplete(self) -> None:
        self.identity_file.unlink(missing_ok=True)
        self.commit("allowed/clean.txt", "clean\n")
        self.assertEqual(self.check("--history").returncode, 3)

    def test_clean_history_passes(self) -> None:
        self.commit("allowed/file.txt", "hello\n")
        result = self.check("--history")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "通過")

    def test_deleted_secret_is_reported_with_commit(self) -> None:
        bad = self.commit("allowed/file.txt", f"token {FAKE_TOKEN}\n")
        self.commit("allowed/file.txt", "clean\n")
        result = self.check("--history")
        self.assertEqual(result.returncode, 1)
        self.assertIn(bad[:12], result.stderr)
        self.assertIn("allowed/file.txt", result.stderr)
        self.assertNotIn(FAKE_TOKEN, result.stdout + result.stderr)
        self.assertIn("不通過", result.stderr.splitlines()[-1])

    def test_old_identity_fails(self) -> None:
        self.git("config", "user.email", f"me{AT}personal.example")
        self.commit("allowed/file.txt", "hello\n")
        self.git("config", "user.email", NOREPLY)
        self.commit("allowed/other.txt", "hello\n")
        result = self.check("--history")
        self.assertEqual(result.returncode, 1)
        self.assertIn("author", result.stderr)

    def test_old_message_fails(self) -> None:
        self.commit("allowed/file.txt", "hello\n", f"see {HOME_PATH}")
        self.assertEqual(self.check("--history").returncode, 1)

    def test_old_file_outside_allowlist_fails(self) -> None:
        self.commit("outside/file.txt", "hello\n")
        self.git("rm", "-q", "outside/file.txt")
        self.git("commit", "-qm", "remove", "--no-verify")
        result = self.check("--history")
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside/file.txt", result.stderr)

    def test_other_branch_and_tag_are_scanned(self) -> None:
        self.commit("allowed/file.txt", "hello\n")
        self.git("switch", "-qc", "side")
        self.commit("allowed/side.txt", f"{HOME_PATH}\n")
        self.git("switch", "-q", "-")
        self.assertEqual(self.check("--history").returncode, 1)
        self.git("tag", "keep", "side")
        self.git("branch", "-qD", "side")
        self.assertEqual(self.check("--history").returncode, 1)

    def test_exception_applies_to_old_versions(self) -> None:
        line = f"token {FAKE_TOKEN}"
        self.commit("allowed/file.txt", line + "\n")
        self.commit("allowed/file.txt", "clean\n")
        item = {
            "path": "allowed/file.txt",
            "kind": "secret",
            "line_sha256": hashlib.sha256(line.encode()).hexdigest(),
            "reason": "fake",
        }
        self.write(".repo-guard-exceptions.json", json.dumps({"exceptions": [item]}))
        self.assertEqual(self.check("--history").returncode, 0)

    def test_missing_identity_list_is_incomplete(self) -> None:
        self.commit("allowed/file.txt", "hello\n")
        self.identity_file.unlink()
        result = self.check("--history")
        self.assertEqual(result.returncode, 3)
        self.assertIn("不通過", result.stderr)
        self.identity_file.write_text("# none\n", encoding="utf-8")
        self.assertEqual(self.check("--history").returncode, 3)

    def test_identity_in_old_commit_and_author_name(self) -> None:
        self.commit("allowed/file.txt", "unusual person wrote this\n")
        self.commit("allowed/file.txt", "clean\n")
        self.assertEqual(self.check("--history").returncode, 1)

    def test_identity_in_old_author_name(self) -> None:
        self.git("config", "user.name", "Unusual Person")
        self.commit("allowed/file.txt", "hello\n")
        result = self.check("--history")
        self.assertEqual(result.returncode, 1)
        self.assertIn("identity", result.stderr)
        self.assertNotIn("unusual", (result.stdout + result.stderr).lower())

    def test_merge_commit_is_handled(self) -> None:
        self.commit("allowed/a.txt", "a\n")
        base = self.git("branch", "--show-current").stdout.strip()
        self.git("switch", "-qc", "side")
        self.commit("allowed/b.txt", "b\n")
        self.git("switch", "-q", base)
        self.commit("allowed/c.txt", "c\n")
        self.git("merge", "-q", "--no-edit", "--no-verify", "side")
        self.assertEqual(self.check("--history").returncode, 0)


@unittest.skipUnless(shutil.which("uv"), "needs uv")
class RealHookTests(RepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.identity_file.write_text("unusual person\n", encoding="utf-8")
        tools = self.repo / "tools"
        tools.mkdir()
        shutil.copy(SCRIPT, tools / "repo_guard.py")
        self.write(".repo-allowlist", "allowed/**\n.repo-allowlist\ntools/**\n")
        self.git("add", ".repo-allowlist", "tools")
        self.git("commit", "-qm", "seed")
        self.check("--install-hook")
        self.bare = self.repo.parent / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.bare)], env=self.env, check=True)
        self.git("remote", "add", "origin", str(self.bare))

    def run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=self.env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=120,
            check=False,
        )

    def branch(self) -> str:
        return self.git("branch", "--show-current").stdout.strip()

    def test_commit_message_hook_blocks(self) -> None:
        self.stage("allowed/file.txt", "hello\n")
        result = self.run_git("commit", "-qm", f"see {HOME_PATH}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commit 訊息", result.stderr)

    def test_push_blocks_bypassed_commit_then_allows_clean(self) -> None:
        self.assertEqual(self.run_git("push", "-q", "origin", self.branch()).returncode, 0)
        self.stage("allowed/file.txt", f"token {FAKE_TOKEN}\n")
        self.git("commit", "-qm", "bypass", "--no-verify")
        result = self.run_git("push", "-q", "origin", self.branch())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("allowed/file.txt", result.stderr)
        self.assertNotIn(FAKE_TOKEN, result.stderr)


if __name__ == "__main__":
    unittest.main()
