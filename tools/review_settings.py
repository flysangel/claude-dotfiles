#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Classify each item in Claude settings as shareable or not, without printing any value.

Contract: specs/001-repo-commit-guard/contracts/review-settings.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_guard  # noqa: E402

SECRET = "含機密"
MACHINE = "機器專屬"
UNKNOWN = "待判斷"
SHARED = "可共用"
SEVERITY = (SECRET, MACHINE, UNKNOWN, SHARED)

EXIT_OK = 0
EXIT_UNREADABLE = 3

SAFE_KEYS = frozenset(
    {
        "alwaysThinkingEnabled",
        "autoUpdates",
        "cleanupPeriodDays",
        "editorMode",
        "includeCoAuthoredBy",
        "language",
        "outputStyle",
        "spinnerTipsEnabled",
        "theme",
        "tui",
        "verbose",
    }
)
MACHINE_KEYS = frozenset({"additionalDirectories", "apiKeyHelper", "awsAuthRefresh", "otelHeadersHelper"})
SECRET_WORDS = frozenset({"apikey", "auth", "credential", "credentials", "passwd", "password", "secret", "token"})
LOCAL_PATH_RE = re.compile(r"(?:^|[\s\"'=:])(?:~[\\/]|\$HOME\b|%USERPROFILE%|/[\w.-]+/|[A-Za-z]:[\\/])")
MASK = "***"


def key_words(key: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
    return [word.lower() for word in re.split(r"[\s_.-]+", spaced) if word]


def is_secret_key(key: str) -> bool:
    words = key_words(key)
    if any(word in SECRET_WORDS for word in words):
        return True
    return any(left == "api" and right == "key" for left, right in zip(words, words[1:]))


def value_class(value: str, identity: repo_guard.Identity) -> str | None:
    if any(pattern.search(value) for pattern in repo_guard.SECRET_RES):
        return SECRET
    if repo_guard.HOME_PATH_RE.search(value) or identity.matches(value):
        return MACHINE
    if LOCAL_PATH_RE.search(value):
        return MACHINE
    return None


def safe_key(key: str, identity: repo_guard.Identity) -> str:
    return MASK if is_secret_like_name(key) or identity.matches(key) else key


def is_secret_like_name(key: str) -> bool:
    return any(pattern.search(key) for pattern in repo_guard.SECRET_RES)


def walk(value: object, path: str, identity: repo_guard.Identity) -> list[tuple[str, str]]:
    """Return (class, key path) for every setting that triggered a rule."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{safe_key(str(key), identity)}"
            if is_secret_key(str(key)) or is_secret_like_name(str(key)):
                found.append((SECRET, child))
            elif identity.matches(str(key)):
                found.append((MACHINE, child))
            found.extend(walk(item, child, identity))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk(item, f"{path}[{index}]", identity))
    elif isinstance(value, str):
        kind = value_class(value, identity)
        if kind:
            found.append((kind, path))
    return found


def classify(key: str, value: object, identity: repo_guard.Identity) -> tuple[str, list[str]]:
    shown = safe_key(key, identity)
    triggers = walk(value, shown, identity)
    if is_secret_key(key) or is_secret_like_name(key):
        triggers.append((SECRET, shown))
    elif identity.matches(key) or key in MACHINE_KEYS:
        triggers.append((MACHINE, shown))
    if triggers:
        worst = min((kind for kind, _ in triggers), key=SEVERITY.index)
        return worst, sorted({path for kind, path in triggers if kind == worst})
    return (SHARED if key in SAFE_KEYS else UNKNOWN), []


def review(settings: dict, identity: repo_guard.Identity) -> int:
    counts = dict.fromkeys(SEVERITY, 0)
    for key, value in settings.items():
        kind, paths = classify(str(key), value, identity)
        counts[kind] += 1
        suffix = f"  ({', '.join(paths)})" if paths else ""
        print(f"{kind}  {safe_key(str(key), identity)}{suffix}")
    summary = "、".join(f"{kind} {counts[kind]}" for kind in (SHARED, SECRET, MACHINE, UNKNOWN))
    print(f"\n共 {len(settings)} 項：{summary}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path.home() / ".claude" / "settings.json", help="預設為 ~/.claude/settings.json")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        settings = json.loads(args.path.read_text(encoding="utf-8"))
    except OSError:
        print("無法讀取設定檔。", file=sys.stderr)
        return EXIT_UNREADABLE
    except ValueError:
        print("設定檔不是有效的 JSON。", file=sys.stderr)
        return EXIT_UNREADABLE
    if not isinstance(settings, dict):
        print("設定檔的最上層必須是物件。", file=sys.stderr)
        return EXIT_UNREADABLE
    try:
        identity = repo_guard.load_identity()
    except repo_guard.CheckError as error:
        print(error, file=sys.stderr)
        return EXIT_UNREADABLE
    return review(settings, identity)


if __name__ == "__main__":
    sys.exit(main())
