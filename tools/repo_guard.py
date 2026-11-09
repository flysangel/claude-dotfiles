#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Keep files outside the allowlist, secrets, and personal data out of git.

Contract: specs/001-repo-commit-guard/contracts/repo-guard.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_INCOMPLETE = 3

ALLOWLIST_NAME = ".repo-allowlist"
EXCEPTIONS_NAME = ".repo-guard-exceptions.json"
IDENTITY_ENV = "REPO_GUARD_IDENTITY_FILE"
DEFAULT_IDENTITY_PATH = Path("~/.config/claude-dotfiles/identity.txt")

HOOK_MARKER = "# managed-by: tools/repo_guard.py"
LEGACY_HOOK_MARKER = "# managed-by: tools/check_allowlist.py"
HOOK_PREFIX = f"#!/bin/sh\n{HOOK_MARKER}\n"
HOOKS = {
    "pre-commit": HOOK_PREFIX + "exec uv run tools/repo_guard.py --staged\n",
    "commit-msg": HOOK_PREFIX + 'exec uv run tools/repo_guard.py --commit-msg "$1"\n',
    "pre-push": HOOK_PREFIX + "cat > /dev/null\nexec uv run tools/repo_guard.py --history\n",
}

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

SECRET_KIND = "secret"
FIXES = {
    "allowlist": f"確定要入庫就加進 {ALLOWLIST_NAME}，否則取消暫存",
    "binary": "二進位檔無法掃描，移除它；確定安全時記錄例外",
    "home-path": "改用相對路徑或 ~ 表示法",
    "git-email": "移除個人 email",
    "email": "移除，或改用 noreply 與保留網域的地址",
    SECRET_KIND: "移除；真實機密要視為已外洩並更換",
    "identity": "移除本機識別清單列出的內容",
    "author": "用 git config user.email 設定此 repo 的 noreply 地址",
    "committer": "用 git config user.email 設定此 repo 的 noreply 地址",
}
NOT_EXEMPTIBLE = frozenset({"allowlist", "git-email", "identity", "author", "committer"})


class CheckError(Exception):
    """The check could not finish, so its result cannot be trusted."""


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    kind: str
    fingerprint: str = ""
    commit: str = ""

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        prefix = f"{self.commit[:12]} " if self.commit else ""
        text = f"{prefix}{where}: {self.kind}：{FIXES[self.kind]}"
        if self.fingerprint:
            text += f" [指紋 {self.fingerprint}]"
        return text


@dataclass(frozen=True)
class Identity:
    entries: tuple[str, ...]

    def matches(self, text: str) -> bool:
        lowered = text.lower()
        return any(entry in lowered for entry in self.entries)


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


def load_exceptions(root: Path) -> frozenset[tuple[str, str, str]]:
    path = root / EXCEPTIONS_NAME
    if not path.exists():
        return frozenset()
    try:
        items = json.loads(path.read_text(encoding="utf-8"))["exceptions"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CheckError(f"{EXCEPTIONS_NAME} 格式錯誤") from error
    if not isinstance(items, list):
        raise CheckError(f"{EXCEPTIONS_NAME} 格式錯誤：exceptions 必須是清單")
    found = set()
    for index, item in enumerate(items, start=1):
        problem = exception_problem(item)
        if problem:
            raise CheckError(f"{EXCEPTIONS_NAME} 第 {index} 筆：{problem}")
        found.add((item["path"], item["kind"], item["line_sha256"].lower()))
    return frozenset(found)


def exception_problem(item: object) -> str:
    if not isinstance(item, dict):
        return "必須是物件"
    fields = {key: item.get(key) for key in ("path", "kind", "line_sha256", "reason")}
    if not all(isinstance(value, str) for value in fields.values()):
        return "path、kind、line_sha256、reason 都必須是字串"
    if not fields["path"] or any(char in fields["path"] for char in "*?[") or "\\" in fields["path"]:
        return "path 必須是單一檔案的完整路徑"
    if fields["kind"] not in FIXES:
        return "kind 不是已知的類型"
    if fields["kind"] in NOT_EXEMPTIBLE:
        return f"{fields['kind']} 不可豁免"
    if not re.fullmatch(r"[0-9a-fA-F]{64}", fields["line_sha256"]):
        return "line_sha256 必須是 64 位十六進位"
    if not fields["reason"].strip():
        return "reason 不可為空"
    return ""


def identity_path() -> Path:
    override = os.environ.get(IDENTITY_ENV)
    return Path(override) if override else DEFAULT_IDENTITY_PATH.expanduser()


def load_identity() -> Identity:
    path = identity_path()
    if not path.exists():
        return Identity(())
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise CheckError(f"無法讀取本機識別清單：{error}") from error
    entries = (line.strip().lower() for line in lines)
    return Identity(tuple(entry for entry in entries if entry and not entry.startswith("#")))


def warn_identity_missing() -> None:
    print("提醒：本機識別清單不存在或沒有內容，這次沒有比對姓名、主機名稱等個資。", file=sys.stderr)


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


def line_hash(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8", "surrogateescape")).hexdigest()


def scan_text(
    path: str,
    text: str,
    own_email: str,
    identity: Identity = Identity(()),
    exceptions: frozenset[tuple[str, str, str]] = frozenset(),
    exemptible: bool = True,
) -> list[Violation]:
    found: list[Violation] = []
    for number, line in enumerate(text.splitlines(), start=1):
        kinds: list[str] = []
        if HOME_PATH_RE.search(line):
            kinds.append("home-path")
        if own_email and own_email in line.lower():
            kinds.append("git-email")
        elif any(not is_public_safe_email(match) for match in EMAIL_RE.findall(line)):
            kinds.append("email")
        if any(pattern.search(line) for pattern in SECRET_RES):
            kinds.append(SECRET_KIND)
        if identity.matches(line):
            kinds.append("identity")
        digest = line_hash(line)
        for kind in kinds:
            if (path, kind, digest) in exceptions:
                continue
            show = exemptible and kind not in NOT_EXEMPTIBLE
            found.append(Violation(path, number, kind, digest if show else ""))
    return found


def scan_content(
    path: str,
    content: bytes,
    own_email: str,
    identity: Identity,
    exceptions: frozenset[tuple[str, str, str]],
) -> list[Violation]:
    if b"\0" in content:
        digest = hashlib.sha256(content).hexdigest()
        if (path, "binary", digest) in exceptions:
            return []
        return [Violation(path, 0, "binary", digest)]
    return scan_text(path, content.decode("utf-8", "surrogateescape"), own_email, identity, exceptions)


def check_paths(root: Path, paths: list[str], identity: Identity) -> list[Violation]:
    patterns = load_allowlist(root)
    exceptions = load_exceptions(root)
    own_email = global_email()
    found: list[Violation] = []
    for path in paths:
        if not is_allowed(path, patterns):
            found.append(Violation(path, 0, "allowlist"))
            continue
        content = git("show", f":{path}", cwd=root)
        found.extend(scan_content(path, content, own_email, identity, exceptions))
    return found


def parse_ident(ident: str) -> tuple[str, str]:
    match = re.match(r"(.*?)\s*<([^>]*)>", ident)
    return (match.group(1), match.group(2)) if match else ("", "")


def identity_violations(
    people: list[tuple[str, str, str]], identity: Identity, commit: str = ""
) -> list[Violation]:
    """Check (label, name, email) for one commit."""
    found: list[Violation] = []
    for kind, name, email in people:
        label = "commit 作者" if kind == "author" else "commit 提交者"
        if not is_noreply(email):
            found.append(Violation(label, 0, kind, commit=commit))
        if identity.matches(name) or identity.matches(email):
            found.append(Violation(label, 0, "identity", commit=commit))
    return found


def check_current_identity(root: Path, identity: Identity) -> list[Violation]:
    people = []
    for variable, kind in (("GIT_AUTHOR_IDENT", "author"), ("GIT_COMMITTER_IDENT", "committer")):
        name, email = parse_ident(git("var", variable, cwd=root).decode("utf-8", "replace"))
        people.append((kind, name, email))
    return identity_violations(people, identity)


def check_commit_message(path: Path, identity: Identity) -> list[Violation]:
    try:
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
    except OSError as error:
        raise CheckError(f"無法讀取 commit 訊息：{error}") from error
    lines = "\n".join("" if line.startswith("#") else line for line in text.splitlines())
    return scan_text("commit 訊息", lines, global_email(), identity, exemptible=False)


def report(violations: list[Violation]) -> int:
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        print(f"檢查未通過：{len(violations)} 個問題。", file=sys.stderr)
        if any(violation.fingerprint for violation in violations):
            print(f"確定是誤判時，把指紋與理由記錄到 {EXCEPTIONS_NAME}。", file=sys.stderr)
        return EXIT_VIOLATION
    print("檢查通過。")
    return EXIT_OK


def history_commits(root: Path) -> list[dict[str, str]]:
    revisions = git("rev-list", "--all", "--reverse", cwd=root).decode().split()
    commits = []
    for revision in revisions:
        raw = git("log", "-1", "--format=%an%x00%ae%x00%cn%x00%ce%x00%B", revision, cwd=root)
        author, author_email, committer, committer_email, message = raw.decode(
            "utf-8", "surrogateescape"
        ).split("\0", 4)
        commits.append(
            {
                "id": revision,
                "author": author,
                "author_email": author_email,
                "committer": committer,
                "committer_email": committer_email,
                "message": message,
            }
        )
    return commits


def commit_blobs(root: Path, commit: str) -> list[tuple[str, str]]:
    """Return the (blob, path) versions a commit introduces, merges included."""
    fields = git(
        "diff-tree", "-r", "-m", "--root", "--no-renames", "--no-commit-id", "--diff-filter=d", "-z", commit, cwd=root
    ).split(b"\0")
    blobs = []
    for index in range(0, len(fields) - 1, 2):
        meta = fields[index].decode().split()
        if meta and meta[1] != "160000":
            blobs.append((meta[3], fields[index + 1].decode("utf-8", "surrogateescape")))
    return blobs


def check_history(root: Path, identity: Identity) -> list[Violation]:
    patterns = load_allowlist(root)
    exceptions = load_exceptions(root)
    own_email = global_email()
    found: list[Violation] = []
    seen_paths: set[str] = set()
    seen_blobs: set[tuple[str, str]] = set()
    for commit in history_commits(root):
        identifier = commit["id"]
        found.extend(
            identity_violations(
                [
                    ("author", commit["author"], commit["author_email"]),
                    ("committer", commit["committer"], commit["committer_email"]),
                ],
                identity,
                identifier,
            )
        )
        for violation in scan_text(
            "commit 訊息", commit["message"], own_email, identity, exemptible=False
        ):
            found.append(Violation(violation.path, violation.line, violation.kind, commit=identifier))
        for blob, path in commit_blobs(root, identifier):
            if path not in seen_paths:
                seen_paths.add(path)
                if not is_allowed(path, patterns):
                    found.append(Violation(path, 0, "allowlist", commit=identifier))
            if (blob, path) in seen_blobs or not is_allowed(path, patterns):
                continue
            seen_blobs.add((blob, path))
            content = git("cat-file", "blob", blob, cwd=root)
            for violation in scan_content(path, content, own_email, identity, exceptions):
                found.append(
                    Violation(violation.path, violation.line, violation.kind, violation.fingerprint, identifier)
                )
    return found


def run_history(root: Path, without_identity: bool = False) -> int:
    if without_identity:
        print("注意：這次沒有比對本機識別清單，姓名、主機名稱等個資要靠本機檢查。")
    identity = Identity(()) if without_identity else load_identity()
    if not identity.entries and not without_identity:
        print(f"本機識別清單不存在或沒有內容：{identity_path()}", file=sys.stderr)
        print("請先建立，否則無法確認歷史中沒有姓名、主機名稱等個資。", file=sys.stderr)
        print("不通過", file=sys.stderr)
        return EXIT_INCOMPLETE
    violations = check_history(root, identity) + check_paths(root, tracked_paths(root), identity)
    unique = list(dict.fromkeys(violations))
    for violation in unique:
        print(violation, file=sys.stderr)
    if unique:
        if any(violation.fingerprint for violation in unique):
            print(f"確定是誤判時，把指紋與理由記錄到 {EXCEPTIONS_NAME}。", file=sys.stderr)
        print(f"不通過：{len(unique)} 個問題", file=sys.stderr)
        return EXIT_VIOLATION
    print("通過")
    return EXIT_OK


def hooks_dir(root: Path) -> Path:
    # Not --git-path: it follows core.hooksPath, which may be shared by every repo on the machine.
    common = Path(git("rev-parse", "--git-common-dir", cwd=root).decode().strip())
    return (common if common.is_absolute() else root / common) / "hooks"


def hooks_path_setting(root: Path) -> str:
    try:
        return git("config", "core.hooksPath", cwd=root).decode().strip()
    except CheckError:
        return ""


def is_own_hook(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return HOOK_MARKER in text or LEGACY_HOOK_MARKER in text


def install_hooks(root: Path) -> int:
    directory = hooks_dir(root)
    foreign = [name for name in HOOKS if (directory / name).exists() and not is_own_hook(directory / name)]
    if foreign:
        print(f"{', '.join(foreign)} 已存在且不是由此工具安裝，未做任何變更。", file=sys.stderr)
        return EXIT_VIOLATION
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in HOOKS.items():
        path = directory / name
        path.write_bytes(body.encode())
        path.chmod(0o755)
    print(f"已安裝 {', '.join(HOOKS)} hook。")
    if hooks_path_setting(root):
        print("注意：已設定 core.hooksPath，請確認它會轉交給 .git/hooks，否則這些 hook 不會執行。")
    return EXIT_OK


def uninstall_hooks(root: Path) -> int:
    directory = hooks_dir(root)
    removed = []
    foreign = []
    for name in HOOKS:
        path = directory / name
        if not path.exists():
            continue
        if is_own_hook(path):
            path.unlink()
            removed.append(name)
        else:
            foreign.append(name)
    print(f"已移除 {', '.join(removed)} hook。" if removed else "沒有可移除的 hook。")
    if foreign:
        print(f"{', '.join(foreign)} 不是由此工具安裝，未移除。", file=sys.stderr)
        return EXIT_VIOLATION
    return EXIT_OK


def print_status(root: Path) -> int:
    directory = hooks_dir(root)
    installed = all(
        (directory / name).exists() and HOOK_MARKER in (directory / name).read_text(encoding="utf-8", errors="replace")
        for name in HOOKS
    )
    setting = hooks_path_setting(root)
    if not installed:
        print("not-installed")
        print("  執行 uv run tools/repo_guard.py --install-hook 來啟用")
    elif setting:
        print("unverified")
        print("  hook 已安裝，但無法確認 core.hooksPath 會轉交給它們")
    else:
        print("enabled")
    print(f"  core.hooksPath：{'已設定' if setting else '未設定'}")
    print(f"  本機識別清單：{'可用' if load_identity().entries else '不存在或沒有內容'}")
    emails = [parse_ident(git("var", var, cwd=root).decode("utf-8", "replace"))[1] for var in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT")]
    print(f"  作者與提交者 email：{'noreply' if all(is_noreply(email) for email in emails) else '不是 noreply'}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="檢查暫存區與 commit 身分（預設）")
    mode.add_argument("--all", action="store_true", help="檢查所有已追蹤的檔案")
    mode.add_argument("--history", action="store_true", help="檢查所有已追蹤的檔案與完整歷史")
    mode.add_argument("--commit-msg", type=Path, metavar="FILE", help="檢查 commit 訊息")
    mode.add_argument("--status", action="store_true", help="回報防護是否已啟用")
    mode.add_argument("--install-hook", action="store_true", help="安裝 git hook")
    mode.add_argument("--uninstall-hook", action="store_true", help="移除此工具安裝的 hook")
    parser.add_argument("--without-identity", action="store_true", help="搭配 --history，用於沒有本機識別清單的 CI")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    if args.without_identity and not args.history:
        print("--without-identity 只能與 --history 一起使用。", file=sys.stderr)
        return EXIT_INCOMPLETE
    try:
        root = repo_root()
        if args.install_hook:
            return install_hooks(root)
        if args.uninstall_hook:
            return uninstall_hooks(root)
        if args.status:
            return print_status(root)
        if args.history:
            return run_history(root, args.without_identity)
        identity = load_identity()
        if not identity.entries:
            warn_identity_missing()
        if args.commit_msg:
            return report(check_commit_message(args.commit_msg, identity))
        if args.all:
            return report(check_paths(root, tracked_paths(root), identity))
        return report(check_current_identity(root, identity) + check_paths(root, staged_paths(root), identity))
    except (CheckError, OSError) as error:
        print(f"無法完成檢查：{error}", file=sys.stderr)
        return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
