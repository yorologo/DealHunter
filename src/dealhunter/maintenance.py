"""Bounded operational retention for DealHunter-owned runtime artifacts.

Commercial SQLite history is intentionally out of scope: maintenance never opens
or deletes observations.
"""

import os
import time
from pathlib import Path

from .scheduler import LOG_FILE

DEFAULT_LOG_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_LOG_BACKUPS = 3
DEFAULT_DIAGNOSTIC_DAYS = 14


def get_state_dir() -> Path:
    root = os.environ.get("XDG_STATE_HOME")
    if root:
        return Path(root).expanduser() / "dealhunter"
    return Path(os.path.expanduser("~/.local/state")) / "dealhunter"


def get_diagnostics_dir() -> Path:
    return get_state_dir() / "diagnostics"


def rotate_file(path, *, max_bytes=DEFAULT_LOG_MAX_BYTES, keep=DEFAULT_LOG_BACKUPS) -> bool:
    path = Path(path)
    if max_bytes < 1 or keep < 1:
        raise ValueError("max_bytes and keep must be positive")
    try:
        if not path.is_file() or path.stat().st_size <= max_bytes:
            return False
    except OSError:
        raise

    path.parent.mkdir(parents=True, exist_ok=True)
    oldest = path.with_name(f"{path.name}.{keep}")
    if oldest.exists():
        oldest.unlink()
    for index in range(keep - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        if source.exists():
            os.replace(source, path.with_name(f"{path.name}.{index + 1}"))
    os.replace(path, path.with_name(f"{path.name}.1"))
    path.touch(mode=0o600)
    os.chmod(path, 0o600)
    return True


def cleanup_diagnostics(directory=None, *, max_age_days=DEFAULT_DIAGNOSTIC_DAYS, now=None):
    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    directory = Path(directory) if directory is not None else get_diagnostics_dir()
    if not directory.exists():
        return []
    cutoff = (time.time() if now is None else float(now)) - (max_age_days * 86400)
    removed = []
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path.name)
    return sorted(removed)


def run_maintenance(*, log_file=None, diagnostics_dir=None, max_log_bytes=DEFAULT_LOG_MAX_BYTES, keep_logs=DEFAULT_LOG_BACKUPS, diagnostic_days=DEFAULT_DIAGNOSTIC_DAYS):
    target_log = Path(log_file) if log_file is not None else LOG_FILE
    return {
        "log_rotated": rotate_file(target_log, max_bytes=max_log_bytes, keep=keep_logs),
        "diagnostics_removed": cleanup_diagnostics(diagnostics_dir, max_age_days=diagnostic_days),
        "commercial_history": "preserved",
    }
