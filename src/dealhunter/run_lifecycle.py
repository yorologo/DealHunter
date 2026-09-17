"""Atomic run lifecycle helpers shared by CLI, Web and scheduled execution."""

import json
from datetime import datetime, timezone


class ActiveRunError(RuntimeError):
    pass


ACTIVE_RUN_WINDOW_HOURS = 2
_UNSET = object()


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def find_active_run(conn, exclude_run_id=None):
    """Return the newest recent RUNNING run using the reservation authority."""
    params = []
    where_exclude = ""
    if exclude_run_id is not None:
        where_exclude = "AND run_id <> ?"
        params.append(exclude_run_id)
    params.append(f"-{ACTIVE_RUN_WINDOW_HOURS} hours")
    return conn.execute(
        f"""SELECT run_id, crawler_mode, started_at
            FROM runs
            WHERE status = 'RUNNING'
              {where_exclude}
              AND datetime(started_at) >= datetime('now', ?)
            ORDER BY started_at DESC
            LIMIT 1""",
        params,
    ).fetchone()


def update_run_progress(
    conn,
    run_id,
    *,
    phase=None,
    completed=None,
    total=_UNSET,
    unit=None,
):
    """Merge a small persistent progress block into existing valid run_metadata."""
    row = conn.execute(
        "SELECT run_metadata FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        return False

    metadata = {}
    if row[0]:
        try:
            parsed = json.loads(row[0])
            if isinstance(parsed, dict):
                metadata = parsed
        except (json.JSONDecodeError, TypeError, ValueError):
            metadata = {}

    progress = metadata.get("progress")
    if not isinstance(progress, dict):
        progress = {}

    now = _utc_now()
    if phase is not None:
        if progress.get("phase") != phase:
            progress["phase_started_at"] = now
        progress["phase"] = str(phase)
    if completed is not None:
        progress["completed"] = max(0, int(completed))
    if total is not _UNSET:
        progress["total"] = None if total is None else max(0, int(total))
    if unit is not None:
        progress["unit"] = str(unit)
    progress["updated_at"] = now

    metadata["progress"] = progress
    conn.execute(
        "UPDATE runs SET run_metadata = ? WHERE run_id = ?",
        (json.dumps(metadata, separators=(",", ":")), run_id),
    )
    conn.commit()
    return True


def reserve_run(conn, run_id, *, lat, lng, radius, vertical="general", source="CLI", allow_existing=False):
    """Atomically reserve one recent RUNNING slot.

    Web may reserve a run before spawning the CLI; the child can adopt only its
    own existing RUNNING reservation when allow_existing is true.
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        other = find_active_run(conn, exclude_run_id=run_id)
        if other:
            raise ActiveRunError(f"another crawler run is active: {other[0]}")

        current = conn.execute(
            "SELECT status FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if current:
            if allow_existing and current[0] == "RUNNING":
                conn.commit()
                return False
            raise ActiveRunError(f"run_id already exists: {run_id}")

        now = _utc_now()
        metadata = json.dumps(
            {
                "progress": {
                    "phase": "STARTING",
                    "completed": 0,
                    "total": None,
                    "unit": None,
                    "updated_at": now,
                    "phase_started_at": now,
                }
            },
            separators=(",", ":"),
        )
        conn.execute(
            """INSERT INTO runs
               (run_id, started_at, lat, lng, radius, vertical, status, source, run_metadata)
               VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, 'RUNNING', ?, ?)""",
            (run_id, lat, lng, radius, str(vertical), source, metadata),
        )
        conn.commit()
        return True
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
