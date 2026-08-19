"""DealHunter Doctor — read-only system diagnostics."""

import os
import sys
import sqlite3

from .db import get_default_db_path, db_integrity
from .config import load_config, get_config_path


def run_doctor(conn=None, db_path=None):
    """Run all diagnostic checks. Returns list of (name, status, detail) tuples."""
    if db_path is None:
        db_path = get_default_db_path()

    checks = []

    # 1. Configuration
    checks.append(_check_config())

    # 2. Database existence/access
    checks.append(_check_db_access(db_path))

    # 3. SQLite integrity
    checks.append(_check_integrity(db_path))

    # 4. Schema version
    checks.append(_check_schema(db_path))

    # 5. Permissions
    checks.append(_check_permissions(db_path))

    # 6. Disk space
    checks.append(_check_disk_space(db_path))

    # 7. Last run
    checks.append(_check_last_run(db_path))

    # 8. Partial runs
    checks.append(_check_partial_runs(db_path))

    # 9. Providers (placeholder for future)
    checks.extend(_check_providers())

    return checks


def format_doctor_output(checks):
    """Format check results as human-readable text."""
    lines = ["", "DealHunter Doctor", ""]

    has_error = False
    for name, status, detail in checks:
        pad = max(1, 23 - len(name))
        line = f"  {name}{' ' * pad}{status}"
        lines.append(line)
        if status == "ERROR":
            has_error = True
            if detail:
                lines.append(f"    Reason             {detail.get('reason', 'Unknown')}")
                lines.append(f"    Action             {detail.get('action', '')}")
        elif status not in ("OK", "NOT_IMPLEMENTED", "NOT_CHECKED") and detail:
            if isinstance(detail, dict) and "info" in detail:
                lines.append(f"    Info               {detail['info']}")

    lines.append("")
    overall = "ERROR" if has_error else "HEALTHY"
    lines.append(f"  Overall              {overall}")
    lines.append("")
    return "\n".join(lines)


def _check_config():
    """Check configuration is loadable."""
    try:
        cfg = load_config()
        path = get_config_path()
        if os.path.exists(path):
            return ("Configuration", "OK", None)
        else:
            return ("Configuration", "OK", {"info": "Using defaults (no config file)"})
    except Exception as e:
        return ("Configuration", "ERROR", {
            "reason": "CONFIG_ERROR",
            "action": str(e),
        })


def _check_db_access(db_path):
    """Check database file exists and is accessible."""
    if not os.path.exists(db_path):
        return ("Database", "ERROR", {
            "reason": "DB file not found",
            "action": f"Expected at: {db_path}",
        })
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        return ("Database", "OK", None)
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return ("Database", "ERROR", {
                "reason": "DB_LOCKED",
                "action": "Close other processes using the database",
            })
        return ("Database", "ERROR", {
            "reason": str(e),
            "action": "Check database file",
        })
    except Exception as e:
        return ("Database", "ERROR", {
            "reason": str(e),
            "action": "Check database file permissions",
        })


def _check_integrity(db_path):
    """Run PRAGMA integrity_check."""
    if not os.path.exists(db_path):
        return ("SQLite integrity", "SKIP", {"info": "No database"})
    try:
        result = db_integrity(db_path)
        if result == "ok":
            return ("SQLite integrity", "OK", None)
        return ("SQLite integrity", "ERROR", {
            "reason": "DB_CORRUPT",
            "action": f"Integrity check returned: {result}",
        })
    except Exception as e:
        return ("SQLite integrity", "ERROR", {
            "reason": str(e),
            "action": "Database may be corrupt. Restore from backup.",
        })


def _check_schema(db_path):
    """Check schema_version table exists and has expected version."""
    if not os.path.exists(db_path):
        return ("Schema", "SKIP", {"info": "No database"})
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT version FROM schema_version LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            return ("Schema", "OK", {"info": f"v{row[0]}"})
        return ("Schema", "OK", {"info": "v0 (initial)"})
    except sqlite3.OperationalError:
        return ("Schema", "OK", {"info": "No schema_version table yet"})


def _check_permissions(db_path):
    """Check read/write permissions on DB file."""
    if not os.path.exists(db_path):
        # Check if parent dir is writable
        parent = os.path.dirname(db_path)
        if os.path.isdir(parent) and os.access(parent, os.W_OK):
            return ("Permissions", "OK", None)
        return ("Permissions", "ERROR", {
            "reason": "Cannot write to database directory",
            "action": f"Check permissions on: {parent}",
        })
    readable = os.access(db_path, os.R_OK)
    writable = os.access(db_path, os.W_OK)
    if readable and writable:
        return ("Permissions", "OK", None)
    return ("Permissions", "ERROR", {
        "reason": f"read={readable} write={writable}",
        "action": "Fix file permissions on database",
    })


def _check_disk_space(db_path):
    """Check basic disk space availability."""
    try:
        target_dir = os.path.dirname(db_path) if db_path else os.path.expanduser("~")
        if not os.path.isdir(target_dir):
            target_dir = os.path.expanduser("~")
        stat = os.statvfs(target_dir)
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        if free_mb < 10:
            return ("Disk space", "ERROR", {
                "reason": f"Only {free_mb:.0f} MB free",
                "action": "Free disk space",
            })
        return ("Disk space", "OK", {"info": f"{free_mb:.0f} MB free"})
    except Exception:
        return ("Disk space", "OK", {"info": "Could not check"})


def _check_last_run(db_path):
    """Check the most recent run."""
    if not os.path.exists(db_path):
        return ("Last run", "OK", {"info": "No runs yet"})
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT run_id, started_at, status FROM runs ORDER BY started_at DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if not row:
            return ("Last run", "OK", {"info": "No runs yet"})
        return ("Last run", "OK", {"info": f"{row[2]} at {row[1]}"})
    except Exception:
        return ("Last run", "OK", {"info": "Could not query runs"})


def _check_partial_runs(db_path):
    """Count runs with non-terminal status."""
    if not os.path.exists(db_path):
        return ("Partial runs", "OK", {"info": "0"})
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM runs WHERE status IN ('RUNNING', 'PARTIAL', 'PARTIAL_RUN')")
        count = c.fetchone()[0]
        conn.close()
        if count > 0:
            return ("Partial runs", "OK", {"info": str(count)})
        return ("Partial runs", "OK", {"info": "0"})
    except Exception:
        return ("Partial runs", "OK", {"info": "0"})


def _check_providers():
    """Placeholder provider checks for future implementation."""
    return [
        ("Rappi catalog", "NOT_CHECKED", None),
        ("Turbo", "AVAILABLE", None),
        ("Restaurants", "NOT_IMPLEMENTED", None),
        ("Account context", "NOT_IMPLEMENTED", None),
    ]
