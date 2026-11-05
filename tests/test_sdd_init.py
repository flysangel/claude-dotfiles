"""Tests for sdd_init.py. Only the test gated by RUN_NETWORK_TESTS reaches the network."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "home" / "skills" / "sdd-init" / "scripts" / "sdd_init.py"
spec = importlib.util.spec_from_file_location("sdd_init", SCRIPT)
sdd_init = importlib.util.module_from_spec(spec)
sys.modules["sdd_init"] = sdd_init
spec.loader.exec_module(sdd_init)

CONSTITUTION = ".specify/memory/constitution.md"


def fake_initializer(tag: str, script: str, destination: Path) -> None:
    files = {
        ".specify/init-options.json": json.dumps({"speckit_version": tag.lstrip("v"), "script": script}),
        CONSTITUTION: "# template\n",
        ".claude/skills/speckit-plan/SKILL.md": "plan\n",
        "README.md": "scaffold readme\n",
    }
    for name, content in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def failing_initializer(tag: str, script: str, destination: Path) -> None:
    raise sdd_init.InitError("boom")


class SddInitTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        config = self.base / "gitconfig"
        config.write_text("", encoding="utf-8")
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_quiet(self, function, *args, **kwargs) -> int:
        self.out = io.StringIO()
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.out):
            return function(*args, **kwargs)

    def init(self, **kwargs) -> int:
        options = {
            "initializer": fake_initializer,
            "fetch_tag": lambda: "v9.9.9",
            "which": lambda tool: f"/fake/{tool}",
            "platform": "linux",
        }
        return self.run_quiet(sdd_init.init, self.project, **{**options, **kwargs})

    def remove(self, **kwargs) -> int:
        return self.run_quiet(sdd_init.remove, self.project, **kwargs)

    def write(self, name: str, content: str) -> None:
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def tree(self) -> dict[str, bytes]:
        return {
            p.relative_to(self.project).as_posix(): p.read_bytes()
            for p in self.project.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(self.project).parts
        }


class InitTests(SddInitTestCase):
    def test_empty_project(self) -> None:
        self.assertEqual(self.init(), 0)
        self.assertTrue((self.project / ".claude/skills/speckit-plan/SKILL.md").exists())
        record = json.loads((self.project / ".specify/sdd-init.json").read_text(encoding="utf-8"))
        self.assertEqual(record["speckit_version"], "9.9.9")
        self.assertEqual(record["script"], "sh")
        self.assertEqual(self.out.getvalue().count("9.9.9"), 1)
        self.assertIn("sdd-grill", self.out.getvalue())
        self.assertIn("shell", self.out.getvalue())

    def test_only_missing_files_are_copied(self) -> None:
        self.write("README.md", "mine\n")
        self.assertEqual(self.init(), 0)
        self.assertEqual((self.project / "README.md").read_text(encoding="utf-8"), "mine\n")
        record = json.loads((self.project / ".specify/sdd-init.json").read_text(encoding="utf-8"))
        self.assertEqual(record["skipped"], ["README.md"])
        self.assertNotIn("README.md", [item["path"] for item in record["created"]])
        self.assertIn("sdd-derive", self.out.getvalue())

    def test_only_scaffold_dirs_count_as_empty(self) -> None:
        self.write(".claude/skills/sdd-init/SKILL.md", "x\n")
        self.init()
        self.assertIn("sdd-grill", self.out.getvalue())

    def test_already_initialized_changes_nothing(self) -> None:
        self.init()
        self.write(CONSTITUTION, "# edited\n")
        before = self.tree()
        calls = []
        result = self.init(initializer=lambda *args: calls.append(args), fetch_tag=lambda: "v10.0.0")
        self.assertEqual(result, 0)
        self.assertEqual(calls, [])
        self.assertEqual(self.tree(), before)
        self.assertIn("9.9.9", self.out.getvalue())

    def test_failure_leaves_project_unchanged(self) -> None:
        self.write("keep.txt", "keep\n")
        before = self.tree()
        self.assertEqual(self.init(initializer=failing_initializer), 1)
        self.assertEqual(self.tree(), before)
        self.assertFalse((self.project / ".git").exists())

    def test_failed_git_init_removes_created_files(self) -> None:
        before = self.tree()

        def fail_git(project: Path) -> None:
            raise sdd_init.InitError("no git")

        with mock.patch.object(sdd_init, "git_init", fail_git):
            self.assertEqual(self.init(), 1)
        self.assertEqual(self.tree(), before)

    def test_missing_tool_returns_3(self) -> None:
        self.assertEqual(self.init(which=lambda tool: None if tool == "uv" else "/x"), 3)
        self.assertIn("uv", self.out.getvalue())
        self.assertEqual(self.tree(), {})

    def test_unavailable_version_returns_3(self) -> None:
        self.assertEqual(self.init(fetch_tag=lambda: None), 3)
        self.assertEqual(self.tree(), {})

    def test_script_follows_platform(self) -> None:
        self.assertEqual(sdd_init.script_type("win32"), "ps")
        self.assertEqual(sdd_init.script_type("linux"), "sh")
        scripts = []

        def capture(tag: str, script: str, destination: Path) -> None:
            scripts.append(script)
            fake_initializer(tag, script, destination)

        self.init(initializer=capture, platform="win32")
        self.assertEqual(scripts, ["ps"])
        self.assertIn("PowerShell", self.out.getvalue())


class StableTagTests(unittest.TestCase):
    def test_excludes_prereleases_and_compares_numerically(self) -> None:
        output = "\n".join(
            f"abc\trefs/tags/{tag}" for tag in ("v1.2.6", "v1.10.0", "v2.0.0-rc.1", "v1.9.9", "nightly")
        )
        self.assertEqual(sdd_init.pick_stable_tag(output), "v1.10.0")

    def test_returns_none_without_stable_tag(self) -> None:
        self.assertIsNone(sdd_init.pick_stable_tag("abc\trefs/tags/v2.0.0-beta\n"))


class GitTests(SddInitTestCase):
    def test_creates_repo_without_commit(self) -> None:
        self.init()
        self.assertTrue((self.project / ".git").is_dir())
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.project, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git repo", self.out.getvalue())

    def test_does_not_init_inside_existing_repo(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.base, check=True)
        self.init()
        self.assertFalse((self.project / ".git").exists())


class RemoveTests(SddInitTestCase):
    def test_removes_unmodified_files_including_template(self) -> None:
        self.write("keep.txt", "keep\n")
        self.init()
        self.assertEqual(self.remove(), 0)
        self.assertEqual(self.tree(), {"keep.txt": b"keep\n"})

    def test_keeps_and_reports_modified_files(self) -> None:
        self.init()
        self.write(CONSTITUTION, "# edited\n")
        self.assertEqual(self.remove(), 0)
        self.assertEqual(self.tree(), {CONSTITUTION: b"# edited\n"})
        self.assertIn(CONSTITUTION, self.out.getvalue())

    def test_all_removes_modified_files(self) -> None:
        self.init()
        self.write(CONSTITUTION, "# edited\n")
        self.assertEqual(self.remove(remove_modified=True), 0)
        self.assertEqual(self.tree(), {})

    def test_never_touches_specs_or_git(self) -> None:
        self.init()
        self.write("specs/001-demo/spec.md", "spec\n")
        self.assertEqual(self.remove(remove_modified=True), 0)
        self.assertEqual(self.tree(), {"specs/001-demo/spec.md": b"spec\n"})
        self.assertTrue((self.project / ".git").is_dir())

    def test_skipped_files_stay(self) -> None:
        self.write("README.md", "mine\n")
        self.init()
        self.remove()
        self.assertEqual(self.tree(), {"README.md": b"mine\n"})

    def test_without_record_changes_nothing(self) -> None:
        self.write(".specify/init-options.json", "{}")
        before = self.tree()
        self.assertEqual(self.remove(), 1)
        self.assertEqual(self.tree(), before)

    def test_record_cannot_escape_project(self) -> None:
        self.init()
        outside = self.base / "outside.txt"
        outside.write_text("safe\n", encoding="utf-8")
        record_path = self.project / ".specify/sdd-init.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["created"].append({"path": "../outside.txt", "sha256": sdd_init.sha256(outside)})
        record_path.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(self.remove(), 0)
        self.assertTrue(outside.exists())


@unittest.skipUnless(os.environ.get("RUN_NETWORK_TESTS") == "1", "set RUN_NETWORK_TESTS=1")
class RealInstallTests(SddInitTestCase):
    def test_latest_release_installs_cleanly(self) -> None:
        self.assertEqual(self.run_quiet(sdd_init.init, self.project), 0, self.out.getvalue())
        self.assertTrue((self.project / ".claude/skills/speckit-specify/SKILL.md").exists())
        self.assertTrue((self.project / ".claude/skills/speckit-constitution/SKILL.md").exists())
        expected = "powershell" if sys.platform == "win32" else "bash"
        self.assertTrue((self.project / ".specify/scripts" / expected).is_dir())
        for path in self.project.rglob("*"):
            if path.is_file() and ".git" not in path.relative_to(self.project).parts:
                self.assertNotIn(b"sdd-init-", path.read_bytes(), path.as_posix())
        self.assertEqual(self.run_quiet(sdd_init.remove, self.project), 0)


if __name__ == "__main__":
    unittest.main()
