"""Tests for tools/setup.sh with fake tools, plus static checks of both entry scripts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import fake_tool  # noqa: E402

SETUP_SH = ROOT / "tools" / "setup.sh"
SETUP_PS1 = ROOT / "tools" / "setup.ps1"
AT = "@"
EMAIL = f"12345+tester{AT}users.noreply.github.com"
ALLOWED_DOWNLOAD_PREFIXES = (
    "https://astral.sh/uv/install.",
    "https://claude.ai/install.",
    "https://github.com/flysangel/claude-dotfiles",
    "https://docs.astral.sh/",
    "https://code.claude.com/",
    "https://git-scm.com/",
)
SYSTEM_COMMANDS = ("bash", "sh", "env", "mktemp", "rm", "cat", "dirname", "sed", "basename")
FAKE_SETUP = """\
import json, os, sys
with open(os.environ["MARKER"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
sys.exit(int(os.environ.get("FAKE_SETUP_RC", "0")))
"""


@unittest.skipUnless(sys.platform.startswith("linux"), "tools/setup.sh targets Linux")
class SetupShTestCase(unittest.TestCase):
    TOOLS = ("uname", "id", "curl", "git", "uv", "claude")

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "calls.jsonl"
        self.marker = self.base / "setup_called.jsonl"
        self.real_git = shutil.which("git")
        self.git_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.git_env.update(
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Tester",
            GIT_AUTHOR_EMAIL=EMAIL,
            GIT_COMMITTER_NAME="Tester",
            GIT_COMMITTER_EMAIL=EMAIL,
        )
        self.source = self.make_source()
        for name in SYSTEM_COMMANDS:
            (self.bin / name).symlink_to(shutil.which(name))
        for name in self.TOOLS:
            fake_tool.write_stub(self.bin, name)
        self.env = {
            "HOME": str(self.home),
            "PATH": str(self.bin),
            "FAKE_HOME": str(self.home),
            "FAKE_BIN": str(self.bin),
            "FAKE_LOG": str(self.log),
            "REAL_GIT": self.real_git,
            "MARKER": str(self.marker),
            "CLAUDE_DOTFILES_REPO": str(self.source),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    def make_source(self) -> Path:
        bare = self.base / "source.git"
        self.real(["init", "-q", "--bare", "-b", "main", str(bare)])
        seed = self.base / "seed"
        self.real(["clone", "-q", str(bare), str(seed)])
        (seed / "tools").mkdir()
        (seed / "tools" / "machine_setup.py").write_text(FAKE_SETUP, encoding="utf-8")
        self.real(["add", "-A"], cwd=seed)
        self.real(["commit", "-q", "-m", "seed"], cwd=seed)
        self.real(["push", "-q", "origin", "HEAD:main"], cwd=seed)
        return bare

    def real(self, args: list[str], cwd: Path | None = None) -> None:
        subprocess.run([self.real_git, *args], cwd=cwd, env=self.git_env, check=True, capture_output=True)

    def without(self, *names: str) -> None:
        for name in names:
            (self.bin / name).unlink(missing_ok=True)

    def add(self, *names: str) -> None:
        for name in names:
            fake_tool.write_stub(self.bin, name)

    def run_script(self, *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [shutil.which("bash"), str(SETUP_SH), *args],
            env={**self.env, **extra_env},
            cwd=self.base,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )

    def calls(self, tool: str | None = None) -> list[dict]:
        if not self.log.exists():
            return []
        entries = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [entry for entry in entries if tool is None or entry["tool"] == tool]

    def installs(self) -> list[dict]:
        return [
            entry
            for entry in self.calls()
            if entry["tool"] in ("_install", "apt-get", "dnf", "pacman", "sudo", "curl", "wget")
        ]

    def setup_calls(self) -> list[list[str]]:
        if not self.marker.exists():
            return []
        return [json.loads(line) for line in self.marker.read_text(encoding="utf-8").splitlines()]


class PreflightTests(SetupShTestCase):
    def test_unsupported_systems_stop_before_any_change(self) -> None:
        self.without("git", "uv", "claude")
        for system in ("Darwin", "MINGW64_NT-10.0-22631"):
            result = self.run_script(FAKE_UNAME=system)
            self.assertEqual(result.returncode, 1, system)
            self.assertIn("system check", result.stderr)
        self.assertEqual(self.installs(), [])
        self.assertFalse((self.home / "claude-dotfiles").exists())
        self.assertEqual(self.setup_calls(), [])

    def test_old_git_stops_before_installing_anything(self) -> None:
        self.without("uv", "claude")
        result = self.run_script(FAKE_GIT_VERSION="2.19.9")
        self.assertEqual(result.returncode, 1)
        self.assertIn("2.20", result.stderr)
        self.assertEqual(self.installs(), [])

    def test_old_uv_stops_before_installing_anything(self) -> None:
        self.without("git", "claude")
        result = self.run_script(FAKE_UV_VERSION="0.3.5")
        self.assertEqual(result.returncode, 1)
        self.assertIn("0.4.0", result.stderr)
        self.assertEqual(self.installs(), [])

    def test_minimum_versions_are_accepted(self) -> None:
        result = self.run_script(FAKE_GIT_VERSION="2.20.0", FAKE_UV_VERSION="0.4.0")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_newer_major_with_small_minor_is_accepted(self) -> None:
        result = self.run_script(FAKE_GIT_VERSION="3.1.0", FAKE_UV_VERSION="1.0.0")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_option_stops(self) -> None:
        result = self.run_script("--nope")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.setup_calls(), [])


class ToolInstallTests(SetupShTestCase):
    def test_nothing_is_installed_when_all_tools_exist(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installs(), [])
        self.assertEqual(self.setup_calls(), [["install"]])

    def test_only_missing_tools_are_installed_and_reported(self) -> None:
        self.without("uv")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([entry["args"] for entry in self.calls("_install")], [["uv"]])
        self.assertEqual(self.setup_calls(), [["install", "--installed", "uv"]])

    def test_tools_installed_only_in_local_bin_can_be_used_in_the_same_run(self) -> None:
        self.without("uv", "claude")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / ".local" / "bin" / "uv").exists())
        self.assertEqual(self.setup_calls(), [["install", "--installed", "uv,claude"]])

    def test_tools_from_an_earlier_run_are_not_installed_again(self) -> None:
        self.without("uv")
        fake_tool.write_stub(self.home / ".local" / "bin", "uv")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("_install"), [])

    def test_package_managers_are_tried_in_order(self) -> None:
        for managers, used in ((("apt-get", "dnf", "pacman"), "apt-get"), (("dnf", "pacman"), "dnf"), (("pacman",), "pacman")):
            self.without("git", "apt-get", "dnf", "pacman")
            self.add("sudo", *managers)
            self.log.unlink(missing_ok=True)
            self.marker.unlink(missing_ok=True)
            shutil.rmtree(self.home / "claude-dotfiles", ignore_errors=True)
            result = self.run_script()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(self.calls(used), used)
            self.assertTrue(all(entry["sudo"] for entry in self.calls(used)))
            for other in ("apt-get", "dnf", "pacman"):
                if other != used:
                    self.assertEqual(self.calls(other), [], other)
            self.assertEqual(self.setup_calls(), [["install", "--installed", "git"]])

    def test_root_does_not_use_sudo(self) -> None:
        self.without("git")
        self.add("apt-get", "sudo")
        result = self.run_script(FAKE_UID="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("sudo"), [])
        self.assertTrue(self.calls("apt-get"))

    def test_missing_sudo_explains_the_manual_way(self) -> None:
        self.without("git")
        self.add("apt-get")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("installing git", result.stderr)
        self.assertIn("git-scm.com", result.stderr)
        self.assertEqual(self.calls("apt-get"), [])

    def test_refused_sudo_explains_the_manual_way(self) -> None:
        self.without("git")
        self.add("apt-get", "sudo")
        result = self.run_script(FAKE_SUDO_FAIL="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("git-scm.com", result.stderr)

    def test_failed_package_manager_explains_the_manual_way(self) -> None:
        self.without("git")
        self.add("dnf", "sudo")
        result = self.run_script(FAKE_PM_FAIL="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("dnf failed", result.stderr)

    def test_no_package_manager_explains_the_manual_way(self) -> None:
        self.without("git")
        self.add("sudo")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no supported package manager", result.stderr)

    def test_official_installers_never_run_under_sudo(self) -> None:
        self.without("git", "uv", "claude")
        self.add("apt-get", "sudo")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(entry["args"][0] for entry in self.calls("_install")), ["claude", "uv"])
        self.assertFalse(any(entry["sudo"] for entry in self.calls("_install")))
        self.assertFalse(any(entry["sudo"] for entry in self.calls("curl")))

    def test_wget_works_when_curl_is_missing(self) -> None:
        self.without("curl", "uv")
        self.add("wget")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.calls("wget"))

    def test_download_failure_names_the_step_and_lists_installed_tools(self) -> None:
        self.without("uv", "claude")
        result = self.run_script(FAKE_DOWNLOAD_FAIL="claude.ai")
        self.assertEqual(result.returncode, 1)
        self.assertIn("installing Claude Code", result.stderr)
        self.assertIn("tools installed in this run: uv", result.stderr)
        self.assertEqual(self.setup_calls(), [])

    def test_exit_code_of_the_second_stage_is_returned(self) -> None:
        self.assertEqual(self.run_script(FAKE_SETUP_RC="2").returncode, 2)


class CloneTests(SetupShTestCase):
    def existing_repo(self, name: str, origin: str | None) -> Path:
        path = self.base / name
        path.mkdir()
        self.real(["init", "-q"], cwd=path)
        if origin:
            self.real(["remote", "add", "origin", origin], cwd=path)
        (path / "tools").mkdir()
        (path / "tools" / "machine_setup.py").write_text(FAKE_SETUP, encoding="utf-8")
        return path

    def test_default_location_is_in_the_home_directory(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / "claude-dotfiles" / ".git").is_dir())

    def test_dir_option_overrides_the_location(self) -> None:
        target = self.base / "elsewhere"
        result = self.run_script("--dir", str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((target / ".git").is_dir())
        self.assertFalse((self.home / "claude-dotfiles").exists())

    def test_relative_dir_is_resolved(self) -> None:
        result = self.run_script("--dir", "relative-clone")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.base / "relative-clone" / ".git").is_dir())

    def test_second_run_reuses_the_clone(self) -> None:
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(len(self.setup_calls()), 2)

    def test_equivalent_origins_are_accepted(self) -> None:
        env = {"CLAUDE_DOTFILES_REPO": "https://github.com/flysangel/claude-dotfiles.git"}
        for index, origin in enumerate(
            (
                "https://github.com/flysangel/claude-dotfiles.git",
                "https://github.com/flysangel/claude-dotfiles",
                "https://github.com/flysangel/claude-dotfiles/",
                "https://github.com/FlysAngel/Claude-Dotfiles.git",
                f"git{AT}github.com:flysangel/claude-dotfiles.git",
                f"git{AT}github.com:flysangel/claude-dotfiles",
                f"ssh://git{AT}github.com/flysangel/claude-dotfiles.git",
            )
        ):
            path = self.existing_repo(f"repo{index}", origin)
            self.marker.unlink(missing_ok=True)
            result = self.run_script("--dir", str(path), **env)
            self.assertEqual(result.returncode, 0, (origin, result.stderr))
            self.assertEqual(len(self.setup_calls()), 1, origin)

    def test_default_source_is_this_repo(self) -> None:
        env = dict(self.env)
        del env["CLAUDE_DOTFILES_REPO"]
        path = self.existing_repo("default", "https://github.com/flysangel/claude-dotfiles.git")
        self.env = env
        result = self.run_script("--dir", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_refused(self, path: Path, **env: str) -> None:
        before = sorted(item.name for item in path.iterdir())
        result = self.run_script("--dir", str(path), **env)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("getting the repo", result.stderr)
        self.assertEqual(sorted(item.name for item in path.iterdir()), before)
        self.assertEqual(self.setup_calls(), [], "code inside the directory must not run")

    def test_other_origins_are_refused_without_running_anything(self) -> None:
        for index, origin in enumerate(
            (
                "https://github.com/someone/claude-dotfiles.git",
                "https://github.com/flysangel/claude-dotfiles-evil.git",
                "https://gitlab.com/flysangel/claude-dotfiles.git",
            )
        ):
            path = self.existing_repo(f"other{index}", origin)
            self.assert_refused(path, CLAUDE_DOTFILES_REPO="https://github.com/flysangel/claude-dotfiles.git")

    def test_repo_without_origin_is_refused(self) -> None:
        self.assert_refused(self.existing_repo("noorigin", None))

    def test_plain_directory_is_refused(self) -> None:
        path = self.base / "plain"
        (path / "tools").mkdir(parents=True)
        (path / "tools" / "machine_setup.py").write_text(FAKE_SETUP, encoding="utf-8")
        self.assert_refused(path)

    def test_subdirectory_of_the_right_repo_is_refused(self) -> None:
        repo = self.existing_repo("parent", str(self.source))
        sub = repo / "nested"
        (sub / "tools").mkdir(parents=True)
        (sub / "tools" / "machine_setup.py").write_text(FAKE_SETUP, encoding="utf-8")
        self.assert_refused(sub)

    def test_clone_failure_explains_what_to_do(self) -> None:
        result = self.run_script(CLAUDE_DOTFILES_REPO=str(self.base / "missing.git"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot clone", result.stderr)
        self.assertIn("--dir", result.stderr)


class PipeTests(SetupShTestCase):
    def pipe(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [shutil.which("bash"), "-s", "--", *args],
            input=script,
            env=self.env,
            cwd=self.base,
            text=True,
            capture_output=True,
        )

    def script(self) -> str:
        return SETUP_SH.read_text(encoding="utf-8")

    def test_options_arrive_through_the_pipe(self) -> None:
        result = self.pipe(self.script(), "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.setup_calls(), [["install", "--force"]])

    def test_dev_options_arrive_through_the_pipe(self) -> None:
        result = self.pipe(self.script(), "--dev", "--email", EMAIL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.setup_calls(), [["install", "--dev", "--email", EMAIL]])

    def test_email_without_a_value_stops(self) -> None:
        result = self.pipe(self.script(), "--email")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--email", result.stderr)
        self.assertEqual(self.setup_calls(), [])

    def test_exit_code_passes_through_the_pipe(self) -> None:
        self.env["FAKE_SETUP_RC"] = "2"
        self.assertEqual(self.pipe(self.script()).returncode, 2)

    def test_truncated_script_runs_no_step(self) -> None:
        self.without("uv")
        text = self.script()
        for fraction in (4, 2):
            self.pipe(text[: len(text) // fraction])
        self.pipe(text[: text.rindex('main "$@"')])
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.setup_calls(), [])

    def test_children_cannot_read_the_piped_script(self) -> None:
        result = self.pipe(self.script() + "\n# trailing line for anything that reads stdin\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("uv")[-1]["stdin"], "")


class StaticTests(unittest.TestCase):
    """These run everywhere, including machines that cannot execute the script."""

    def scripts(self) -> list[Path]:
        return [SETUP_SH, SETUP_PS1]

    def test_entry_scripts_are_ascii(self) -> None:
        for path in self.scripts():
            path.read_bytes().decode("ascii")

    def test_entry_scripts_only_name_expected_urls(self) -> None:
        for path in self.scripts():
            text = path.read_text(encoding="ascii")
            self.assertIsNone(re.search(r"http://\w", text), path.name)
            for url in re.findall(r"https://\w[^\s\"')]+", text):
                self.assertTrue(url.startswith(ALLOWED_DOWNLOAD_PREFIXES), (path.name, url))

    def test_shell_script_ends_with_the_only_call_to_main(self) -> None:
        lines = [line for line in SETUP_SH.read_text(encoding="ascii").splitlines() if line.strip()]
        self.assertEqual(lines[-1], 'main "$@"')
        self.assertEqual(lines.count('main "$@"'), 1)

    def test_powershell_script_never_exits_the_session(self) -> None:
        code = [line.split("#", 1)[0] for line in SETUP_PS1.read_text(encoding="ascii").splitlines()]
        self.assertIsNone(re.search(r"\bexit\b", "\n".join(code), re.IGNORECASE))

    def test_powershell_runs_official_installers_in_a_child_process(self) -> None:
        text = SETUP_PS1.read_text(encoding="ascii")
        self.assertIn("powershell -NoProfile -ExecutionPolicy Bypass -Command", text)
        self.assertIn("https://astral.sh/uv/install.ps1", text)
        self.assertIn("https://claude.ai/install.ps1", text)
        self.assertIn("winget install --id Git.Git", text)
        iex_lines = [line for line in text.splitlines() if re.search(r"\|\s*iex", line)]
        self.assertEqual(len(iex_lines), 1)
        self.assertIn("$command = ", iex_lines[0])

    def test_powershell_starts_with_parameters(self) -> None:
        code = [
            line
            for line in SETUP_PS1.read_text(encoding="ascii").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(code[0].startswith("param("), code[0])


if __name__ == "__main__":
    unittest.main()
