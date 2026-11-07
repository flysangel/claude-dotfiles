"""Tests for tools/dotfiles.py. Every test runs in temp directories, never the real config."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dotfiles", ROOT / "tools" / "dotfiles.py")
dotfiles = importlib.util.module_from_spec(spec)
sys.modules["dotfiles"] = dotfiles
spec.loader.exec_module(dotfiles)


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class DotfilesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.source = base / "home"
        self.target = base / "target"
        self.target.mkdir()
        self.write(self.source, "CLAUDE.md", "# new\n")
        self.write(self.source, "skills/demo/SKILL.md", "demo\n")
        self.write(self.source, "skills/demo/scripts/run.py", "print(1)\n")

    @staticmethod
    def write(root: Path, name: str, content: str) -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def run_quiet(self, function, *args, **kwargs):
        self.out = io.StringIO()
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.out):
            return function(*args, **kwargs)

    def deploy(self, force: bool = False) -> int:
        return self.run_quiet(dotfiles.deploy, self.source, self.target, force=force)

    def undeploy(self) -> int:
        return self.run_quiet(dotfiles.undeploy, self.target)

    def status(self) -> str:
        self.assertEqual(self.run_quiet(dotfiles.status, self.source, self.target), 0)
        return self.out.getvalue().splitlines()[0]

    def manifest(self) -> dict:
        return json.loads((self.target / ".dotfiles" / "manifest.json").read_text(encoding="utf-8"))

    def set_manifest_status(self, status: str) -> None:
        data = self.manifest()
        data["status"] = status
        path = self.target / ".dotfiles" / "manifest.json"
        path.write_text(json.dumps(data), encoding="utf-8")

    def backups(self) -> list[Path]:
        return [p for p in (self.target / ".dotfiles").rglob("*") if p.is_file() and p.name != "manifest.json"]


class DeployTests(DotfilesTestCase):
    def test_first_deploy_copies_files(self) -> None:
        self.assertEqual(self.deploy(), 0)
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# new\n")
        self.assertTrue((self.target / "skills/demo/scripts/run.py").exists())
        self.assertEqual(self.manifest()["status"], "complete")
        self.assertIn("rules", self.out.getvalue())

    def test_manifest_uses_forward_slashes_and_records_absent(self) -> None:
        self.deploy()
        entries = {e["path"]: e for e in self.manifest()["entries"]}
        self.assertIn("skills/demo/SKILL.md", entries)
        self.assertEqual(entries["CLAUDE.md"]["original"], "absent")

    def test_existing_claude_md_is_backed_up(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        self.assertEqual(self.deploy(), 0)
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# new\n")
        original = {e["path"]: e for e in self.manifest()["entries"]}["CLAUDE.md"]["original"]
        backup = self.target / ".dotfiles" / original["backup"]
        self.assertEqual(backup.read_text(encoding="utf-8"), "# mine\n")
        self.assertNotIn("# mine", self.out.getvalue())

    def test_repeat_deploy_changes_nothing(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        self.deploy()
        before = snapshot(self.target)
        self.assertEqual(self.deploy(), 0)
        self.assertEqual(snapshot(self.target), before)

    def test_redeploy_keeps_first_original(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        self.deploy()
        self.write(self.source, "CLAUDE.md", "# newer\n")
        self.deploy()
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# newer\n")
        self.assertEqual(self.undeploy(), 0)
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# mine\n")

    def test_unmanaged_content_is_untouched(self) -> None:
        self.write(self.target, "skills/other/SKILL.md", "other\n")
        self.write(self.target, "rules/machine.md", "machine\n")
        self.deploy()
        self.undeploy()
        self.assertEqual((self.target / "skills/other/SKILL.md").read_text(encoding="utf-8"), "other\n")
        self.assertEqual((self.target / "rules/machine.md").read_text(encoding="utf-8"), "machine\n")

    def test_same_name_unmanaged_skill_conflicts(self) -> None:
        self.write(self.target, "skills/demo/SKILL.md", "theirs\n")
        before = snapshot(self.target)
        self.assertEqual(self.deploy(), 2)
        self.assertEqual(snapshot(self.target), before)

    def test_force_replaces_conflict_and_undeploy_restores_it(self) -> None:
        self.write(self.target, "skills/demo/SKILL.md", "theirs\n")
        self.write(self.target, "skills/demo/extra.md", "extra\n")
        before = snapshot(self.target)
        self.assertEqual(self.deploy(force=True), 0)
        self.assertEqual((self.target / "skills/demo/SKILL.md").read_text(encoding="utf-8"), "demo\n")
        self.assertFalse((self.target / "skills/demo/extra.md").exists())
        self.assertEqual(self.status(), "clean")
        self.undeploy()
        self.assertEqual(snapshot(self.target), before)

    def test_local_change_is_backed_up_before_overwrite(self) -> None:
        self.deploy()
        self.write(self.target, "CLAUDE.md", "# local edit\n")
        self.assertEqual(self.deploy(), 0)
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# new\n")
        contents = [p.read_text(encoding="utf-8") for p in self.backups()]
        self.assertIn("# local edit\n", contents)

    def test_file_removed_from_repo_is_removed_from_target(self) -> None:
        self.deploy()
        (self.source / "skills/demo/scripts/run.py").unlink()
        self.assertEqual(self.deploy(), 0)
        self.assertFalse((self.target / "skills/demo/scripts/run.py").exists())
        self.assertFalse((self.target / "skills/demo/scripts").exists())
        self.assertNotIn("skills/demo/scripts/run.py", [e["path"] for e in self.manifest()["entries"]])

    def test_python_caches_are_not_deployed(self) -> None:
        self.write(self.source, "skills/demo/scripts/__pycache__/run.pyc", "x")
        self.deploy()
        self.assertFalse((self.target / "skills/demo/scripts/__pycache__").exists())


class InterruptedTests(DotfilesTestCase):
    def interrupted(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        self.deploy()
        self.set_manifest_status("in_progress")
        (self.target / "skills/demo/SKILL.md").unlink()

    def test_redeploy_completes(self) -> None:
        self.interrupted()
        self.assertEqual(self.status(), "incomplete")
        self.assertEqual(self.deploy(), 0)
        self.assertEqual(self.status(), "clean")
        self.undeploy()
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# mine\n")

    def test_undeploy_restores(self) -> None:
        self.interrupted()
        self.assertEqual(self.undeploy(), 0)
        self.assertEqual(snapshot(self.target), {"CLAUDE.md": b"# mine\n"})


class UndeployTests(DotfilesTestCase):
    def test_restores_bytes_exactly(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        (self.target / "skills").mkdir()
        self.write(self.target, "skills/other/SKILL.md", "other\n")
        (self.target / "binary").write_bytes(b"\r\n\0\xff")
        before = snapshot(self.target)
        self.deploy()
        self.assertEqual(self.undeploy(), 0)
        self.assertEqual(snapshot(self.target), before)
        self.assertFalse((self.target / ".dotfiles").exists())

    def test_removes_created_directories(self) -> None:
        self.deploy()
        self.undeploy()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_local_change_is_kept_in_backup(self) -> None:
        self.deploy()
        self.write(self.target, "CLAUDE.md", "# local edit\n")
        self.assertEqual(self.undeploy(), 0)
        self.assertFalse((self.target / "CLAUDE.md").exists())
        contents = [p.read_text(encoding="utf-8") for p in self.backups()]
        self.assertEqual(contents, ["# local edit\n"])
        self.assertIn(".dotfiles", self.out.getvalue())

    def test_failed_undeploy_can_run_again(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        self.write(self.target, "skills/other/SKILL.md", "other\n")
        self.write(self.source, "skills/other2/SKILL.md", "x\n")
        self.deploy()
        real_restore = dotfiles.restore_entry
        calls = []

        def fail_on_second(*args):
            calls.append(args)
            if len(calls) == 2:
                raise OSError("disk error")
            return real_restore(*args)

        with mock.patch.object(dotfiles, "restore_entry", fail_on_second):
            with self.assertRaises(OSError):
                self.undeploy()
        self.assertEqual(self.undeploy(), 0)
        self.assertEqual((self.target / "CLAUDE.md").read_text(encoding="utf-8"), "# mine\n")
        self.assertFalse((self.target / ".dotfiles").exists())

    def test_without_manifest_changes_nothing(self) -> None:
        self.write(self.target, "CLAUDE.md", "# mine\n")
        before = snapshot(self.target)
        self.assertEqual(self.undeploy(), 0)
        self.assertEqual(snapshot(self.target), before)


class StatusTests(DotfilesTestCase):
    def test_not_deployed(self) -> None:
        self.assertEqual(self.status(), "not-deployed")

    def test_clean(self) -> None:
        self.deploy()
        self.assertEqual(self.status(), "clean")

    def test_local_modified(self) -> None:
        self.deploy()
        self.write(self.target, "CLAUDE.md", "# local\n")
        self.assertEqual(self.status(), "local-modified")
        self.assertIn("CLAUDE.md", self.out.getvalue())

    def test_missing_target_file_is_local_modified(self) -> None:
        self.deploy()
        (self.target / "CLAUDE.md").unlink()
        self.assertEqual(self.status(), "local-modified")

    def test_repo_ahead_when_changed_added_or_removed(self) -> None:
        self.deploy()
        self.write(self.source, "CLAUDE.md", "# newer\n")
        self.assertEqual(self.status(), "repo-ahead")
        self.write(self.source, "CLAUDE.md", "# new\n")
        self.write(self.source, "skills/added/SKILL.md", "added\n")
        self.assertEqual(self.status(), "repo-ahead")

    def test_priority_incomplete_then_local_then_repo(self) -> None:
        self.deploy()
        self.write(self.target, "CLAUDE.md", "# local\n")
        self.write(self.source, "CLAUDE.md", "# newer\n")
        self.assertEqual(self.status(), "local-modified")
        self.set_manifest_status("in_progress")
        self.assertEqual(self.status(), "incomplete")

    def test_status_does_not_write(self) -> None:
        self.deploy()
        before = snapshot(self.target)
        self.status()
        self.assertEqual(snapshot(self.target), before)


if __name__ == "__main__":
    unittest.main()
