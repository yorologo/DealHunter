import datetime
import os
from .runtime import ChromiumRuntime
from ...db import setup_db

# Provider health states
READY = "READY"
NEEDS_LOGIN = "NEEDS_LOGIN"
NEEDS_LOCATION = "NEEDS_LOCATION"
STALE = "STALE"
RUNTIME_ERROR = "RUNTIME_ERROR"
DISABLED = "DISABLED"
RUNTIME_STOPPED = "RUNTIME_STOPPED"


def get_status():
    """Get current Uber Eats provider health status.

    Distinguishes between runtime availability, session validity,
    and overall operational readiness. Does not make network requests.
    """
    rt = ChromiumRuntime()
    runtime_ready = rt.is_healthy()

    # Check profile existence (necessary but not sufficient for session)
    has_profile = os.path.isdir(rt.profile_path)

    # Session: profile existence is a weak signal. Real check requires network.
    if not has_profile:
        session_status = NEEDS_LOGIN
    else:
        session_status = "CONFIGURED"  # Profile exists, but validity unknown without network

    # Runtime status
    if not runtime_ready:
        runtime_status = RUNTIME_STOPPED
    else:
        runtime_status = READY

    # Last sync from runs table
    last_sync = "Never"
    last_sync_age_hours = None
    try:
        conn = setup_db()
        c = conn.cursor()
        # Provider is part of the current raw identity contract.
        c.execute("""SELECT finished_at FROM runs
                     WHERE run_id IN (
                         SELECT DISTINCT run_id FROM trusted_observations WHERE provider = 'uber_eats'
                     ) ORDER BY finished_at DESC LIMIT 1""")
        row = c.fetchone()
        if row and row[0]:
            last_sync = row[0]
            try:
                last_dt = datetime.datetime.fromisoformat(last_sync)
                age = datetime.datetime.now() - last_dt
                last_sync_age_hours = age.total_seconds() / 3600
            except (ValueError, TypeError):
                pass
        conn.close()
    except Exception:
        pass

    # Staleness check
    if last_sync_age_hours is not None and last_sync_age_hours > 48:
        data_status = STALE
    elif last_sync == "Never":
        data_status = "NO_DATA"
    else:
        data_status = "CURRENT"

    # Overall status: requires runtime AND session
    if not runtime_ready and not has_profile:
        overall = DISABLED
    elif not runtime_ready:
        overall = RUNTIME_STOPPED
    elif not has_profile:
        overall = NEEDS_LOGIN
    else:
        overall = READY

    return {
        "provider": "Uber Eats",
        "runtime": runtime_status,
        "session": session_status,
        "discovery": "GROCERY_RESTAURANT",
        "catalog": "AVAILABLE" if runtime_ready else RUNTIME_STOPPED,
        "last_sync": last_sync,
        "last_sync_age_hours": last_sync_age_hours,
        "data_status": data_status,
        "status": overall,
    }


def print_status():
    st = get_status()
    print(st["provider"])
    print(f"Runtime ...... {st['runtime']}")
    print(f"Session ...... {st['session']}")
    print(f"Discovery .... {st['discovery']}")
    print(f"Catalog ...... {st['catalog']}")
    print(f"Data ......... {st['data_status']}")
    print(f"Last Sync .... {st['last_sync']}")
    age = st.get('last_sync_age_hours')
    if age is not None:
        print(f"  Age ........ {age:.1f}h")
    print(f"Status ....... {st['status']}")
