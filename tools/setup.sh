#!/usr/bin/env bash
# One-line setup for Linux: install missing tools, get the repo, then hand over to machine_setup.py.
# Contract: specs/003-license-oneline-setup/contracts/setup-cli.md
#
# Everything lives in functions and the last line calls main, so a partial download runs nothing.

say() {
    printf '==> %s\n' "$1"
}

fail() {
    printf 'setup failed: %s\n' "$1" >&2
    if [ -n "$INSTALLED" ]; then
        printf 'tools installed in this run: %s\n' "$INSTALLED" >&2
    fi
    exit 1
}

note_installed() {
    INSTALLED="${INSTALLED:+$INSTALLED,}$1"
}

extract_version() {
    if [[ "$1" =~ ([0-9]+(\.[0-9]+)+) ]]; then
        printf '%s' "${BASH_REMATCH[1]}"
    fi
}

version_at_least() {
    local have want i
    IFS=. read -r -a have <<<"$1"
    IFS=. read -r -a want <<<"$2"
    for i in 0 1 2; do
        if ((10#${have[i]:-0} > 10#${want[i]:-0})); then
            return 0
        fi
        if ((10#${have[i]:-0} < 10#${want[i]:-0})); then
            return 1
        fi
    done
    return 0
}

check_version() {
    local tool=$1 need=$2 have
    command -v "$tool" >/dev/null 2>&1 || return 0
    have=$(extract_version "$("$tool" --version 2>/dev/null)")
    if [ -z "$have" ] || ! version_at_least "$have" "$need"; then
        fail "version check: $tool ${have:-unknown} is too old, $need or newer is required. Upgrade it and run this again."
    fi
}

download() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$1"
    else
        return 127
    fi
}

run_official_installer() {
    local name=$1 url=$2 shell=$3 script
    say "Installing $name"
    script=$(mktemp) || fail "installing $name: cannot create a temporary file."
    if ! download "$url" >"$script"; then
        rm -f "$script"
        fail "installing $name: cannot download $url. Check the network and run this again, or see $4"
    fi
    if ! "$shell" "$script"; then
        rm -f "$script"
        fail "installing $name: the official installer failed. See $4"
    fi
    rm -f "$script"
    hash -r
    command -v "$5" >/dev/null 2>&1 || fail "installing $name: installed, but $5 is not on PATH. Open a new terminal and run this again."
    note_installed "$5"
}

install_git() {
    local manual="install git with your package manager (https://git-scm.com/downloads/linux) and run this again"
    local elevate=()
    if [ "$(id -u)" != "0" ]; then
        command -v sudo >/dev/null 2>&1 || fail "installing git: sudo is not available, $manual."
        elevate=(sudo)
    fi
    say "Installing git (your system may ask for a password)"
    if command -v apt-get >/dev/null 2>&1; then
        "${elevate[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update -y &&
            "${elevate[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y git ||
            fail "installing git: apt-get failed, $manual."
    elif command -v dnf >/dev/null 2>&1; then
        "${elevate[@]}" dnf install -y git || fail "installing git: dnf failed, $manual."
    elif command -v pacman >/dev/null 2>&1; then
        "${elevate[@]}" pacman -Sy --noconfirm git || fail "installing git: pacman failed, $manual."
    else
        fail "installing git: no supported package manager found, $manual."
    fi
    hash -r
    command -v git >/dev/null 2>&1 || fail "installing git: installed, but git is not on PATH. Open a new terminal and run this again."
    note_installed git
}

normalize_origin() {
    local url=$1
    url=${url%/}
    url=${url%.git}
    url=${url%/}
    case "$url" in
    https://* | http://* | ssh://*)
        url=${url#*://}
        url=${url#*@}
        printf '%s' "${url,,}"
        ;;
    /* | ./* | ../* | file://*)
        printf '%s' "$url"
        ;;
    *@*:*)
        url=${url#*@}
        url=${url/://}
        printf '%s' "${url,,}"
        ;;
    *)
        printf '%s' "$url"
        ;;
    esac
}

ensure_clone() {
    local dir=$1 source=$2 top here origin
    if [ -e "$dir" ]; then
        # Nothing inside the directory may run until it is known to be this repo.
        top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || fail "getting the repo: $dir exists and is not a git repo. Use --dir to choose another location."
        here=$(cd "$dir" && pwd -P)
        [ "$top" = "$here" ] || fail "getting the repo: $dir is inside another git repo. Use --dir to choose another location."
        origin=$(git -C "$dir" remote get-url origin 2>/dev/null) || fail "getting the repo: $dir has no origin. Use --dir to choose another location."
        [ "$(normalize_origin "$origin")" = "$(normalize_origin "$source")" ] || fail "getting the repo: the origin of $dir is not $source. Use --dir to choose another location."
        return
    fi
    say "Cloning into $dir"
    GIT_TERMINAL_PROMPT=0 git clone --quiet "$source" "$dir" || fail "getting the repo: cannot clone $source. If it is private, clone it yourself and run tools/setup.sh --dir <clone>."
}

main() {
    INSTALLED=""
    # Nothing below may read the rest of a piped script.
    exec </dev/null

    local dir="" source="${CLAUDE_DOTFILES_REPO:-https://github.com/flysangel/claude-dotfiles.git}"
    local passthrough=()
    while [ $# -gt 0 ]; do
        case "$1" in
        --dir)
            [ $# -ge 2 ] || fail "options: --dir needs a path."
            dir=$2
            shift 2
            ;;
        --email)
            [ $# -ge 2 ] || fail "options: --email needs an address."
            passthrough+=(--email "$2")
            shift 2
            ;;
        --dev | --force)
            passthrough+=("$1")
            shift
            ;;
        *)
            fail "options: unknown option $1."
            ;;
        esac
    done

    local system
    system=$(uname -s)
    if [ "$system" != "Linux" ]; then
        fail "system check: tools/setup.sh supports Linux only, found $system. On Windows use tools/setup.ps1; macOS is not supported."
    fi

    # Tools from an earlier run may be here even if this shell has not picked them up yet.
    PATH="$PATH:$HOME/.local/bin"
    export PATH
    hash -r

    check_version git 2.20
    check_version uv 0.4.0

    command -v git >/dev/null 2>&1 || install_git
    command -v uv >/dev/null 2>&1 || run_official_installer uv https://astral.sh/uv/install.sh sh https://docs.astral.sh/uv/getting-started/installation/ uv
    command -v claude >/dev/null 2>&1 || run_official_installer "Claude Code" https://claude.ai/install.sh bash https://code.claude.com/docs/en/setup claude

    dir=${dir:-$HOME/claude-dotfiles}
    case "$dir" in
    /*) ;;
    *) dir="$PWD/$dir" ;;
    esac
    ensure_clone "$dir" "$source"

    say "Running the setup in $dir"
    cd "$dir" || fail "getting the repo: cannot enter $dir."
    if [ -n "$INSTALLED" ]; then
        passthrough+=(--installed "$INSTALLED")
    fi
    uv run "$dir/tools/machine_setup.py" install "${passthrough[@]}"
}

main "$@"
