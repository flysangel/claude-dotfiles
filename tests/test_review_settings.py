"""Tests for tools/review_settings.py. Samples are assembled at runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "review_settings.py"
FAKE_TOKEN = "gh" + "p_" + "a1" * 18
HOME_PATH = "/ho" + "me/someone/bin/tool.sh"
WINDOWS_PATH = "C:" + "\\Us" + "ers\\someone\\tool.ps1"


class ReviewTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.path = self.base / "settings.json"
        self.identity = self.base / "identity.txt"

    def review(self, settings: object) -> subprocess.CompletedProcess[str]:
        self.path.write_text(json.dumps(settings), encoding="utf-8")
        return self.run_script()

    def run_script(self) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "REPO_GUARD_IDENTITY_FILE": str(self.identity)}
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(self.path)],
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def classes(self, settings: dict) -> dict[str, str]:
        result = self.review(settings)
        self.assertEqual(result.returncode, 0, result.stderr)
        found = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("可共用", "含機密", "機器專屬", "待判斷"):
                found[parts[1]] = parts[0]
        return found


class ClassificationTests(ReviewTestCase):
    def test_token_value_is_secret(self) -> None:
        self.assertEqual(self.classes({"thing": FAKE_TOKEN})["thing"], "含機密")

    def test_secret_like_key_is_secret(self) -> None:
        for key in ("apiKey", "API_KEY", "authToken", "password"):
            with self.subTest(key=key):
                self.assertEqual(self.classes({"env": {key: "x"}})["env"], "含機密")

    def test_unrelated_word_is_not_secret(self) -> None:
        self.assertEqual(self.classes({"maxTokens": "100"})["maxTokens"], "待判斷")

    def test_home_paths_are_machine_specific(self) -> None:
        for sample in (HOME_PATH, WINDOWS_PATH, "~/bin/tool.sh", "$HOME/bin/tool.sh"):
            with self.subTest(sample=sample):
                self.assertEqual(self.classes({"statusLine": {"command": sample}})["statusLine"], "機器專屬")

    def test_known_safe_key_is_shared(self) -> None:
        self.assertEqual(self.classes({"theme": "dark"})["theme"], "可共用")

    def test_unknown_key_is_not_assumed_shared(self) -> None:
        self.assertEqual(self.classes({"experimentalThing": True})["experimentalThing"], "待判斷")

    def test_safe_key_with_bad_value_is_not_shared(self) -> None:
        self.assertEqual(self.classes({"theme": FAKE_TOKEN})["theme"], "含機密")

    def test_nested_uses_worst_class_and_lists_path(self) -> None:
        settings = {"hooks": {"Stop": [{"command": HOME_PATH}, {"env": {"apiKey": "x"}}]}}
        result = self.review(settings)
        self.assertIn("含機密  hooks", result.stdout)
        self.assertIn("hooks.Stop[1].env.apiKey", result.stdout)

    def test_identity_list_marks_machine_specific(self) -> None:
        self.identity.write_text("Unusual Person\n", encoding="utf-8")
        result = self.review({"owner": "unusual person"})
        self.assertIn("機器專屬  owner", result.stdout)
        self.assertNotIn("unusual", result.stdout.lower())

    def test_every_top_level_item_is_listed(self) -> None:
        settings = {"theme": "dark", "env": {"apiKey": "x"}, "statusLine": {"command": HOME_PATH}, "other": 1}
        self.assertEqual(set(self.classes(settings)), set(settings))
        self.assertIn("共 4 項", self.review(settings).stdout)


class PrivacyTests(ReviewTestCase):
    def test_values_are_never_printed(self) -> None:
        settings = {
            "theme": "plain-marker-value",
            "env": {"apiKey": FAKE_TOKEN},
            "statusLine": {"command": HOME_PATH},
        }
        result = self.review(settings)
        output = result.stdout + result.stderr
        for value in ("plain-marker-value", FAKE_TOKEN, HOME_PATH):
            self.assertNotIn(value, output)

    def test_sensitive_key_names_are_masked(self) -> None:
        self.identity.write_text("unusual person\n", encoding="utf-8")
        result = self.review({"unusual person": 1, FAKE_TOKEN: 2, "env": {"unusual person": "x"}})
        output = result.stdout + result.stderr
        self.assertNotIn("unusual", output.lower())
        self.assertNotIn(FAKE_TOKEN, output)

    def test_source_file_is_unchanged(self) -> None:
        self.path.write_bytes(b'{"theme":   "dark"}\n')
        before = self.path.read_bytes()
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(sorted(item.name for item in self.base.iterdir()), ["settings.json"])

    def test_missing_file_returns_3(self) -> None:
        self.assertEqual(self.run_script().returncode, 3)

    def test_invalid_json_returns_3_without_content(self) -> None:
        self.path.write_text('{"apiKey": "' + FAKE_TOKEN + '",', encoding="utf-8")
        result = self.run_script()
        self.assertEqual(result.returncode, 3)
        self.assertNotIn(FAKE_TOKEN, result.stdout + result.stderr)

    def test_non_object_returns_3(self) -> None:
        self.assertEqual(self.review(["x"]).returncode, 3)


if __name__ == "__main__":
    unittest.main()
