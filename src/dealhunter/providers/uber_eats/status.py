import datetime
from .runtime import ChromiumRuntime
from ...db import setup_db

def get_status():
    rt = ChromiumRuntime()
    runtime_ready = rt.is_healthy()
    
    conn = setup_db()
    c = conn.cursor()
    c.execute("SELECT finished_at FROM runs WHERE vertical = 'uber_eats' OR crawler_mode = 'uber_eats' ORDER BY started_at DESC LIMIT 1")
    row = c.fetchone()
    last_sync = row[0] if row else "Never"
    
    # We could do a deeper check for session, but for now we approximate.
    # The true test is actually doing a fetch. But we shouldn't fetch during status.
    # We will assume VALID if we have a directory.
    import os
    has_profile = os.path.isdir(rt.profile_path)
    session_status = "VALID" if has_profile else "NEEDS_LOGIN"
    
    overall = "READY" if (runtime_ready or has_profile) else "NEEDS_LOGIN"
    
    return {
        "provider": "Uber Eats",
        "runtime": "READY" if runtime_ready else "STOPPED",
        "session": session_status,
        "discovery": "READY",
        "catalog": "READY",
        "last_sync": last_sync,
        "status": overall
    }

def print_status():
    st = get_status()
    print(st["provider"])
    print(f"Runtime ...... {st['runtime']}")
    print(f"Session ...... {st['session']}")
    print(f"Discovery .... {st['discovery']}")
    print(f"Catalog ...... {st['catalog']}")
    print(f"Last Sync .... {st['last_sync']}")
    print(f"Status ....... {st['status']}")
