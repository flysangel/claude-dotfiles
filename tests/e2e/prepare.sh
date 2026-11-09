#!/usr/bin/env bash
# Runs as root in a throwaway container: set up the environment, then start the driver as the right user.
# Everything is read from /e2e, which the workflow mounts read-only. Never run this on a real machine.
set -eu

environment=$1
driver=(bash /e2e/linux.sh "$environment" /e2e/source.git)

case "$environment" in
ubuntu | ubuntu-public)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq curl sudo >/dev/null
    useradd -m tester
    echo 'tester ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/tester
    exec su - tester -c "E2E_SETUP_URL='${E2E_SETUP_URL:-}' ${driver[*]}"
    ;;
fedora | arch)
    exec "${driver[@]}"
    ;;
minimum)
    # The oldest git and uv the setup accepts, and only wget for downloads. Claude Code is a stand-in
    # because this environment checks version limits, not the Claude Code installer.
    echo 'deb http://archive.debian.org/debian buster main' >/etc/apt/sources.list
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq wget git ca-certificates >/dev/null
    wget -qO- https://astral.sh/uv/0.4.0/install.sh | sh >/dev/null
    for candidate in "$HOME/.cargo/bin/uv" "$HOME/.local/bin/uv"; do
        if [ -x "$candidate" ]; then
            install -m 755 "$candidate" /usr/local/bin/uv
        fi
    done
    printf '#!/bin/sh\necho "0.0.0 (Claude Code stand-in)"\n' >/usr/local/bin/claude
    chmod 755 /usr/local/bin/claude
    exec "${driver[@]}"
    ;;
*)
    echo "unknown environment: $environment" >&2
    exit 2
    ;;
esac
