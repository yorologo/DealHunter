"""Admin queries for DealHunter web administration."""

import sqlite3
import json
import math
from datetime import datetime, timezone


def get_runs_paginated(db_path, page=1, per_page=20, status_filter=None):
    """Get paginated runs from the database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    offset = (page - 1) * per_page

    # Build WHERE clause
    where = ""
    params = []
    if status_filter and status_filter in ('COMPLETED', 'PARTIAL', 'PARTIAL_RUN', 'FAILED', 'RUNNING'):
        where = "WHERE status = ?"
        params.append(status_filter)

    # Get total
    c.execute(f"SELECT COUNT(*) FROM runs {where}", params)
    total = c.fetchone()[0]
    total_pages = max(1, math.ceil(total / per_page))

    # Get paginated runs
    c.execute(
        f"SELECT run_id, started_at, finished_at, status, vertical "
        f"FROM runs {where} ORDER BY started_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    )
    rows = c.fetchall()
    conn.close()

    runs = []
    for r in rows:
        run = dict(r)
        # Calculate duration
        run['duration'] = _calc_duration(run.get('started_at'), run.get('finished_at'))
        # Parse vertical for summary info
        run['vertical_name'] = _parse_vertical_name(run.get('vertical'))
        # Convert to local time for display
        # (Handled by frontend)
        runs.append(run)

    return runs, total_pages, total


def get_run_detail(db_path, run_id):
    """Get detailed run information including observation counts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None

    run = dict(row)

    # Calculate duration
    run['duration'] = _calc_duration(run.get('started_at'), run.get('finished_at'))

    # Count observations for this run
    c.execute("SELECT COUNT(*) FROM observations WHERE run_id = ?", (run_id,))
    run['observation_count'] = c.fetchone()[0]

    # Count distinct products
    c.execute("SELECT COUNT(DISTINCT product_id) FROM observations WHERE run_id = ?", (run_id,))
    run['product_count'] = c.fetchone()[0]

    # Count distinct stores
    c.execute("SELECT COUNT(DISTINCT store_id) FROM observations WHERE run_id = ?", (run_id,))
    run['store_count'] = c.fetchone()[0]

    # Convert times to local for display
    # (Handled by frontend)

    # Parse vertical data
    if run.get('vertical'):
        try:
            run['vertical_data'] = json.loads(run['vertical'])
        except (json.JSONDecodeError, TypeError):
            run['vertical_data'] = None
    else:
        run['vertical_data'] = None

    conn.close()
    return run


def get_events(db_path, page=1, per_page=50):
    """Get structured events from runs with problems."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Count total
    c.execute("SELECT COUNT(*) FROM runs WHERE status IN ('FAILED', 'PARTIAL', 'PARTIAL_RUN')")
    total = c.fetchone()[0]
    total_pages = max(1, math.ceil(total / per_page))
    offset = (page - 1) * per_page

    c.execute(
        "SELECT run_id, started_at, finished_at, status, vertical "
        "FROM runs WHERE status IN ('FAILED', 'PARTIAL', 'PARTIAL_RUN') "
        "ORDER BY started_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    )
    rows = c.fetchall()
    conn.close()

    events = []
    for r in rows:
        run_id = r['run_id']
        started_at = r['started_at']
        status = r['status']
        error_code = "UNKNOWN"
        component = "crawler"
        message = ""

        # Try to extract structured error info from vertical JSON
        try:
            data = json.loads(r['vertical']) if r['vertical'] else None
            if data and isinstance(data, dict):
                error_code = data.get('error_code', data.get('error', 'UNKNOWN'))
                component = data.get('component', data.get('vertical', 'crawler'))
                message = data.get('message', data.get('error_message', ''))
        except (json.JSONDecodeError, TypeError):
            pass

        # Map status to severity
        severity = "ERROR" if status == "FAILED" else "WARNING"

        events.append({
            "run_id": run_id,
            "started_at": started_at,
            "status": status,
            "severity": severity,
            "error_code": error_code,
            "component": component,
            "message": message,
            "duration": _calc_duration(started_at, r['finished_at']),
        })

    return events, total_pages, total


def get_run_status_summary(db_path):
    """Get summary counts by run status."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        SELECT status, COUNT(*) as cnt
        FROM runs
        GROUP BY status
    """)
    rows = c.fetchall()
    conn.close()

    summary = {}
    for status, cnt in rows:
        summary[status or 'UNKNOWN'] = cnt
    return summary


def get_db_extended_stats(db_path):
    """Get extended database statistics for admin view."""
    import os
    from dealhunter.db import db_status

    stats = db_status(db_path)
    if stats.get('error'):
        return stats

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Alerts count
    try:
        c.execute("SELECT COUNT(*) FROM alerts")
        stats['alerts'] = c.fetchone()[0]
    except sqlite3.OperationalError:
        stats['alerts'] = 0

    # Last observation timestamp
    try:
        c.execute("SELECT MAX(timestamp) FROM observations")
        stats['last_observation'] = c.fetchone()[0]
    except sqlite3.OperationalError:
        stats['last_observation'] = None

    # Schema info
    try:
        tables = []
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for row in c.fetchall():
            name = row[0]
            try:
                c.execute(f"SELECT COUNT(*) FROM [{name}]")
                count = c.fetchone()[0]
            except sqlite3.OperationalError:
                count = 0
            tables.append({"name": name, "rows": count})
        stats['tables'] = tables
    except sqlite3.OperationalError:
        stats['tables'] = []

    conn.close()
    return stats


def _calc_duration(started_at, finished_at):
    """Calculate human-readable duration between timestamps."""
    if not started_at or not finished_at:
        return None
    try:
        start = datetime.fromisoformat(str(started_at).replace("Z", ""))
        end = datetime.fromisoformat(str(finished_at).replace("Z", ""))
        delta = end - start
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return None
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes < 60:
            return f"{minutes}m {seconds}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"
    except (ValueError, TypeError):
        return None


def _parse_vertical_name(vertical_json):
    """Extract vertical name from JSON if available."""
    if not vertical_json:
        return None
    try:
        data = json.loads(vertical_json)
        if isinstance(data, dict):
            return data.get('vertical', data.get('type', None))
        return None
    except (json.JSONDecodeError, TypeError):
        return vertical_json if isinstance(vertical_json, str) and len(vertical_json) < 30 else None


def _utc_to_local_str(timestamp_str):
    """Pass through timestamp string for frontend to parse as UTC."""
    return timestamp_str
