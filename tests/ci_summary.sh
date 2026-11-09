#!/usr/bin/env bash
# Add a unittest -v log to the GitHub job summary: counts, failed tests, and every skipped test.
title=$1
log=$2
{
    printf '### %s\n\n' "$title"
    if [ ! -f "$log" ]; then
        printf 'No test output was produced.\n'
        exit 0
    fi
    printf '```text\n'
    grep -E '^(Ran [0-9]+ tests? in|OK|FAILED)' "$log"
    printf '```\n\n'
    printf 'Failed tests:\n\n'
    grep -E '^(FAIL|ERROR): ' "$log" | sed 's/^/- /'
    printf '\nSkipped tests: %s\n\n' "$(grep -cE ' \.\.\. skipped ' "$log")"
    grep -E ' \.\.\. skipped ' "$log" | sed 's/^/- /'
    printf '\n'
} >>"${GITHUB_STEP_SUMMARY:-/dev/stdout}"
