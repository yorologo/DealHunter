#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

say() { printf '[DealHunter] %s\n' "$*"; }
fail() { printf '[DealHunter] ERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || fail "git is required"
[ "$(git branch --show-current)" = "main" ] || fail "update.sh is for release installs on branch main; developers should update their branch with Git"
[ -z "$(git status --porcelain)" ] || fail "working tree is not clean; commit/stash/remove local changes before updating"

old_sha="$(git rev-parse HEAD)"
backup=""
recovery_hint() {
    printf '[DealHunter] Previous checkout: %s\n' "$old_sha" >&2
    printf '[DealHunter] Temporary code rollback: git switch --detach %s && ./install.sh\n' "$old_sha" >&2
    printf '[DealHunter] Return to the release branch later with: git switch main\n' >&2
    [ -z "$backup" ] || printf '[DealHunter] Pre-update %s\n' "$backup" >&2
}

if command -v dealhunter >/dev/null 2>&1; then
    backup="$(dealhunter db backup)"
    [ -z "$backup" ] || say "$backup"
fi

say "Fetching origin/main"
git fetch --tags origin main
git merge-base --is-ancestor HEAD origin/main || fail "local main is not an ancestor of origin/main; refusing a non-fast-forward update"

new_sha="$(git rev-parse origin/main)"
if [ "$old_sha" != "$new_sha" ]; then
    git merge --ff-only origin/main
else
    say "Checkout is already current"
fi

if ! ./install.sh; then
    printf '[DealHunter] Update install failed.\n' >&2
    recovery_hint
    exit 1
fi

integrity="$(dealhunter db integrity 2>/dev/null || true)"
case "$integrity" in
    ok|not_initialized) ;;
    *)
        printf '[DealHunter] ERROR: SQLite integrity check failed after update: %s\n' "${integrity:-no result}" >&2
        recovery_hint
        exit 1
        ;;
esac
if ! dealhunter doctor >/dev/null; then
    printf '[DealHunter] ERROR: Doctor reported a post-update problem.\n' >&2
    recovery_hint
    exit 1
fi
say "Update complete: $(git rev-parse --short HEAD)"
