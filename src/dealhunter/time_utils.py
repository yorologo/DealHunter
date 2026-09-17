"""Canonical time helpers for persisted DealHunter timestamps."""
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return an explicit RFC 3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
