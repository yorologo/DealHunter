import asyncio
import datetime
import os
import sqlite3

from ...db import get_default_db_path, read_connection
from .browser_transport import (
    CHALLENGE_REQUIRED,
    LOGIN_REQUIRED,
    READY as TRANSPORT_READY,
    UberBrowserTransport,
)
from .runtime import ChromiumRuntime

READY = "READY"
VALID = "VALID"
NEEDS_LOGIN = "NEEDS_LOGIN"
UNVERIFIED = "UNVERIFIED"
STALE = "STALE"
RUNTIME_ERROR = "RUNTIME_ERROR"
RUNTIME_STOPPED = "RUNTIME_STOPPED"
NO_DATA = "NO_DATA"
CURRENT = "CURRENT"
PROFILE_CONFIGURED = "CONFIGURED"
PROFILE_NOT_CONFIGURED = "NOT_CONFIGURED"


def session_status_from_transport(transport_state):
    """Map browser transport readiness to the canonical Uber session state."""
    if transport_state == TRANSPORT_READY:
        return VALID
    if transport_state == LOGIN_REQUIRED:
        return NEEDS_LOGIN
    if transport_state == CHALLENGE_REQUIRED:
        return UNVERIFIED
    return UNVERIFIED


def _last_sync_status(db_path):
    """Read Uber sync age without creating or migrating SQLite."""
    if not db_path or not os.path.exists(db_path):
        return "Never", None, NO_DATA

    try:
        with read_connection(db_path) as conn:
            row = conn.execute(
                """SELECT r.finished_at
                   FROM runs r
                   WHERE r.finished_at IS NOT NULL
                     AND EXISTS (
                         SELECT 1 FROM trusted_observations o
                         WHERE o.run_id = r.run_id AND o.provider = 'uber_eats'
                     )
                   ORDER BY r.finished_at DESC
                   LIMIT 1"""
            ).fetchone()
    except (sqlite3.Error, OSError):
        return "Never", None, NO_DATA

    if not row or not row[0]:
        return "Never", None, NO_DATA

    last_sync = row[0]
    age_hours = None
    try:
        last_dt = datetime.datetime.fromisoformat(str(last_sync).replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        age_hours = max(
            0.0,
            (now - last_dt.astimezone(datetime.timezone.utc)).total_seconds() / 3600,
        )
    except (ValueError, TypeError, OverflowError):
        pass

    return last_sync, age_hours, (STALE if age_hours is not None and age_hours > 48 else CURRENT)


async def _check_transport_session():
    transport = UberBrowserTransport()
    try:
        return session_status_from_transport(await transport.ensure_ready())
    finally:
        try:
            await transport.close()
        except Exception:
            pass


def get_status(check_network=False, db_path=None):
    """Return canonical Uber Eats provider status.

    Local diagnostics are side-effect free and perform no HTTP/CDP requests.
    A real session validation occurs only when ``check_network=True``.
    """
    rt = ChromiumRuntime()
    has_profile = os.path.isdir(rt.profile_path)
    runtime_running = rt.is_running_local()
    last_sync, last_sync_age_hours, data_status = _last_sync_status(
        db_path or get_default_db_path()
    )

    result = {
        "provider": "Uber Eats",
        "profile": PROFILE_CONFIGURED if has_profile else PROFILE_NOT_CONFIGURED,
        "runtime": READY if runtime_running else RUNTIME_STOPPED,
        "session": NEEDS_LOGIN if not has_profile else UNVERIFIED,
        "discovery": "GROCERY_RESTAURANT",
        "catalog": UNVERIFIED if has_profile else NEEDS_LOGIN,
        "last_sync": last_sync,
        "last_sync_age_hours": last_sync_age_hours,
        "data_status": data_status,
        "status": NEEDS_LOGIN if not has_profile else UNVERIFIED,
        "checked_network": False,
    }

    if not check_network or not has_profile:
        return result

    result["checked_network"] = True
    started_here = not runtime_running
    if started_here:
        try:
            rt.start()
        except Exception:
            result["runtime"] = RUNTIME_ERROR
            result["session"] = UNVERIFIED
            result["status"] = RUNTIME_ERROR
            result["catalog"] = UNVERIFIED
            try:
                rt.stop()
            except Exception:
                pass
            return result

    try:
        session = asyncio.run(_check_transport_session())
        result["session"] = session
        if session == VALID:
            result["status"] = READY
            result["catalog"] = "AVAILABLE"
        elif session == NEEDS_LOGIN:
            result["status"] = NEEDS_LOGIN
            result["catalog"] = NEEDS_LOGIN
        else:
            result["status"] = UNVERIFIED
            result["catalog"] = UNVERIFIED
    except Exception:
        result["session"] = UNVERIFIED
        result["status"] = UNVERIFIED
        result["catalog"] = UNVERIFIED
    finally:
        if started_here:
            try:
                rt.stop()
            finally:
                result["runtime"] = RUNTIME_STOPPED
        else:
            result["runtime"] = READY

    return result


def print_status(check_network=False):
    st = get_status(check_network=check_network)
    print(st["provider"])
    print(f"Runtime ...... {st['runtime']}")
    print(f"Profile ...... {st['profile']}")
    print(f"Session ...... {st['session']}")
    print(f"Discovery .... {st['discovery']}")
    print(f"Catalog ...... {st['catalog']}")
    print(f"Data ......... {st['data_status']}")
    print(f"Last Sync .... {st['last_sync']}")
    age = st.get("last_sync_age_hours")
    if age is not None:
        print(f"  Age ........ {age:.1f}h")
    print(f"Status ....... {st['status']}")
