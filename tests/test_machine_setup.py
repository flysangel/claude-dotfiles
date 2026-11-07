"""Tests for tools/machine_setup.py. Everything runs in temp directories with an isolated home."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AT = "@"
EMAIL = f"12345+tester{AT}users.noreply.github.com"
OTHER_EMAIL = f"67890+tester{AT}users.noreply.github.com"
PLAIN_EMAIL = f"someone{AT}example.com"
RESERVED_NOREPLY = f"noreply{AT}example.com"
COPIED_TOOLS = ("machine_setup.py", "dotfiles.py", "repo_guard.py")
LOGGED_IN = {"loggedIn": True, "email": PLAIN_EMAIL}


def tree_hashes(directory: Path, skip: tuple[str, ...] = ()) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and not any(part in skip for part in path.parts)
    }


class SetupTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.target = self.home / ".claude"
        self.fake_bin = self.base / "bin"
        self.fake_bin.mkdir()
        self.global_config = self.base / "gitconfig"
        self.global_config.write_text("", encoding="utf-8")
        self.identity = self.base / "identity.txt"
        self.identity.write_text("nothing-to-match-here\n", encoding="utf-8")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(
            HOME=str(self.home),
            USERPROFILE=str(self.home),
            PATH=os.pathsep.join((str(self.fake_bin), os.environ["PATH"])),
            GIT_CONFIG_GLOBAL=str(self.global_config),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Tester",
            GIT_AUTHOR_EMAIL=EMAIL,
            GIT_COMMITTER_NAME="Tester",
            GIT_COMMITTER_EMAIL=EMAIL,
            REPO_GUARD_IDENTITY_FILE=str(self.identity),
        )
        self.set_login(LOGGED_IN)
        self.source = self.base / "source.git"
        self.clone = self.base / "clone"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.source)], env=self.env, check=True)
        seed = self.base / "seed"
        self.git("clone", "-q", str(self.source), str(seed), cwd=self.base)
        (seed / "tools").mkdir()
        for name in COPIED_TOOLS:
            shutil.copy(ROOT / "tools" / name, seed / "tools" / name)
        self.write(seed / ".gitignore", "__pycache__/\n")
        self.write(seed / "home" / "CLAUDE.md", "managed\n")
        self.write(seed / "home" / "skills" / "demo" / "SKILL.md", "demo\n")
        self.git("add", "-A", cwd=seed)
        self.git("commit", "-q", "-m", "seed", cwd=seed)
        self.git("push", "-q", "origin", "HEAD:main", cwd=seed)
        self.seed = seed
        self.git("clone", "-q", str(self.source), str(self.clone), cwd=self.base)

    def set_login(self, payload: object) -> None:
        """Replace the claude command so the real one, and the real account, are never used."""
        script = self.base / "fake_claude.py"
        script.write_text(f"import sys\nprint({json.dumps(json.dumps(payload))})\n", encoding="utf-8")
        if os.name == "nt":
            (self.fake_bin / "claude.cmd").write_text(f'@"{sys.executable}" "{script}"\r\n', encoding="utf-8")
        else:
            stub = self.fake_bin / "claude"
            stub.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}"\n', encoding="utf-8")
            stub.chmod(0o755)

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode())

    def git(self, *args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=cwd or self.clone, env=self.env, text=True, capture_output=True, check=check
        )

    def run_setup(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = args[0]
        target = () if "--target" in args else ("--target", str(self.target))
        return subprocess.run(
            [sys.executable, str(self.clone / "tools" / "machine_setup.py"), command, *args[1:], *target],
            env=self.env,
            cwd=self.base,
            text=True,
            encoding="utf-8",
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )

    def install(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run_setup("install", *args)

    def record_file(self) -> Path:
        return self.home / ".config" / "claude-dotfiles" / "setup.json"

    def record(self) -> dict:
        return json.loads(self.record_file().read_text(encoding="utf-8"))

    def push_to_source(self, path: str, content: str) -> None:
        self.write(self.seed / path, content)
        self.git("add", "-A", cwd=self.seed)
        self.git("commit", "-q", "-m", "update", cwd=self.seed)
        self.git("push", "-q", "origin", "HEAD:main", cwd=self.seed)

    def assert_isolated(self) -> None:
        real_home = Path.home().resolve()
        self.assertNotEqual(self.home, real_home)
        self.assertTrue(self.target.is_relative_to(self.base))


class IsolationTests(SetupTestCase):
    def test_paths_stay_in_the_temp_directory(self) -> None:
        self.assert_isolated()
        result = subprocess.run(
            [sys.executable, "-c", "from pathlib import Path; print(Path.home())"],
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(Path(result.stdout.strip()).resolve(), self.home)


class RecordTests(SetupTestCase):
    def test_record_fields_and_location(self) -> None:
        self.assertEqual(self.install("--installed", "uv").returncode, 0)
        self.assertEqual(
            self.record(),
            {"version": 1, "clone": str(self.clone), "installed_tools": ["uv"], "deployed_before": False, "dev": None},
        )

    def test_installed_tools_accumulate(self) -> None:
        self.install("--installed", "uv")
        self.install("--installed", "git,claude")
        self.install()
        self.assertEqual(sorted(self.record()["installed_tools"]), ["claude", "git", "uv"])

    def test_unknown_tool_is_rejected(self) -> None:
        self.assertEqual(self.install("--installed", "nano").returncode, 1)
        self.assertFalse(self.record_file().exists())

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_record_is_private(self) -> None:
        self.install()
        self.assertEqual(stat.S_IMODE(self.record_file().stat().st_mode), 0o600)

    def test_no_temp_files_left_next_to_the_record(self) -> None:
        self.install()
        self.assertEqual([path.name for path in self.record_file().parent.iterdir()], ["setup.json"])

    def test_malformed_record_stops_both_commands(self) -> None:
        for content in ("{not json", '{"version": 99}', '{"version": 1, "clone": "x", "installed_tools": ["nano"], "dev": null}'):
            self.write(self.record_file(), content)
            before = tree_hashes(self.home)
            for command in ("install", "remove"):
                result = self.run_setup(command)
                self.assertEqual(result.returncode, 1, (content, command))
                self.assertIn("設定紀錄", result.stderr)
            self.assertEqual(tree_hashes(self.home), before)


class UpdateTests(SetupTestCase):
    def test_fast_forward_updates_and_restarts_exactly_once(self) -> None:
        self.install()
        marker = self.base / "restarts.txt"
        tool = (ROOT / "tools" / "machine_setup.py").read_text(encoding="utf-8")
        hook = f'    with open(r"{marker}", "a") as note:\n        note.write("run\\n")\n'
        patched = tool.replace('    args = parser.parse_args(argv)\n', hook + '    args = parser.parse_args(argv)\n')
        self.assertNotEqual(patched, tool)
        self.push_to_source("tools/machine_setup.py", patched)
        self.push_to_source("home/CLAUDE.md", "updated\n")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(marker.read_text(encoding="utf-8"), "run\n")
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "updated\n")

    def test_uncommitted_changes_stop_everything(self) -> None:
        self.write(self.clone / "notes.txt", "mine\n")
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("未提交的改動", result.stderr)
        self.assertEqual((self.clone / "notes.txt").read_text(encoding="utf-8"), "mine\n")
        self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_diverged_clone_stops(self) -> None:
        self.write(self.clone / "local.txt", "local\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "local")
        self.push_to_source("remote.txt", "remote\n")
        head = self.git("rev-parse", "HEAD").stdout
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("分岔", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)
        self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_clone_ahead_deploys_and_warns(self) -> None:
        self.write(self.clone / "local.txt", "local\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "local")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("領先", result.stdout)
        self.assertTrue((self.target / "CLAUDE.md").exists())

    def test_no_upstream_deploys_and_warns(self) -> None:
        self.git("switch", "-q", "-c", "topic")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("upstream", result.stdout)
        self.assertTrue((self.target / "CLAUDE.md").exists())

    def test_fetch_failure_names_the_step(self) -> None:
        self.git("remote", "set-url", "origin", str(self.base / "missing.git"))
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("更新 clone", result.stderr)
        self.assertFalse((self.target / "CLAUDE.md").exists())


class DeployTests(SetupTestCase):
    def test_summary_lists_what_happened(self) -> None:
        result = self.install("--installed", "uv,git")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("設定完成。", result.stdout)
        self.assertIn("已安裝工具：uv、git", result.stdout)
        self.assertIn(f"repo 位置：{self.clone}", result.stdout)
        self.assertIn("部署結果：已部署 2 個檔案", result.stdout)
        self.assertIn("開新的終端機", result.stdout)
        self.assertNotIn("commit 防護", result.stdout)

    def test_second_run_changes_nothing(self) -> None:
        self.install()
        target_before = tree_hashes(self.target)
        clone_before = tree_hashes(self.clone, skip=("__pycache__", ".git"))
        record_before = self.record()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("部署結果：已是最新狀態", result.stdout)
        self.assertIn("已安裝工具：無", result.stdout)
        self.assertNotIn("開新的終端機", result.stdout)
        self.assertEqual(tree_hashes(self.target), target_before)
        self.assertEqual(tree_hashes(self.clone, skip=("__pycache__", ".git")), clone_before)
        self.assertEqual(self.record(), record_before)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

    def test_existing_claude_md_is_backed_up(self) -> None:
        self.write(self.target / "CLAUDE.md", "mine\n")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("已備份", result.stdout)
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "managed\n")

    def test_unmanaged_skill_needs_force(self) -> None:
        self.write(self.target / "skills" / "demo" / "SKILL.md", "mine\n")
        result = self.install()
        self.assertEqual(result.returncode, 2)
        self.assertIn("--force", result.stderr)
        self.assertEqual((self.target / "skills" / "demo" / "SKILL.md").read_text(encoding="utf-8"), "mine\n")
        result = self.install("--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / "skills" / "demo" / "SKILL.md").read_text(encoding="utf-8"), "demo\n")

    def test_login_prompt_follows_auth_status(self) -> None:
        self.assertNotIn("claude 登入", self.install().stdout)
        for payload in ({"loggedIn": False}, ["unexpected"], "not json"):
            self.set_login(payload)
            self.assertIn("claude 登入", self.install().stdout, payload)

    def test_account_details_are_never_printed(self) -> None:
        result = self.install()
        self.assertNotIn(PLAIN_EMAIL, result.stdout + result.stderr)

    def test_record_pointing_at_another_live_clone_stops(self) -> None:
        other = self.base / "other"
        other.mkdir()
        self.write(self.record_file(), json.dumps({"version": 1, "clone": str(other), "installed_tools": [], "dev": None}))
        before = self.record()
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("另一個 clone", result.stderr)
        self.assertEqual(self.record(), before)
        self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_record_pointing_at_a_missing_clone_is_rewritten(self) -> None:
        self.write(
            self.record_file(),
            json.dumps({"version": 1, "clone": str(self.base / "gone"), "installed_tools": ["uv"], "dev": None}),
        )
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.record()["clone"], str(self.clone))
        self.assertEqual(self.record()["installed_tools"], ["uv"])


class DevEmailTests(SetupTestCase):
    def test_email_goes_to_the_clone_only(self) -> None:
        result = self.install("--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("config", "--local", "user.email").stdout.strip(), EMAIL)
        self.assertEqual(self.global_config.read_text(encoding="utf-8"), "")
        self.assertEqual(self.record()["dev"]["email_set"], EMAIL)
        self.assertIsNone(self.record()["dev"]["previous_email"])
        self.assertNotIn(EMAIL, result.stdout + result.stderr)

    def test_other_addresses_are_rejected_before_anything_changes(self) -> None:
        for bad in (PLAIN_EMAIL, RESERVED_NOREPLY, f"x{AT}users.noreply.github.com.example.com"):
            result = self.install("--dev", "--email", bad)
            self.assertEqual(result.returncode, 1, bad)
            self.assertNotIn(bad, result.stdout + result.stderr)
            self.assertFalse((self.target / "CLAUDE.md").exists())
            self.assertFalse(self.record_file().exists())
            self.assertEqual(self.git("config", "--local", "user.email", check=False).stdout, "")

    def test_missing_email_stops_when_the_clone_has_no_noreply_address(self) -> None:
        for current in (None, PLAIN_EMAIL, RESERVED_NOREPLY):
            if current:
                self.git("config", "--local", "user.email", current)
            result = self.install("--dev")
            self.assertEqual(result.returncode, 1, current)
            self.assertIn("--email", result.stderr)
            self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_existing_noreply_address_is_kept(self) -> None:
        self.git("config", "--local", "user.email", EMAIL)
        result = self.install("--dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(self.record()["dev"]["email_set"])
        self.assertEqual(self.record()["dev"]["previous_email"], EMAIL)

    def test_email_without_dev_is_rejected(self) -> None:
        self.assertEqual(self.install("--email", EMAIL).returncode, 1)
        self.assertFalse(self.record_file().exists())

    def test_without_dev_identity_and_hooks_stay_put(self) -> None:
        self.git("config", "--local", "user.email", PLAIN_EMAIL)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.git("config", "--local", "user.email").stdout.strip(), PLAIN_EMAIL)
        self.assertFalse((self.clone / ".git" / "hooks" / "pre-commit").exists())
        self.assertIsNone(self.record()["dev"])

    def test_previous_email_survives_repeated_runs(self) -> None:
        self.git("config", "--local", "user.email", PLAIN_EMAIL)
        self.install("--dev", "--email", EMAIL)
        self.install("--dev", "--email", OTHER_EMAIL)
        self.assertEqual(self.record()["dev"]["previous_email"], PLAIN_EMAIL)
        self.assertEqual(self.record()["dev"]["email_set"], OTHER_EMAIL)


class DevHookTests(SetupTestCase):
    def hook(self, name: str = "pre-commit") -> Path:
        return self.clone / ".git" / "hooks" / name

    def test_new_hook_counts_as_ours(self) -> None:
        result = self.install("--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.hook().exists())
        self.assertTrue(self.record()["dev"]["hook_installed"])
        self.assertIn("commit 防護：enabled", result.stdout)

    def test_already_enabled_hook_is_not_ours(self) -> None:
        subprocess.run(
            [sys.executable, str(self.clone / "tools" / "repo_guard.py"), "--install-hook"],
            cwd=self.clone,
            env=self.env,
            check=True,
            capture_output=True,
        )
        self.assertEqual(self.install("--dev", "--email", EMAIL).returncode, 0)
        self.assertFalse(self.record()["dev"]["hook_installed"])

    def test_hook_ownership_survives_a_second_run(self) -> None:
        self.install("--dev", "--email", EMAIL)
        self.install("--dev", "--email", EMAIL)
        self.assertTrue(self.record()["dev"]["hook_installed"])

    def test_foreign_hook_is_kept_and_reported(self) -> None:
        self.write(self.hook(), "#!/bin/sh\nexit 0\n")
        result = self.install("--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.hook().read_text(encoding="utf-8"), "#!/bin/sh\nexit 0\n")
        self.assertIn("設定未全部完成。", result.stdout)
        self.assertIn("commit 防護：not-installed", result.stdout)
        self.assertIn("佔用", result.stderr)
        self.assertTrue((self.target / "CLAUDE.md").exists())
        self.assertFalse(self.record()["dev"]["hook_installed"])

    def test_hooks_path_is_reported_as_unverified(self) -> None:
        self.git("config", "--local", "core.hooksPath", str(self.base / "shared-hooks"))
        result = self.install("--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("commit 防護：unverified", result.stdout)

    def test_missing_identity_list_is_only_a_reminder(self) -> None:
        self.identity.unlink()
        result = self.install("--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("identity.txt", result.stdout)
        self.assertFalse(self.identity.exists())
        self.assertFalse((self.home / ".config" / "claude-dotfiles" / "identity.txt").exists())

    def test_missing_committer_name_is_a_reminder(self) -> None:
        del self.env["GIT_AUTHOR_NAME"]
        result = self.install("--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("commit 防護：enabled", result.stdout)
        self.assertIn("git config user.name", result.stdout)

    def test_known_committer_name_gets_no_reminder(self) -> None:
        self.assertNotIn("git config user.name", self.install("--dev", "--email", EMAIL).stdout)

    def test_no_identity_reminder_without_dev(self) -> None:
        self.identity.unlink()
        self.assertNotIn("identity.txt", self.install().stdout)


class RemoveTests(SetupTestCase):
    def remove(self) -> subprocess.CompletedProcess[str]:
        return self.run_setup("remove")

    def test_target_returns_to_its_previous_content(self) -> None:
        self.write(self.target / "CLAUDE.md", "mine\n")
        self.write(self.target / "rules" / "machine.md", "local\n")
        before = tree_hashes(self.target)
        self.assertEqual(self.install("--dev", "--email", EMAIL).returncode, 0)
        self.assertNotEqual(tree_hashes(self.target), before)
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tree_hashes(self.target), before)

    def test_without_a_record_nothing_changes(self) -> None:
        self.write(self.target / "CLAUDE.md", "mine\n")
        before = tree_hashes(self.home)
        result = self.remove()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(tree_hashes(self.home), before)

    def test_our_hook_is_removed_and_foreign_hooks_stay(self) -> None:
        self.install("--dev", "--email", EMAIL)
        hooks = self.clone / ".git" / "hooks"
        self.write(hooks / "commit-msg", "#!/bin/sh\nexit 0\n")
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((hooks / "pre-commit").exists())
        self.assertEqual((hooks / "commit-msg").read_text(encoding="utf-8"), "#!/bin/sh\nexit 0\n")

    def test_hook_that_was_already_there_stays(self) -> None:
        subprocess.run(
            [sys.executable, str(self.clone / "tools" / "repo_guard.py"), "--install-hook"],
            cwd=self.clone,
            env=self.env,
            check=True,
            capture_output=True,
        )
        self.install("--dev", "--email", EMAIL)
        self.assertEqual(self.remove().returncode, 0)
        self.assertTrue((self.clone / ".git" / "hooks" / "pre-commit").exists())

    def test_email_returns_to_the_previous_value(self) -> None:
        self.git("config", "--local", "user.email", PLAIN_EMAIL)
        self.install("--dev", "--email", EMAIL)
        self.assertEqual(self.remove().returncode, 0)
        self.assertEqual(self.git("config", "--local", "user.email").stdout.strip(), PLAIN_EMAIL)

    def test_email_is_unset_when_there_was_none(self) -> None:
        self.install("--dev", "--email", EMAIL)
        self.assertEqual(self.remove().returncode, 0)
        self.assertEqual(self.git("config", "--local", "user.email", check=False).stdout, "")

    def test_email_changed_by_the_user_is_kept(self) -> None:
        self.install("--dev", "--email", EMAIL)
        self.git("config", "--local", "user.email", OTHER_EMAIL)
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("config", "--local", "user.email").stdout.strip(), OTHER_EMAIL)
        self.assertIn("保留目前的值", result.stdout)
        self.assertNotIn(OTHER_EMAIL, result.stdout)

    def test_tools_and_clone_are_kept_and_listed(self) -> None:
        self.install("--installed", "uv,git,claude")
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.clone.is_dir())
        self.assertIn(str(self.clone), result.stdout)
        self.assertIn("docs.astral.sh/uv", result.stdout)
        self.assertIn("code.claude.com/docs", result.stdout)
        self.assertIn("winget", result.stdout)

    def test_record_and_empty_directory_are_removed(self) -> None:
        self.install()
        self.assertEqual(self.remove().returncode, 0)
        self.assertFalse(self.record_file().parent.exists())

    def test_directory_with_the_identity_list_stays(self) -> None:
        self.install()
        identity = self.record_file().parent / "identity.txt"
        identity.write_text("private\n", encoding="utf-8")
        self.assertEqual(self.remove().returncode, 0)
        self.assertEqual(identity.read_text(encoding="utf-8"), "private\n")
        self.assertFalse(self.record_file().exists())

    def test_failure_keeps_the_record_so_it_can_run_again(self) -> None:
        self.write(self.target / "CLAUDE.md", "mine\n")
        before = tree_hashes(self.target)
        self.install()
        manifest = self.target / ".dotfiles" / "manifest.json"
        good = manifest.read_bytes()
        manifest.write_text("{broken", encoding="utf-8")
        result = self.remove()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(self.record_file().exists())
        manifest.write_bytes(good)
        self.assertEqual(self.remove().returncode, 0)
        self.assertEqual(tree_hashes(self.target), before)

    def test_deployment_made_before_setup_is_kept(self) -> None:
        subprocess.run(
            [sys.executable, str(self.clone / "tools" / "dotfiles.py"), "deploy", "--target", str(self.target)],
            env=self.env,
            check=True,
            capture_output=True,
        )
        deployed = tree_hashes(self.target)
        self.install()
        self.assertTrue(self.record()["deployed_before"])
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dotfiles.py undeploy", result.stdout)
        self.assertEqual(tree_hashes(self.target), deployed)
        self.assertFalse(self.record_file().exists())

    def test_record_without_the_field_keeps_the_deployment(self) -> None:
        self.install()
        record = self.record()
        del record["deployed_before"]
        self.write(self.record_file(), json.dumps(record))
        deployed = tree_hashes(self.target)
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tree_hashes(self.target), deployed)

    def test_invalid_field_is_a_malformed_record(self) -> None:
        self.install()
        record = self.record()
        record["deployed_before"] = "yes"
        self.write(self.record_file(), json.dumps(record))
        self.assertEqual(self.remove().returncode, 1)

    def test_record_never_lands_in_the_target(self) -> None:
        self.install()
        self.assertFalse((self.target / "setup.json").exists())
        self.assertFalse(any(path.name == "setup.json" for path in self.target.rglob("*")))

    def test_missing_clone_is_reported(self) -> None:
        self.install("--dev", "--email", EMAIL)
        record = self.record()
        record["clone"] = str(self.base / "gone")
        self.write(self.record_file(), json.dumps(record))
        result = self.remove()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("找不到 clone", result.stdout)


if __name__ == "__main__":
    unittest.main()
