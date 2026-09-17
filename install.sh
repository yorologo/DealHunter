#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

say() { printf '[DealHunter] %s\n' "$*"; }
fail() { printf '[DealHunter] ERROR: %s\n' "$*" >&2; exit 1; }

if [ "${PREFIX:-}" = "/data/data/com.termux/files/usr" ]; then
    command -v pkg >/dev/null 2>&1 || fail "Termux package manager (pkg) not found"
    missing=()
    command -v git >/dev/null 2>&1 || missing+=(git)
    command -v python >/dev/null 2>&1 || missing+=(python)
    command -v flock >/dev/null 2>&1 || missing+=(util-linux)
    command -v crontab >/dev/null 2>&1 || missing+=(cronie)
    if ! python -c 'from cryptography.fernet import Fernet' >/dev/null 2>&1; then
        missing+=(python-cryptography)
    fi
    if ((${#missing[@]})); then
        say "Installing missing Termux packages: ${missing[*]}"
        pkg install -y "${missing[@]}"
    fi
    PYTHON=python
else
    PYTHON="${PYTHON:-python3}"
    command -v "$PYTHON" >/dev/null 2>&1 || fail "Python 3.11+ is required"
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        fail "Outside Termux, run this installer inside a Python virtual environment"
    fi
fi

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"Python 3.11+ required; found {sys.version.split()[0]}")
PY

say "Installing DealHunter from this checkout"
"$PYTHON" -m pip install .

command -v dealhunter >/dev/null 2>&1 || fail "dealhunter console command was not installed on PATH"
dealhunter --help >/dev/null
"$PYTHON" -c 'from cryptography.fernet import Fernet' >/dev/null
dealhunter doctor >/dev/null

say "Installed successfully"
say "Next: dealhunter web"
say "Before the first sync, set delivery lat/lng in Web → Admin → Settings (or with dealhunter config set)."
