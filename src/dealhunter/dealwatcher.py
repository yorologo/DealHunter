"""Evaluate the latest completed run and deliver pending DealHunter alerts."""

import argparse
import sqlite3


def build_parser():
    parser = argparse.ArgumentParser(
        description="Evaluate the latest completed DealHunter run and deliver new alerts."
    )
    parser.add_argument(
        "action", nargs="?", choices=("run",),
        help="Optional explicit action; omitting it also runs the watcher.",
    )
    return parser


def run():
    from .alerts_engine import DealWatcher
    from .db import get_default_db_path
    from .delivery import send_pending_events

    db_path = get_default_db_path()
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT run_id FROM runs "
            "WHERE status IN ('SUCCESS', 'PARTIAL', 'COMPLETED', 'COMPLETE') "
            "ORDER BY started_at DESC LIMIT 1"
        ).fetchone()

    if not row:
        print("No completed runs found.")
        return 0

    run_id = row[0]
    print(f"Processing run: {run_id}")
    watcher = DealWatcher(db_path)
    events = watcher.process_run(run_id)
    if events:
        inserted = watcher.persist_events(events)
        print(f"Inserted {inserted} new alert events.")
    else:
        print("No new events generated.")

    print("Applying Canary Watch and sending Termux notifications...")
    send_pending_events(db_path, limit=5, dry_run=False)
    print("Delivery pass completed.")
    return 0


def main(argv=None):
    build_parser().parse_args(argv)
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
