"""Static checks for everything under home/, which gets deployed to every machine."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_CLAUDE_MD_LINES = 199
MAX_LISTING_CHARS = 1536

spec = importlib.util.spec_from_file_location("check_allowlist", ROOT / "tools" / "check_allowlist.py")
check_allowlist = importlib.util.module_from_spec(spec)
sys.modules["check_allowlist"] = check_allowlist
spec.loader.exec_module(check_allowlist)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        return {}
    block = text[4 : text.index("\n---", 3)]
    fields: dict[str, str] = {}
    key = None
    for line in block.splitlines():
        match = re.match(r"([A-Za-z_-]+):\s*(.*)", line)
        if match and not line.startswith((" ", "\t")):
            key = match.group(1)
            fields[key] = match.group(2).strip().strip("\"'")
        elif key:
            fields[key] += " " + line.strip()
    return fields


def claude_md_problems(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    problems = []
    if len(text.splitlines()) > MAX_CLAUDE_MD_LINES:
        problems.append(f"{path.name} 必須少於 200 行")
    if not re.search(r"^#{1,6} ", text, re.M):
        problems.append(f"{path.name} 缺少 markdown 標題")
    if not re.search(r"^- ", text, re.M):
        problems.append(f"{path.name} 缺少條列")
    return problems


def skill_problems(skills_dir: Path, skill_tests_dir: Path) -> list[str]:
    problems = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_md.parent.name
        fields = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fields.get("name") != name:
            problems.append(f"{name}: frontmatter 的 name 必須與目錄同名")
        if not fields.get("description"):
            problems.append(f"{name}: 缺少 description")
        listing = fields.get("description", "") + fields.get("when_to_use", "")
        if len(listing) > MAX_LISTING_CHARS:
            problems.append(f"{name}: description 加 when_to_use 超過 {MAX_LISTING_CHARS} 字元")
        for required in ("triggers.json", "scenarios.md"):
            if not (skill_tests_dir / name / required).is_file():
                problems.append(f"{name}: 缺少 tests/skills/{name}/{required}")
    return problems


def personal_data_problems(home_dir: Path) -> list[str]:
    problems = []
    for path in sorted(item for item in home_dir.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(home_dir).as_posix()
        problems.extend(str(found) for found in check_allowlist.scan_text(relative, text, ""))
    return problems


class RepoContentTests(unittest.TestCase):
    def test_claude_md(self) -> None:
        self.assertEqual(claude_md_problems(ROOT / "home" / "CLAUDE.md"), [])

    def test_skills(self) -> None:
        self.assertEqual(skill_problems(ROOT / "home" / "skills", ROOT / "tests" / "skills"), [])

    def test_no_personal_data(self) -> None:
        self.assertEqual(personal_data_problems(ROOT / "home"), [])

    def test_trigger_files_are_valid(self) -> None:
        for path in sorted((ROOT / "tests" / "skills").glob("*/triggers.json")):
            with self.subTest(path=path.parent.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("should_not_trigger", data)
                self.assertIn("should_trigger", data)


if __name__ == "__main__":
    unittest.main()
