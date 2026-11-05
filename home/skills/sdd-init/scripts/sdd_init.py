#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Add the latest stable Spec Kit to a project without touching what is already there."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

REPO_URL = "https://github.com/github/spec-kit.git"
RECORD = ".specify/sdd-init.json"
INIT_OPTIONS = ".specify/init-options.json"
CONSTITUTION = ".specify/memory/constitution.md"
SCAFFOLD_DIRS = {".git", ".claude", ".specify"}
TIMEOUT_SECONDS = 300

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_MISSING = 3


class InitError(Exception):
    """Setup failed; the project has been left as it was."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pick_stable_tag(ls_remote_output: str) -> str | None:
    best: tuple[tuple[int, int, int], str] | None = None
    for line in ls_remote_output.splitlines():
        match = re.search(r"refs/tags/(v?(\d+)\.(\d+)\.(\d+))$", line.strip())
        if match:
            version = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
            if best is None or version > best[0]:
                best = (version, match.group(1))
    return best[1] if best else None


def fetch_latest_tag() -> str | None:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", REPO_URL],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return pick_stable_tag(result.stdout) if result.returncode == 0 else None


def script_type(platform: str = sys.platform) -> str:
    return "ps" if platform == "win32" else "sh"


def run_specify(tag: str, script: str, destination: Path) -> None:
    command = [
        "uv", "tool", "run", "--from", f"git+{REPO_URL}@{tag}",
        "specify", "init", str(destination),
        "--integration", "claude", "--script", script,
        "--ignore-agent-tools", "--non-interactive",
    ]  # fmt: skip
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            env=environment,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InitError(f"無法執行 specify init：{error}") from error
    if result.returncode != 0:
        detail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-5:])
        raise InitError(f"specify init 失敗：\n{detail}")


def has_project_content(project: Path) -> bool:
    return any(item.name not in SCAFFOLD_DIRS for item in project.iterdir())


def is_inside_git_repo(project: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def git_init(project: Path) -> None:
    try:
        result = subprocess.run(["git", "init", "-q"], cwd=project, capture_output=True, text=True, check=False)
    except OSError as error:
        raise InitError(f"無法建立 git repo：{error}") from error
    if result.returncode != 0:
        raise InitError(f"無法建立 git repo：{result.stderr.strip()}")


def remove_empty_parents(path: Path, stop: Path) -> None:
    parent = path.parent
    while parent != stop and stop in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def copy_missing(source: Path, project: Path) -> tuple[list[dict], list[str]]:
    created: list[dict] = []
    skipped: list[str] = []
    try:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source)
            if relative.parts[0] == ".git":
                continue
            destination = project / relative
            if destination.exists():
                skipped.append(relative.as_posix())
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            created.append({"path": relative.as_posix(), "sha256": sha256(destination)})
    except OSError:
        undo_created(project, created)
        raise
    return created, skipped


def undo_created(project: Path, created: list[dict]) -> None:
    for item in created:
        path = project / item["path"]
        path.unlink(missing_ok=True)
        remove_empty_parents(path, project)


def read_version(path: Path) -> str:
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("speckit_version", "未知"))
    except (OSError, ValueError):
        return "未知"


def init(
    project: Path,
    initializer: Callable[[str, str, Path], None] = run_specify,
    fetch_tag: Callable[[], str | None] = fetch_latest_tag,
    which: Callable[[str], str | None] = shutil.which,
    platform: str = sys.platform,
) -> int:
    existing = project / INIT_OPTIONS
    if existing.exists():
        print(f"此專案已導入 Spec Kit {read_version(existing)}，未做任何變更，也不會自動升級。")
        return EXIT_OK

    missing = [tool for tool in ("uv", "git") if not which(tool)]
    if missing:
        print(f"缺少必要工具：{', '.join(missing)}。請先安裝後再執行，專案未做任何變更。", file=sys.stderr)
        return EXIT_MISSING

    tag = fetch_tag()
    if not tag:
        print("無法取得 Spec Kit 的最新版本，請確認網路連線。專案未做任何變更。", file=sys.stderr)
        return EXIT_MISSING

    had_content = has_project_content(project)
    script = script_type(platform)
    created: list[dict] = []
    try:
        with tempfile.TemporaryDirectory(prefix="sdd-init-") as temp:
            scaffold = Path(temp) / "project"
            initializer(tag, script, scaffold)
            version = read_version(scaffold / INIT_OPTIONS)
            created, skipped = copy_missing(scaffold, project)
        record = {"speckit_version": version, "script": script, "created": created, "skipped": skipped}
        record_path = project / RECORD
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        git_created = not is_inside_git_repo(project)
        if git_created:
            git_init(project)
    except (InitError, OSError) as error:
        undo_created(project, created)
        (project / RECORD).unlink(missing_ok=True)
        remove_empty_parents(project / RECORD, project)
        print(f"導入失敗，專案已回到執行前的狀態。\n{error}", file=sys.stderr)
        return EXIT_FAILED

    print(f"已導入 Spec Kit {version}，建立 {len(created)} 個檔案。")
    if skipped:
        print(f"因已存在而略過 {len(skipped)} 個檔案：")
        for path in skipped:
            print(f"  {path}")
    if git_created:
        print("已建立 git repo，尚未 commit。")
    shell = "PowerShell" if script == "ps" else "bash（Windows 上可用 Git Bash）"
    print(f"此專案的 Spec Kit 腳本使用 {shell}；換到另一個作業系統時，需要對應的 shell。")
    if had_content:
        print("下一步：使用 sdd-derive 從現有內容導出 constitution 與 spec。")
    else:
        print("下一步：使用 sdd-grill 討論出 constitution 與 spec。")
    return EXIT_OK


def remove(project: Path, remove_modified: bool = False) -> int:
    record_path = project / RECORD
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"找不到可用的 {RECORD}，無法判斷哪些檔案由導入建立，未做任何變更。", file=sys.stderr)
        return EXIT_FAILED

    removed = 0
    kept: list[str] = []
    for item in record.get("created", []):
        relative = item["path"]
        parts = Path(relative).parts
        if ".." in parts or Path(relative).is_absolute() or parts[0] in {"specs", ".git"}:
            continue
        path = project / relative
        if not path.exists():
            continue
        if sha256(path) == item["sha256"] or remove_modified:
            path.unlink()
            remove_empty_parents(path, project)
            removed += 1
        else:
            kept.append(relative)
    record_path.unlink()
    remove_empty_parents(record_path, project)

    print(f"已移除 {removed} 個檔案。specs/ 與 .git 未變動。")
    if kept:
        print("以下檔案已修改，所以保留；要一併移除時加 --all：")
        for relative in kept:
            print(f"  {relative}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="init", choices=("init", "remove"))
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="目標專案，預設為目前目錄")
    parser.add_argument("--all", action="store_true", help="remove 時連已修改的檔案一併移除")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    project = args.project.resolve()
    if not project.is_dir():
        print(f"找不到專案目錄：{project}", file=sys.stderr)
        return EXIT_FAILED
    return init(project) if args.command == "init" else remove(project, args.all)


if __name__ == "__main__":
    sys.exit(main())
