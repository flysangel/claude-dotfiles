#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deploy home/ to the Claude config directory, with backups and a full undo.

Contract: specs/002-personal-sdd-toolkit/contracts/dotfiles-cli.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ".dotfiles"
MANIFEST = "manifest.json"
ABSENT = "absent"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFLICT = 2


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(source: Path) -> dict[str, Path]:
    files = {}
    for path in sorted(source.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            files[path.relative_to(source).as_posix()] = path
    return files


def manifest_path(target: Path) -> Path:
    return target / STATE_DIR / MANIFEST


def load_manifest(target: Path) -> dict | None:
    path = manifest_path(target)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def save_manifest(target: Path, status: str, entries: dict[str, dict]) -> None:
    data = {
        "status": status,
        "repo_commit": repo_commit(),
        "entries": [entries[path] for path in sorted(entries)],
    }
    atomic_write(manifest_path(target), (json.dumps(data, indent=2) + "\n").encode())


def repo_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def remove_empty_parents(path: Path, stop: Path) -> None:
    parent = path.parent
    while parent != stop and stop in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def backup_original(target: Path, relative: str) -> dict:
    current = target / relative
    backup = f"backups/original/{relative}"
    atomic_write(target / STATE_DIR / backup, current.read_bytes())
    return {"backup": backup, "sha256": sha256(current)}


def preserve_local_change(target: Path, relative: str, session: str) -> str:
    backup = target / STATE_DIR / "backups" / f"local-{session}" / relative
    atomic_write(backup, (target / relative).read_bytes())
    return backup.relative_to(target).as_posix()


def is_local_change(target: Path, entry: dict) -> bool:
    path = target / entry["path"]
    if not path.exists():
        return False
    current = sha256(path)
    original = entry["original"]
    known = {entry["sha256"]}
    if original != ABSENT:
        known.add(original["sha256"])
    return current not in known


def restore_entry(target: Path, entry: dict, session: str) -> str | None:
    """Put one file back the way it was before the first deploy."""
    relative = entry["path"]
    path = target / relative
    kept = preserve_local_change(target, relative, session) if is_local_change(target, entry) else None
    original = entry["original"]
    if original == ABSENT:
        path.unlink(missing_ok=True)
        remove_empty_parents(path, target)
    else:
        atomic_write(path, (target / STATE_DIR / original["backup"]).read_bytes())
    return kept


def discard_original_backup(target: Path, entry: dict) -> None:
    if entry["original"] != ABSENT:
        backup = target / STATE_DIR / entry["original"]["backup"]
        backup.unlink(missing_ok=True)
        remove_empty_parents(backup, target)


def conflicting_skills(files: dict[str, Path], target: Path, entries: dict[str, dict]) -> list[str]:
    conflicts = set()
    for relative in files:
        parts = relative.split("/")
        if len(parts) >= 2 and parts[0] == "skills":
            directory = target / "skills" / parts[1]
            prefix = f"skills/{parts[1]}/"
            managed = any(path.startswith(prefix) for path in entries)
            if directory.exists() and not managed:
                conflicts.add(parts[1])
    return sorted(conflicts)


def plan_entries(
    files: dict[str, Path], target: Path, entries: dict[str, dict], conflicts: list[str]
) -> dict[str, dict]:
    planned = dict(entries)
    for relative, source in files.items():
        current = target / relative
        previous = entries.get(relative)
        if previous:
            original = previous["original"]
        elif current.exists():
            original = backup_original(target, relative)
        else:
            original = ABSENT
        planned[relative] = {"path": relative, "sha256": sha256(source), "original": original}
    # With --force, files of the replaced skill that the repo doesn't ship must come back on undeploy.
    for skill in conflicts:
        directory = target / "skills" / skill
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            relative = path.relative_to(target).as_posix()
            if relative not in files:
                planned[relative] = {
                    "path": relative,
                    "sha256": None,
                    "original": backup_original(target, relative),
                }
    return planned


def is_up_to_date(manifest: dict | None, files: dict[str, Path], target: Path) -> bool:
    if not manifest or manifest["status"] != "complete":
        return False
    entries = {entry["path"]: entry for entry in manifest["entries"]}
    live = {path: entry for path, entry in entries.items() if entry["sha256"] is not None}
    if set(live) != set(files):
        return False
    for relative, source in files.items():
        path = target / relative
        if not path.exists() or sha256(path) != sha256(source) or live[relative]["sha256"] != sha256(source):
            return False
    return True


def deploy(source: Path, target: Path, force: bool = False) -> int:
    files = source_files(source)
    manifest = load_manifest(target)
    if is_up_to_date(manifest, files, target):
        print("已是最新狀態，沒有變更。")
        return EXIT_OK

    entries = {entry["path"]: entry for entry in manifest["entries"]} if manifest else {}
    conflicts = conflicting_skills(files, target, entries)
    if conflicts and not force:
        print(f"同名的 skill 已存在且不受管：{', '.join(conflicts)}", file=sys.stderr)
        print("未做任何變更。確定要取代時加 --force，原內容會先備份。", file=sys.stderr)
        return EXIT_CONFLICT

    session = time.strftime("%Y%m%d-%H%M%S")
    kept = []
    stale = [
        entry for path, entry in entries.items() if path not in files and entry["sha256"] is not None
    ]
    for relative, path in files.items():
        entry = entries.get(relative)
        current = target / relative
        if entry and is_local_change(target, entry) and sha256(current) != sha256(path):
            kept.append(preserve_local_change(target, relative, session))

    planned = plan_entries(files, target, entries, conflicts if force else [])
    save_manifest(target, "in_progress", planned)

    for relative, entry in planned.items():
        if entry["sha256"] is None:
            path = target / relative
            path.unlink(missing_ok=True)
            remove_empty_parents(path, target)
    for relative, path in files.items():
        atomic_write(target / relative, path.read_bytes())
    for entry in stale:
        restored = restore_entry(target, entry, session)
        if restored:
            kept.append(restored)
        discard_original_backup(target, entry)
        del planned[entry["path"]]
    save_manifest(target, "complete", planned)

    print(f"已部署 {len(files)} 個檔案到 {target}。")
    for relative, entry in sorted(planned.items()):
        if relative in files and entry["original"] != ABSENT and relative not in entries:
            print(f"原有的 {relative} 已備份到 {STATE_DIR}/{entry['original']['backup']}。")
    for path in kept:
        print(f"本機修改已另存到 {path}。")
    print("機器專屬內容請放在 ~/.claude/rules/，部署不會碰這個目錄。")
    return EXIT_OK


def undeploy(target: Path) -> int:
    manifest = load_manifest(target)
    if not manifest:
        print("沒有部署紀錄，未做任何變更。")
        return EXIT_OK
    session = time.strftime("%Y%m%d-%H%M%S")
    kept = []
    for entry in manifest["entries"]:
        restored = restore_entry(target, entry, session)
        if restored:
            kept.append(restored)
    # Backups go last so a failed undeploy can simply be run again.
    for entry in manifest["entries"]:
        discard_original_backup(target, entry)
    manifest_path(target).unlink()
    remove_empty_parents(manifest_path(target), target)
    print("已還原到部署前的狀態。")
    for path in kept:
        print(f"本機修改已另存到 {path}。")
    return EXIT_OK


def status(source: Path, target: Path) -> int:
    manifest = load_manifest(target)
    if not manifest:
        print("not-deployed")
        return EXIT_OK
    if manifest["status"] != "complete":
        print("incomplete")
        print("上次部署沒有完成，請重新部署或解除部署。")
        return EXIT_OK

    entries = {entry["path"]: entry for entry in manifest["entries"]}
    local = []
    for relative, entry in entries.items():
        path = target / relative
        if entry["sha256"] is None:
            if path.exists():
                local.append(relative)
        elif not path.exists() or sha256(path) != entry["sha256"]:
            local.append(relative)
    if local:
        print("local-modified")
        for relative in sorted(local):
            print(f"  {relative}")
        return EXIT_OK

    files = source_files(source)
    live = {path: entry["sha256"] for path, entry in entries.items() if entry["sha256"] is not None}
    wanted = {relative: sha256(path) for relative, path in files.items()}
    ahead = sorted(path for path in set(live) | set(wanted) if live.get(path) != wanted.get(path))
    if ahead:
        print("repo-ahead")
        for relative in ahead:
            print(f"  {relative}")
        return EXIT_OK
    print("clean")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("deploy", "undeploy", "status"))
    parser.add_argument("--target", type=Path, default=Path.home() / ".claude", help="預設為 ~/.claude")
    parser.add_argument("--force", action="store_true", help="備份後取代同名且不受管的 skill")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    source = ROOT / "home"
    try:
        if args.command == "deploy":
            if not source.is_dir():
                print(f"找不到 {source}", file=sys.stderr)
                return EXIT_FAILED
            args.target.mkdir(parents=True, exist_ok=True)
            return deploy(source, args.target, args.force)
        if args.command == "undeploy":
            return undeploy(args.target)
        return status(source, args.target)
    except (OSError, ValueError, KeyError) as error:
        print(f"失敗：{error}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
