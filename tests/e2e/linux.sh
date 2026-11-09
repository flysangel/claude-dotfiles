#!/usr/bin/env bash
# E2E driver for Linux. It really installs tools and changes the home directory, so it only runs inside
# a throwaway container, started by prepare.sh. Contract: specs/004-ci-e2e-tests/contracts/e2e-driver.md
set -u

ENVIRONMENT=$1
HERE=$(cd "$(dirname "$0")" && pwd)
EMAIL="12345+e2e@users.noreply.github.com"
CLONE="$HOME/claude-dotfiles"
LOG=$(mktemp)
BROKEN=""
FAILED=0
export PATH="$PATH:$HOME/.local/bin"

if [ -z "${E2E_SETUP_URL:-}" ]; then
    # A read-only mount may belong to another user, and git refuses to read those.
    cp -r "$2" "$HOME/e2e-source.git"
    export CLAUDE_DOTFILES_REPO="$HOME/e2e-source.git"
fi

report() {
    printf 'E2E %s %s %s %s\n' "$ENVIRONMENT" "$1" "$2" "$3"
    if [ "$2" = "FAIL" ]; then
        FAILED=1
        BROKEN=$1
    fi
}

run_setup() {
    if [ -n "${E2E_SETUP_URL:-}" ]; then
        curl -fsSL "$E2E_SETUP_URL" | bash -s -- "$@" >"$LOG" 2>&1
        status=${PIPESTATUS[1]}
    else
        bash -s -- "$@" <"$HERE/setup.sh" >"$LOG" 2>&1
        status=$?
    fi
    cat "$LOG"
    return "$status"
}

managed_hash() {
    (cd "$HOME/.claude" && find CLAUDE.md rules skills .dotfiles -type f 2>/dev/null | sort | xargs sha256sum)
}

clone_hash() {
    (cd "$CLONE" && find . -type f -not -path './.git/*' -not -name '*.pyc' | sort | xargs sha256sum)
}

record() {
    cat "$HOME/.config/claude-dotfiles/setup.json" 2>/dev/null
}

stage_setup() {
    local attempt failure
    for attempt in 1 2; do
        if run_setup; then
            break
        fi
        failure=$(grep -E 'cannot download|apt-get failed|dnf failed|pacman failed' "$LOG" | head -1)
        if [ -z "$failure" ]; then
            report setup FAIL "the setup failed, see the output above"
            return
        fi
        if [ "$attempt" = 2 ]; then
            report setup FAIL "download failed after a retry: $failure"
            return
        fi
    done
    for tool in uv git claude; do
        command -v "$tool" >/dev/null 2>&1 || {
            report setup FAIL "$tool is not available after the setup"
            return
        }
    done
    if [ "${ENVIRONMENT%-public}" != "minimum" ]; then
        for tool in uv git claude; do
            record | grep -q "\"$tool\"" || {
                report setup FAIL "$tool was already there, so this run did not install it"
                return
            }
        done
    elif [ "$(record | grep -c -E '"(uv|git|claude)"')" != "0" ]; then
        report setup FAIL "the minimum environment should not install anything"
        return
    fi
    local state
    state=$(cd "$CLONE" && uv run tools/dotfiles.py status 2>/dev/null | head -1)
    if [ "$state" != "clean" ]; then
        report setup FAIL "deployment status is $state"
        return
    fi
    report setup PASS "tools available and deployment clean"
}

stage_rerun() {
    local before after
    before=$(managed_hash; clone_hash)
    if ! run_setup; then
        report rerun FAIL "the second run failed"
        return
    fi
    after=$(managed_hash; clone_hash)
    if [ "$before" != "$after" ]; then
        report rerun FAIL "the second run changed files"
        return
    fi
    report rerun PASS "nothing changed"
}

stage_dev() {
    if ! run_setup --dev --email "$EMAIL"; then
        report dev FAIL "dev setup failed"
        return
    fi
    local state
    state=$(cd "$CLONE" && uv run tools/repo_guard.py --status 2>/dev/null | head -1)
    if [ "$state" != "enabled" ]; then
        report dev FAIL "commit guard is $state"
        return
    fi
    if git config --global --get user.email >/dev/null; then
        report dev FAIL "the global email was changed"
        return
    fi
    git -C "$CLONE" config user.name "E2E Tester"
    echo "# e2e" >>"$CLONE/README.md"
    git -C "$CLONE" add README.md
    if ! git -C "$CLONE" commit -q -m "test: e2e commit"; then
        report dev FAIL "a real commit failed"
        return
    fi
    report dev PASS "guard enabled and a real commit worked"
}

stage_remove() {
    if ! uv run "$CLONE/tools/machine_setup.py" remove; then
        report remove FAIL "remove failed"
        return
    fi
    if [ "$(cat "$HOME/.claude/CLAUDE.md")" != "mine" ] || [ "$(cat "$HOME/.claude/rules/machine.md")" != "local" ]; then
        report remove FAIL "the original files did not come back"
        return
    fi
    if [ -e "$CLONE/.git/hooks/pre-commit" ]; then
        report remove FAIL "the hook is still installed"
        return
    fi
    if [ -e "$HOME/.config/claude-dotfiles/setup.json" ]; then
        report remove FAIL "the setup record is still there"
        return
    fi
    if [ ! -d "$CLONE" ] || ! command -v uv >/dev/null 2>&1; then
        report remove FAIL "the clone or the tools were removed"
        return
    fi
    report remove PASS "original files back, tools and clone kept"
}

stage_refuse() {
    local plain="$HOME/not-this-repo" marker="$HOME/refuse-marker"
    mkdir -p "$plain/tools"
    printf 'open(r"%s", "w").close()\n' "$marker" >"$plain/tools/machine_setup.py"
    if run_setup --dir "$plain"; then
        report refuse FAIL "the setup accepted a directory that is not this repo"
        return
    fi
    if [ -e "$marker" ]; then
        report refuse FAIL "code inside the directory ran"
        return
    fi
    report refuse PASS "stopped without running anything"
}

mkdir -p "$HOME/.claude/rules"
echo mine >"$HOME/.claude/CLAUDE.md"
echo local >"$HOME/.claude/rules/machine.md"

for stage in setup rerun dev remove refuse; do
    if [ -n "$BROKEN" ]; then
        report "$stage" FAIL "previous stage failed"
        continue
    fi
    printf '::group::%s\n' "$stage"
    "stage_$stage"
    printf '::endgroup::\n'
done
exit "$FAILED"
