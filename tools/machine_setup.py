#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Second stage of the one-line setup: update the clone, dev setup, deploy, and undo.

Contract: specs/003-license-oneline-setup/contracts/setup-cli.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_VERSION = 1
KNOWN_TOOLS = ("uv", "git", "claude")
REEXEC_ENV = "CLAUDE_DOTFILES_SETUP_UPDATED"
NOREPLY_RE = re.compile(r"[\w.+-]+@users\.noreply\.github\.com", re.IGNORECASE)
IDENTITY_MISSING = "本機識別清單：不存在或沒有內容"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFLICT = 2

TOOL_REMOVAL = {
    "uv": "uv：https://docs.astral.sh/uv/getting-started/installation/#uninstallation",
    "git": "git：用安裝時的套件管理工具移除（apt-get、dnf、pacman 或 winget）",
    "claude": "Claude Code：https://code.claude.com/docs/en/setup#uninstall-claude-code",
}


class SetupError(Exception):
    def __init__(self, message: str, code: int = EXIT_FAILED) -> None:
        super().__init__(message)
        self.code = code


def record_path() -> Path:
    return Path.home() / ".config" / "claude-dotfiles" / "setup.json"


def validate_record(data: object) -> bool:
    if not isinstance(data, dict) or data.get("version") != RECORD_VERSION:
        return False
    tools = data.get("installed_tools")
    if not isinstance(data.get("clone"), str) or not isinstance(tools, list):
        return False
    if any(tool not in KNOWN_TOOLS for tool in tools):
        return False
    dev = data.get("dev", "missing")
    if dev is None:
        return True
    return (
        isinstance(dev, dict)
        and isinstance(dev.get("hook_installed"), bool)
        and all(dev.get(key, 0) is None or isinstance(dev.get(key), str) for key in ("email_set", "previous_email"))
    )


def load_record() -> dict | None:
    path = record_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except ValueError as error:
        raise SetupError(f"設定紀錄無法解析：{path}。請確認內容或移走它，再重新執行。") from error
    if not validate_record(data):
        raise SetupError(f"設定紀錄的格式不符：{path}。請確認內容或移走它，再重新執行。")
    return data


def save_record(record: dict) -> None:
    path = record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # mkstemp creates the file with mode 600, and the replace keeps it.
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", *args], cwd=cwd, env=env, text=True, capture_output=True)


def run_tool(script: str, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(cwd / "tools" / script), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )


def is_github_noreply(email: str) -> bool:
    return NOREPLY_RE.fullmatch(email) is not None


def local_email(cwd: Path = ROOT) -> str | None:
    result = git("config", "--local", "--get", "user.email", cwd=cwd)
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def check_email_options(args: argparse.Namespace) -> None:
    if args.email and not args.dev:
        raise SetupError("參數檢查：--email 要與 --dev 一起使用。")
    if not args.dev:
        return
    if args.email:
        if not is_github_noreply(args.email):
            raise SetupError("參數檢查：email 必須是 <id>+<帳號>@users.noreply.github.com 格式。未做任何設定。")
        return
    current = local_email()
    if current is None or not is_github_noreply(current):
        raise SetupError("參數檢查：開發設定需要 noreply 地址，請加上 --email <id>+<帳號>@users.noreply.github.com。未做任何設定。")


def check_clone_matches(record: dict | None) -> None:
    if not record:
        return
    previous = Path(record["clone"])
    if previous.resolve() != ROOT and previous.exists():
        raise SetupError(f"設定紀錄指向另一個 clone：{previous}。請改用原位置，或先在那裡執行 remove。")


def update_clone() -> None:
    """Fast-forward only, and restart so the new version of this file does the rest."""
    if os.environ.get(REEXEC_ENV):
        return
    if git("status", "--porcelain").stdout.strip():
        raise SetupError(f"更新 clone：{ROOT} 有未提交的改動，未更新也未部署。請提交或還原後重新執行。")
    if git("rev-parse", "--abbrev-ref", "@{upstream}").returncode != 0:
        print("提醒：目前分支沒有 upstream，略過更新。")
        return
    fetched = git("fetch", "--quiet")
    if fetched.returncode != 0:
        raise SetupError("更新 clone：無法取得遠端內容，請檢查網路或存取權限後重新執行。")
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}").stdout.split()
    ahead, behind = int(counts[0]), int(counts[1])
    if not behind:
        if ahead:
            print("提醒：本機領先遠端，略過更新。")
        return
    if ahead:
        raise SetupError(f"更新 clone：{ROOT} 與遠端已分岔，未更新也未部署。請自行整合後重新執行。")
    if git("merge", "--ff-only", "--quiet", "@{upstream}").returncode != 0:
        raise SetupError("更新 clone：無法快轉到遠端版本，請自行確認後重新執行。")
    print("已更新 clone，重新執行設定。")
    env = {**os.environ, REEXEC_ENV: "1"}
    restarted = subprocess.run([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
    raise SystemExit(restarted.returncode)


def guard_status() -> tuple[str, str]:
    """Return the first status line and the full output; status may fail after printing it."""
    output = run_tool("repo_guard.py", "--status").stdout
    lines = output.splitlines()
    return (lines[0].strip() if lines else "unknown"), output


def dev_setup(record: dict, email: str | None) -> tuple[str, list[str], str | None]:
    """Return the guard status, things left for the user, and a failure to report."""
    before = local_email()
    dev = record["dev"] or {"hook_installed": False, "email_set": None, "previous_email": before}
    record["dev"] = dev
    change_email = email is not None and email != before
    if change_email:
        dev["email_set"] = email
    save_record(record)
    if change_email and git("config", "--local", "user.email", email).returncode != 0:
        raise SetupError("開發設定：無法寫入這個 clone 的 user.email。")

    status_before, _ = guard_status()
    installed = run_tool("repo_guard.py", "--install-hook")
    failure = None
    if installed.returncode != 0:
        failure = "commit 防護未啟用：hook 位置已被其他工具佔用，未覆蓋。處理後重新執行。"
    elif status_before == "not-installed":
        dev["hook_installed"] = True
        save_record(record)

    status, output = guard_status()
    todo = []
    if IDENTITY_MISSING in output:
        todo.append("建立 ~/.config/claude-dotfiles/identity.txt，每行一筆不想公開的內容；沒有它時 push 不會通過")
    return status, todo, failure


def deploy(args: argparse.Namespace) -> str:
    command = ["deploy", "--target", str(args.target)]
    if args.force:
        command.append("--force")
    result = run_tool("dotfiles.py", *command)
    print(result.stdout, end="")
    if result.returncode == EXIT_CONFLICT:
        print(result.stderr, end="", file=sys.stderr)
        raise SetupError("部署：同名的 skill 已存在且不受管。確定要取代時加 --force（Windows 為 -Force）。", EXIT_CONFLICT)
    if result.returncode != 0:
        print(result.stderr, end="", file=sys.stderr)
        raise SetupError("部署：未完成。修正上面的問題後重新執行。")
    if "已是最新狀態" in result.stdout:
        return "已是最新狀態"
    match = re.search(r"已部署 (\d+) 個檔案", result.stdout)
    return f"已部署 {match.group(1)} 個檔案" if match else "已部署"


def is_logged_in() -> bool | None:
    claude = shutil.which("claude")
    if not claude:
        return None
    try:
        # The output includes the account email, so it must never be printed.
        result = subprocess.run(
            [claude, "auth", "status"], text=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL
        )
        state = json.loads(result.stdout).get("loggedIn")
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
        return None
    return state if isinstance(state, bool) else None


def install(args: argparse.Namespace) -> int:
    record = load_record()
    check_email_options(args)
    check_clone_matches(record)
    tools_now = [tool for tool in args.installed.split(",") if tool]
    unknown = [tool for tool in tools_now if tool not in KNOWN_TOOLS]
    if unknown:
        raise SetupError(f"參數檢查：不認識的工具 {', '.join(unknown)}。")

    record = record or {"version": RECORD_VERSION, "clone": str(ROOT), "installed_tools": [], "dev": None}
    record["clone"] = str(ROOT)
    record["installed_tools"] = [
        tool for tool in KNOWN_TOOLS if tool in record["installed_tools"] or tool in tools_now
    ]
    save_record(record)

    update_clone()

    guard, todo, failure = None, [], None
    if args.dev:
        guard, todo, failure = dev_setup(record, args.email)
    deployed = deploy(args)

    if is_logged_in() is not True:
        todo.insert(0, "執行 claude 登入（Claude Code 尚未登入或無法確認時）")
    if tools_now:
        todo.append("開新的終端機，讓這次安裝的工具可以直接使用")

    print("設定未全部完成。" if failure else "設定完成。")
    print(f"  已安裝工具：{'、'.join(tools_now) or '無'}")
    print(f"  repo 位置：{ROOT}")
    print(f"  部署結果：{deployed}")
    if guard:
        print(f"  commit 防護：{guard}")
    if todo:
        print("待處理：")
        for item in todo:
            print(f"  - {item}")
    if failure:
        print(f"失敗：{failure}", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_OK


def restore_dev(record: dict, clone: Path) -> list[str]:
    dev = record["dev"]
    if not dev:
        return []
    if not clone.is_dir():
        return [f"找不到 clone（{clone}），略過 commit 防護與提交身分。"]
    notes = []
    if dev["hook_installed"]:
        removed = run_tool("repo_guard.py", "--uninstall-hook", cwd=clone)
        if removed.returncode not in (0, 1):
            raise SetupError("解除 commit 防護：未完成。修正後重新執行 remove。")
        notes.append("commit 防護已移除；其他工具的 hook 未變動。")
    if dev["email_set"]:
        if local_email(clone) != dev["email_set"]:
            notes.append("提交身分設定後已被改動，保留目前的值。")
        else:
            if dev["previous_email"] is None:
                result = git("config", "--local", "--unset", "user.email", cwd=clone)
            else:
                result = git("config", "--local", "user.email", dev["previous_email"], cwd=clone)
            if result.returncode != 0:
                raise SetupError("還原提交身分：未完成。修正後重新執行 remove。")
            notes.append("提交身分已還原。")
    return notes


def remove(args: argparse.Namespace) -> int:
    record = load_record()
    if record is None:
        print("沒有設定紀錄，未做任何變更。")
        return EXIT_OK
    undeployed = run_tool("dotfiles.py", "undeploy", "--target", str(args.target))
    print(undeployed.stdout, end="")
    if undeployed.returncode != 0:
        print(undeployed.stderr, end="", file=sys.stderr)
        raise SetupError("還原 ~/.claude/：未完成。修正上面的問題後重新執行 remove。")
    clone = Path(record["clone"])
    notes = restore_dev(record, clone)

    path = record_path()
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass  # The directory also holds the identity list when there is one.

    print("解除完成。")
    for note in notes:
        print(f"  {note}")
    print("保留在這台機器上的項目：")
    print(f"  - clone：{clone}（不需要時自行刪除）")
    for tool in record["installed_tools"]:
        print(f"  - {TOOL_REMOVAL[tool]}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    default_target = Path.home() / ".claude"
    install_parser = commands.add_parser("install", help="由入口腳本呼叫")
    install_parser.add_argument("--dev", action="store_true", help="同時做開發設定")
    install_parser.add_argument("--email", help="開發設定使用的 GitHub noreply 地址")
    install_parser.add_argument("--force", action="store_true", help="備份後取代同名且不受管的 skill")
    install_parser.add_argument("--installed", default="", help="入口這次安裝的工具，以逗號分隔")
    install_parser.add_argument("--target", type=Path, default=default_target, help="預設為 ~/.claude")
    remove_parser = commands.add_parser("remove", help="還原 ~/.claude/ 與開發設定")
    remove_parser.add_argument("--target", type=Path, default=default_target, help="預設為 ~/.claude")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        return install(args) if args.command == "install" else remove(args)
    except SetupError as error:
        print(f"失敗：{error}", file=sys.stderr)
        return error.code
    except OSError as error:
        print(f"失敗：{error}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
