#!/usr/bin/env python3
"""Stand-ins for the tools the setup entry scripts call. Nothing is installed or downloaded.

Each stub runs this file with the tool name first, logs the call, and acts according to FAKE_* variables.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve()


def write_stub(directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        body = f'@"{sys.executable}" "{TOOL}" {name} %*\r\n@exit /b %ERRORLEVEL%\r\n'
        (directory / f"{name}.cmd").write_bytes(body.encode())
        return
    path = directory / name
    path.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{TOOL}" {name} "$@"\n', encoding="utf-8")
    path.chmod(0o755)


def local_bin() -> Path:
    return Path(os.environ["FAKE_HOME"]) / ".local" / "bin"


def log(name: str, args: list[str], **extra: object) -> None:
    entry = {"tool": name, "args": args, "sudo": "FAKE_VIA_SUDO" in os.environ, **extra}
    with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")


def installer_for(url: str) -> str | None:
    if "astral.sh" in url:
        return "uv"
    if "claude.ai" in url:
        return "claude"
    return None


def download_fails(url: str) -> bool:
    blocked = os.environ.get("FAKE_DOWNLOAD_FAIL", "")
    return bool(blocked) and blocked in url


def main() -> int:
    name, args = sys.argv[1], sys.argv[2:]
    if name == "_install":
        log("_install", args)
        write_stub(local_bin(), args[0])
        return 0
    if name == "uv" and args[:1] == ["run"]:
        log(name, args, stdin=sys.stdin.read())
        return subprocess.run([sys.executable, *args[1:]], stdin=subprocess.DEVNULL).returncode
    log(name, args)

    if name == "uname":
        print(os.environ.get("FAKE_UNAME", "Linux"))
    elif name == "id":
        print(os.environ.get("FAKE_UID", "1000"))
    elif name == "sudo":
        if "FAKE_SUDO_FAIL" in os.environ:
            print("sudo: refused", file=sys.stderr)
            return 1
        return subprocess.run(args, env={**os.environ, "FAKE_VIA_SUDO": "1"}).returncode
    elif name in ("apt-get", "dnf", "pacman", "winget"):
        if args[0] == "update":
            return 0
        if "FAKE_PM_FAIL" in os.environ:
            return 1
        write_stub(Path(os.environ["FAKE_BIN"]), "git")
    elif name in ("curl", "wget"):
        url = args[-1]
        if download_fails(url):
            return 22
        tool = installer_for(url)
        if tool:
            print(f'"{sys.executable}" "{TOOL}" _install {tool}')
    elif name == "powershell":
        command = " ".join(args)
        if download_fails(command):
            return 1
        tool = installer_for(command)
        if tool:
            log("_install", [tool])
            write_stub(local_bin(), tool)
    elif name == "uv":
        print(f"uv {os.environ.get('FAKE_UV_VERSION', '0.9.0')}")
    elif name == "claude":
        print("2.0.0 (Claude Code)")
    elif name == "git":
        if args[:1] == ["--version"]:
            print(f"git version {os.environ.get('FAKE_GIT_VERSION', '2.43.0')}")
            return 0
        # Tests hide the real git's folder, but the programs git starts still need the DLLs there.
        real = os.environ["REAL_GIT"]
        path = os.pathsep.join((str(Path(real).parent), os.environ["PATH"]))
        return subprocess.run([real, *args], env={**os.environ, "PATH": path}).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
