"""Atomic run reservation shared by CLI, Web and scheduled execution."""


class ActiveRunError(RuntimeError):
    pass


def reserve_run(conn, run_id, *, lat, lng, radius, vertical="general", source="CLI", allow_existing=False):
    """Atomically reserve one recent RUNNING slot.

    Web may reserve a run before spawning the CLI; the child then calls this with
    ``allow_existing=True`` and adopts only its own RUNNING reservation.
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        other = conn.execute(
            """SELECT run_id FROM runs
               WHERE status = 'RUNNING'
                 AND run_id <> ?
                 AND datetime(started_at) >= datetime('now', '-2 hours')
               ORDER BY started_at DESC LIMIT 1""",
            (run_id,),
        ).fetchone()
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

        conn.execute(
            """INSERT INTO runs
               (run_id, started_at, lat, lng, radius, vertical, status, source)
               VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, 'RUNNING', ?)""",
            (run_id, lat, lng, radius, str(vertical), source),
        )
        conn.commit()
        return True
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
