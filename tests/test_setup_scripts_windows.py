"""Tests for tools/setup.ps1 with fake tools.

These run on Windows, where they must not be skipped for acceptance to count. On other systems they
run only under pwsh with SETUP_PS1_TESTS=1, which checks the logic but not winget or PowerShell 5.1.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import fake_tool  # noqa: E402

SETUP_PS1 = ROOT / "tools" / "setup.ps1"
AT = "@"
EMAIL = f"12345+tester{AT}users.noreply.github.com"
IS_WINDOWS = os.name == "nt"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
RUN_ALL = IS_WINDOWS or os.environ.get("SETUP_PS1_TESTS") == "1"
FAKE_SETUP = """\
import json, os, sys
with open(os.environ["MARKER"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
sys.exit(int(os.environ.get("FAKE_SETUP_RC", "0")))
"""


def quoted(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


class PowerShellTestCase(unittest.TestCase):
    TOOLS = ("git", "uv", "claude", "winget", "powershell")

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
        for name in self.TOOLS:
            fake_tool.write_stub(self.bin, name)
        # The script runs through an absolute path, so the fake powershell on PATH is the only one its
        # children can reach. cmd.exe is needed to run the .cmd stubs.
        path = [str(self.bin)]
        if IS_WINDOWS:
            path.append(str(Path(os.environ["SystemRoot"]) / "System32"))
        else:
            for name in ("sh", "env"):
                (self.bin / name).symlink_to(shutil.which(name))
        self.env = {
            **os.environ,
            "PATH": os.pathsep.join(path),
            "USERPROFILE": str(self.home),
            "OS": "Windows_NT",
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
            for suffix in ("", ".cmd"):
                (self.bin / f"{name}{suffix}").unlink(missing_ok=True)

    def powershell(self, command: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            env={**self.env, **extra_env},
            cwd=self.base,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )

    def run_script(self, *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        block = f"[scriptblock]::Create((Get-Content -Raw -LiteralPath {quoted(str(SETUP_PS1))}))"
        return self.powershell(f"& ({block}) {' '.join(args)}", **extra_env)

    def calls(self, tool: str) -> list[dict]:
        if not self.log.exists():
            return []
        entries = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [entry for entry in entries if entry["tool"] == tool]

    def setup_calls(self) -> list[list[str]]:
        if not self.marker.exists():
            return []
        return [json.loads(line) for line in self.marker.read_text(encoding="utf-8").splitlines()]

    def output(self, result: subprocess.CompletedProcess[str]) -> str:
        return result.stdout + result.stderr


@unittest.skipUnless(POWERSHELL and RUN_ALL, "needs Windows, or pwsh with SETUP_PS1_TESTS=1")
class WindowsPreflightTests(PowerShellTestCase):
    def test_old_git_stops_before_installing_anything(self) -> None:
        self.without("uv", "claude")
        result = self.run_script(FAKE_GIT_VERSION="2.19.9")
        self.assertEqual(result.returncode, 1)
        self.assertIn("2.20", self.output(result))
        self.assertEqual(self.calls("powershell"), [])

    def test_git_for_windows_version_string_is_understood(self) -> None:
        result = self.run_script(FAKE_GIT_VERSION="2.47.1.windows.2")
        self.assertEqual(result.returncode, 0, self.output(result))

    def test_old_uv_stops_before_installing_anything(self) -> None:
        self.without("git", "claude")
        result = self.run_script(FAKE_UV_VERSION="0.3.5")
        self.assertEqual(result.returncode, 1)
        self.assertIn("0.4.0", self.output(result))
        self.assertEqual(self.calls("winget"), [])

    def test_wrong_system_stops_before_any_change(self) -> None:
        self.without("git", "uv", "claude")
        result = self.run_script(OS="Other")
        self.assertEqual(result.returncode, 1)
        self.assertIn("system check", self.output(result))
        self.assertEqual(self.calls("winget"), [])
        self.assertFalse((self.home / "claude-dotfiles").exists())


@unittest.skipUnless(POWERSHELL and RUN_ALL, "needs Windows, or pwsh with SETUP_PS1_TESTS=1")
class WindowsToolInstallTests(PowerShellTestCase):
    def test_nothing_is_installed_when_all_tools_exist(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertEqual(self.calls("winget"), [])
        self.assertEqual(self.calls("powershell"), [])
        self.assertEqual(self.setup_calls(), [["install"]])

    def test_only_missing_tools_are_installed_and_reported(self) -> None:
        self.without("uv")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertEqual([entry["args"] for entry in self.calls("_install")], [["uv"]])
        self.assertEqual(self.setup_calls(), [["install", "--installed", "uv"]])

    def test_tools_in_local_bin_can_be_used_in_the_same_run(self) -> None:
        self.without("uv", "claude")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertEqual(self.setup_calls(), [["install", "--installed", "uv,claude"]])

    def test_official_installers_run_in_a_child_process(self) -> None:
        self.without("uv")
        self.run_script()
        command = self.calls("powershell")[0]["args"]
        self.assertEqual(command[:3], ["-NoProfile", "-ExecutionPolicy", "Bypass"])
        self.assertIn("https://astral.sh/uv/install.ps1", " ".join(command))

    def test_git_comes_from_winget(self) -> None:
        self.without("git")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertIn("Git.Git", self.calls("winget")[0]["args"])
        self.assertEqual(self.setup_calls(), [["install", "--installed", "git"]])

    def test_missing_winget_explains_the_manual_way(self) -> None:
        self.without("git", "winget")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("git-scm.com", self.output(result))

    def test_failed_winget_explains_the_manual_way(self) -> None:
        self.without("git")
        result = self.run_script(FAKE_PM_FAIL="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("winget failed", self.output(result))

    def test_download_failure_names_the_step_and_lists_installed_tools(self) -> None:
        self.without("uv", "claude")
        result = self.run_script(FAKE_DOWNLOAD_FAIL="claude.ai")
        self.assertEqual(result.returncode, 1)
        text = " ".join(self.output(result).split())
        self.assertIn("installing Claude Code", text)
        self.assertIn("Tools installed in this run: uv", text)
        self.assertEqual(self.setup_calls(), [])


@unittest.skipUnless(POWERSHELL and RUN_ALL, "needs Windows, or pwsh with SETUP_PS1_TESTS=1")
class WindowsCloneTests(PowerShellTestCase):
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
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertTrue((self.home / "claude-dotfiles" / ".git").is_dir())

    def test_dir_option_overrides_the_location(self) -> None:
        target = self.base / "elsewhere"
        result = self.run_script("-Dir", quoted(str(target)))
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertTrue((target / ".git").is_dir())

    def test_second_run_reuses_the_clone(self) -> None:
        self.assertEqual(self.run_script().returncode, 0)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertEqual(len(self.setup_calls()), 2)

    def test_equivalent_origins_are_accepted(self) -> None:
        env = {"CLAUDE_DOTFILES_REPO": "https://github.com/flysangel/claude-dotfiles.git"}
        for index, origin in enumerate(
            (
                "https://github.com/flysangel/claude-dotfiles",
                "https://github.com/FlysAngel/Claude-Dotfiles.git",
                f"git{AT}github.com:flysangel/claude-dotfiles.git",
                f"ssh://git{AT}github.com/flysangel/claude-dotfiles.git",
            )
        ):
            path = self.existing_repo(f"repo{index}", origin)
            self.marker.unlink(missing_ok=True)
            result = self.run_script("-Dir", quoted(str(path)), **env)
            self.assertEqual(result.returncode, 0, (origin, self.output(result)))
            self.assertEqual(len(self.setup_calls()), 1, origin)

    def test_other_origin_is_refused_without_running_anything(self) -> None:
        path = self.existing_repo("other", "https://github.com/someone/claude-dotfiles.git")
        result = self.run_script("-Dir", quoted(str(path)), CLAUDE_DOTFILES_REPO="https://github.com/flysangel/claude-dotfiles.git")
        self.assertEqual(result.returncode, 1)
        self.assertIn("getting the repo", self.output(result))
        self.assertEqual(self.setup_calls(), [])

    def test_plain_directory_is_refused_without_running_anything(self) -> None:
        path = self.base / "plain"
        (path / "tools").mkdir(parents=True)
        (path / "tools" / "machine_setup.py").write_text(FAKE_SETUP, encoding="utf-8")
        result = self.run_script("-Dir", quoted(str(path)))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.setup_calls(), [])

    def test_clone_failure_explains_what_to_do(self) -> None:
        result = self.run_script(CLAUDE_DOTFILES_REPO=str(self.base / "missing.git"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot clone", self.output(result))


@unittest.skipUnless(POWERSHELL and RUN_ALL, "needs Windows, or pwsh with SETUP_PS1_TESTS=1")
class WindowsSessionTests(PowerShellTestCase):
    def test_options_reach_the_second_stage(self) -> None:
        result = self.run_script("-Dev", "-Email", quoted(EMAIL), "-Force")
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertEqual(self.setup_calls(), [["install", "--dev", "--email", EMAIL, "--force"]])

    def test_runs_through_iex_without_options(self) -> None:
        result = self.powershell(f"Get-Content -Raw -LiteralPath {quoted(str(SETUP_PS1))} | iex")
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertEqual(self.setup_calls(), [["install"]])

    def test_failure_can_be_caught_so_the_window_stays_open(self) -> None:
        self.without("git", "winget")
        command = (
            f"try {{ Get-Content -Raw -LiteralPath {quoted(str(SETUP_PS1))} | iex }} "
            "catch { Write-Output 'CAUGHT' }; Write-Output 'WINDOW-STILL-OPEN'"
        )
        result = self.powershell(command)
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertIn("CAUGHT", result.stdout)
        self.assertIn("WINDOW-STILL-OPEN", result.stdout)

    def test_failure_exits_with_one_through_command(self) -> None:
        self.without("git", "winget")
        self.assertEqual(self.run_script().returncode, 1)

    def test_second_stage_failure_is_reported(self) -> None:
        result = self.run_script(FAKE_SETUP_RC="2")
        self.assertEqual(result.returncode, 1)
        self.assertIn("code 2", self.output(result))


@unittest.skipUnless(POWERSHELL and not IS_WINDOWS, "needs pwsh outside Windows")
class NonWindowsTests(PowerShellTestCase):
    def test_other_systems_stop_before_any_change(self) -> None:
        self.without("git", "uv", "claude")
        env = dict(self.env)
        env.pop("OS")
        self.env = env
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("system check", self.output(result))
        self.assertEqual(self.calls("winget"), [])
        self.assertFalse((self.home / "claude-dotfiles").exists())


if __name__ == "__main__":
    unittest.main()
