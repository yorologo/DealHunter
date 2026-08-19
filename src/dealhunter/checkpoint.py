"""Minimal checkpoint model for DealHunter crawl progress.

This module provides the data model for tracking crawl progress.
It does NOT implement automatic resume — only stores enough state
to support future resumption.
"""

import json
from datetime import datetime


class RunCheckpoint:
    """Tracks crawl progress for a single run."""

    def __init__(self, run_id, mode="discover", current_vertical=None,
                 last_completed_query=None, status="RUNNING",
                 queries_completed=0, requests_made=0, error_code=None,
                 updated_at=None):
        self.run_id = run_id
        self.mode = mode
        self.current_vertical = current_vertical
        self.last_completed_query = last_completed_query
        self.status = status
        self.queries_completed = queries_completed
        self.requests_made = requests_made
        self.error_code = error_code
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "current_vertical": self.current_vertical,
            "last_completed_query": self.last_completed_query,
            "status": self.status,
            "queries_completed": self.queries_completed,
            "requests_made": self.requests_made,
            "error_code": self.error_code,
            "updated_at": self.updated_at,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__init__.__code__.co_varnames})


def save_checkpoint(conn, checkpoint):
    """Save checkpoint progress to the runs table.

    Stores checkpoint JSON in the 'vertical' column (TEXT) and
    updates the run status.
    """
    c = conn.cursor()
    c.execute(
        "UPDATE runs SET status = ?, vertical = ? WHERE run_id = ?",
        (checkpoint.status, checkpoint.to_json(), checkpoint.run_id),
    )
    conn.commit()


def load_checkpoint(conn, run_id):
    """Load checkpoint from the runs table. Returns RunCheckpoint or None."""
    c = conn.cursor()
    c.execute("SELECT vertical, status FROM runs WHERE run_id = ?", (run_id,))
    row = c.fetchone()
    if not row or not row[0]:
        return None
    try:
        data = json.loads(row[0])
        return RunCheckpoint.from_dict(data)
    except (json.JSONDecodeError, TypeError):
        return None
