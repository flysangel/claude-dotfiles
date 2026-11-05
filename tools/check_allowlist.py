#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Keep files outside the allowlist, secrets, and personal data out of git.

Contract: specs/002-personal-sdd-toolkit/contracts/allowlist.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_INCOMPLETE = 3

ALLOWLIST_NAME = ".repo-allowlist"
FAKE_SECRET_DIR = "tests/fixtures/sample-project/"
HOOK_MARKER = "# managed-by: tools/check_allowlist.py"
HOOK_BODY = f"#!/bin/sh\n{HOOK_MARKER}\nexec uv run tools/check_allowlist.py --staged\n"

HOME_PATH_RE = re.compile(
    r"(?<![\w.-])/(?:home|Users)/[A-Za-z0-9_][\w.-]*|\b[A-Za-z]:[\\/]+Users[\\/]+[^\s\\/\"'`<>]+"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
SECRET_RES = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\b"
        r"\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"
    ),
)
RESERVED_DOMAINS = ("example.com", "example.net", "example.org")
RESERVED_TLDS = (".example", ".invalid", ".localhost", ".test")


class CheckError(Exception):
    """The check could not finish, so its result cannot be trusted."""


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    kind: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: {self.kind}"


def git(*args: str, cwd: Path | None = None) -> bytes:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)
    except OSError as error:
        raise CheckError(f"無法執行 git：{error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise CheckError(f"git {args[0]} 失敗：{detail}")
    return result.stdout


def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel").decode().strip())


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts))


def load_allowlist(root: Path) -> list[re.Pattern[str]]:
    path = root / ALLOWLIST_NAME
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise CheckError(f"無法讀取 {ALLOWLIST_NAME}：{error}") from error
    patterns = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    if not patterns:
        raise CheckError(f"{ALLOWLIST_NAME} 沒有任何規則")
    return [glob_to_regex(pattern) for pattern in patterns]


def is_allowed(path: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.fullmatch(path) for pattern in patterns)


def split_paths(output: bytes) -> list[str]:
    return [item.decode("utf-8", "surrogateescape") for item in output.split(b"\0") if item]


def staged_paths(root: Path) -> list[str]:
    return split_paths(git("diff", "--cached", "--name-only", "--diff-filter=d", "-z", cwd=root))


def tracked_paths(root: Path) -> list[str]:
    return split_paths(git("ls-files", "-z", cwd=root))


def global_email() -> str:
    try:
        return git("config", "--global", "user.email").decode().strip().lower()
    except CheckError:
        return ""


def is_noreply(email: str) -> bool:
    email = email.lower()
    return email.startswith("noreply@") or email.endswith("@users.noreply.github.com")


def is_public_safe_email(email: str) -> bool:
    if is_noreply(email):
        return True
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in RESERVED_DOMAINS or domain.endswith(RESERVED_TLDS)


def scan_text(path: str, text: str, own_email: str) -> list[Violation]:
    found: list[Violation] = []
    check_secrets = not path.startswith(FAKE_SECRET_DIR)
    for number, line in enumerate(text.splitlines(), start=1):
        if HOME_PATH_RE.search(line):
            found.append(Violation(path, number, "個人家目錄路徑"))
        if own_email and own_email in line.lower():
            found.append(Violation(path, number, "全域 git email"))
        elif any(not is_public_safe_email(match) for match in EMAIL_RE.findall(line)):
            found.append(Violation(path, number, "email"))
        if check_secrets and any(pattern.search(line) for pattern in SECRET_RES):
            found.append(Violation(path, number, "憑證或 token"))
    return found


def check_paths(root: Path, paths: list[str]) -> list[Violation]:
    patterns = load_allowlist(root)
    own_email = global_email()
    found: list[Violation] = []
    for path in paths:
        if not is_allowed(path, patterns):
            found.append(Violation(path, 0, f"不在 {ALLOWLIST_NAME} 內"))
            continue
        content = git("show", f":{path}", cwd=root)
        if b"\0" in content:
            found.append(Violation(path, 0, "二進位檔案無法掃描"))
            continue
        found.extend(scan_text(path, content.decode("utf-8", "replace"), own_email))
    return found


def check_identity(root: Path) -> list[Violation]:
    found: list[Violation] = []
    for variable, label in (("GIT_AUTHOR_IDENT", "作者"), ("GIT_COMMITTER_IDENT", "提交者")):
        match = re.search(r"<([^>]*)>", git("var", variable, cwd=root).decode("utf-8", "replace"))
        if not match or not is_noreply(match.group(1)):
            found.append(
                Violation(
                    f"commit {label}",
                    0,
                    "email 不是 noreply 地址，請用 git config user.email 設定此 repo 的 noreply 地址",
                )
            )
    return found


def hook_path(root: Path) -> Path:
    # Not --git-path: it follows core.hooksPath, which may be shared by every repo on the machine.
    common = Path(git("rev-parse", "--git-common-dir", cwd=root).decode().strip())
    return (common if common.is_absolute() else root / common) / "hooks" / "pre-commit"


def hooks_path_setting(root: Path) -> str:
    try:
        return git("config", "core.hooksPath", cwd=root).decode().strip()
    except CheckError:
        return ""


def install_hook(root: Path) -> int:
    path = hook_path(root)
    if path.exists() and HOOK_MARKER not in path.read_text(encoding="utf-8", errors="replace"):
        print(f"{path.name} 已存在且不是由此工具安裝，未覆蓋。", file=sys.stderr)
        return EXIT_VIOLATION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(HOOK_BODY.encode())
    path.chmod(0o755)
    print("已安裝 pre-commit hook。")
    if hooks_path_setting(root):
        print("注意：已設定 core.hooksPath，請確認它會轉交給 .git/hooks，否則此 hook 不會執行。")
    return EXIT_OK


def uninstall_hook(root: Path) -> int:
    path = hook_path(root)
    if not path.exists():
        print("沒有已安裝的 pre-commit hook。")
        return EXIT_OK
    if HOOK_MARKER not in path.read_text(encoding="utf-8", errors="replace"):
        print(f"{path.name} 不是由此工具安裝，未移除。", file=sys.stderr)
        return EXIT_VIOLATION
    path.unlink()
    print("已移除 pre-commit hook。")
    return EXIT_OK


def run_check(root: Path, check_all: bool) -> int:
    if check_all:
        violations = check_paths(root, tracked_paths(root))
    else:
        violations = check_identity(root) + check_paths(root, staged_paths(root))
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        print(f"檢查未通過：{len(violations)} 個問題。", file=sys.stderr)
        return EXIT_VIOLATION
    print("檢查通過。")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="檢查暫存區（預設）")
    mode.add_argument("--all", action="store_true", help="檢查所有已追蹤的檔案")
    mode.add_argument("--install-hook", action="store_true", help="安裝 pre-commit hook")
    mode.add_argument("--uninstall-hook", action="store_true", help="移除自己安裝的 hook")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        root = repo_root()
        if args.install_hook:
            return install_hook(root)
        if args.uninstall_hook:
            return uninstall_hook(root)
        return run_check(root, args.all)
    except (CheckError, OSError) as error:
        print(f"無法完成檢查：{error}", file=sys.stderr)
        return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
