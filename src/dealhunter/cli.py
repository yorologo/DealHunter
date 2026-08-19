import argparse
import sys
from .config import get_merged_config, save_config, load_config
from .db import setup_db, db_status, db_integrity, db_vacuum, backup_db
from .crawler import run_discover, run_update
from .historico import analyze_history, compare_stores
from .output import print_results
from .doctor import run_doctor, format_doctor_output
from datetime import datetime

VERSION = "2.2.0"

def build_parser():
    # Base parser for shared arguments
    base_parser = argparse.ArgumentParser(add_help=False)
    
    # Configuration
    group_config = base_parser.add_argument_group("Configuration")
    group_config.add_argument('--profile', type=str, help="Use specific configuration profile")
    group_config.add_argument('--show-config', action='store_true', help="Show merged config and exit")
    
    # Location
    group_loc = base_parser.add_argument_group("Location")
    group_loc.add_argument('--lat', type=float, help="Latitude")
    group_loc.add_argument('--lng', type=float, help="Longitude")
    
    # Search
    group_search = base_parser.add_argument_group("Search")
    group_search.add_argument('--query', action='append', help="Specific product query")
    group_search.add_argument('--vertical', action='append', help="Specific vertical to search")
    group_search.add_argument('--exclude-vertical', action='append', help="Exclude vertical")
    
    # Filters
    group_filters = base_parser.add_argument_group("Filters")
    group_filters.add_argument('--min-discount', type=float, help="Minimum effective discount")
    group_filters.add_argument('--max-discount', type=float, help="Maximum effective discount")
    group_filters.add_argument('--min-price', type=float, help="Minimum price")
    group_filters.add_argument('--max-price', type=float, help="Maximum price")
    group_filters.add_argument('--store', action='append', help="Include only specific stores")
    group_filters.add_argument('--exclude-store', action='append', help="Exclude specific stores")
    group_filters.add_argument('--exclude', action='append', help="Exclude queries/brands")
    
    # Promotions
    group_promo = base_parser.add_argument_group("Promotions")
    group_promo.add_argument('--promo', action='append', help="Filter by promo type (price, bundle, NxM)")
    group_promo.add_argument('--only-nxm', action='store_true', help="Only show NxM promos")
    group_promo.add_argument('--min-promo-discount', type=float, help="Min discount only for promos")
    
    # Historical
    group_hist = base_parser.add_argument_group("Historical")
    group_hist.add_argument('--status', action='append', help="Filter by status (GOOD_DEAL, NEW_LOW...)")
    group_hist.add_argument('--historical-discount', type=float, help="Min historical discount")
    group_hist.add_argument('--min-observations', type=int, help="Min observations in history")
    group_hist.add_argument('--history-days', type=float, help="Days of history required")
    group_hist.add_argument('--new-low', action='store_true', help="Only new lows")
    group_hist.add_argument('--price-drop', type=float, help="Minimum price drop vs last observation")
    group_hist.add_argument('--new-deals', action='store_true', help="Products that became deals recently")
    group_hist.add_argument('--price-changes', action='store_true', help="Only products with changed price")
    
    # Crawler Control
    group_crawler = base_parser.add_argument_group("Crawler Control")
    group_crawler.add_argument('--dry-run', action='store_true', help="Do not execute requests")
    group_crawler.add_argument('--max-requests', type=int, help="Stop after N requests")
    group_crawler.add_argument('--max-runtime', type=int, help="Stop after N seconds")
    
    # Output
    group_out = base_parser.add_argument_group("Output")
    group_out.add_argument('--top', type=int, help="Limit number of results")
    group_out.add_argument('--sort', choices=['discount', 'price', 'store', 'name', 'deal-score', 'historical-discount'], help="Sort order")
    group_out.add_argument('--desc', action='store_true', default=True, help="Sort descending")
    group_out.add_argument('--asc', action='store_false', dest='desc', help="Sort ascending")
    group_out.add_argument('--format', choices=['table', 'json', 'csv', 'markdown'], help="Output format")
    group_out.add_argument('--output', type=str, help="Output file")
    group_out.add_argument('--compact', action='store_true', help="Compact output format")
    
    parser = argparse.ArgumentParser(description=f"DealHunter CLI v{VERSION}", parents=[base_parser])
    subparsers = parser.add_subparsers(dest="command", title="Subcommands", description="Available commands")
    
    # Subcommands
    config_p = subparsers.add_parser("config", help="Manage configuration")
    config_p.add_argument("action", choices=["show", "get", "set", "unset", "reset"])
    config_p.add_argument("key", nargs="?")
    config_p.add_argument("value", nargs="?")

    discover_p = subparsers.add_parser("discover", help="Discover new deals via crawler", parents=[base_parser])
    update_p = subparsers.add_parser("update", help="Update known deals quickly", parents=[base_parser])
    
    rest_p = subparsers.add_parser("restaurants", help="Discover deals in restaurants", parents=[base_parser])
    rest_p.add_argument("--restaurant", action="append", help="Filter by restaurant name (alias for --store)")

    acc_p = subparsers.add_parser("account", help="Read-only account diagnostics")
    acc_p.add_argument("action", choices=["status"])

    db_p = subparsers.add_parser("db", help="Database management")
    db_p.add_argument("action", choices=["status", "integrity", "backup", "vacuum"])

    runs_p = subparsers.add_parser("runs", help="Show previous runs")
    runs_p.add_argument("--last", type=int, default=10)

    stats_p = subparsers.add_parser("stats", help="Show database stats")

    watch_p = subparsers.add_parser("watch", help="Manage watchlist")
    watch_p.add_argument("action", choices=["add", "list", "remove", "enable", "disable"])
    watch_p.add_argument("query_or_id", nargs="?")
    watch_p.add_argument("--below", type=float)

    doctor_p = subparsers.add_parser("doctor", help="Run system diagnostics")
    doctor_p.add_argument("--network", action='store_true', help="Include network checks (not yet implemented)")

    return parser

def handle_config_command(args):
    cfg = load_config()
    if args.action == "show":
        import json
        print(json.dumps(cfg, indent=2))
    elif args.action == "get":
        print(cfg.get(args.key, ""))
    elif args.action == "set":
        if args.key in ["rappi_token", "token", "bearer_token"]:
            import sys
            print("ERROR: Tokens cannot be saved to configuration for security reasons. Use RAPPI_BEARER_TOKEN env var.", file=sys.stderr)
            sys.exit(1)
        try:
            val = float(args.value) if '.' in args.value else int(args.value)
        except:
            val = args.value
        cfg[args.key] = val
        save_config(cfg)
    elif args.action == "unset":
        if args.key in cfg:
            del cfg[args.key]
            save_config(cfg)
    elif args.action == "reset":
        if sys.stdin.isatty():
            ans = input("Are you sure you want to reset config? (y/N) ")
            if ans.lower() != 'y': return
        save_config({})

def main(args_list=None):
    parser = build_parser()
    args = parser.parse_args(args_list)
    
    config = get_merged_config(args, args.profile)
    
    if args.show_config:
        import json
        print(json.dumps(config, indent=2))
        return
        
    if args.command == "config":
        handle_config_command(args)
        return

    if args.command == "doctor":
        import os
        db_path = os.environ.get("RAPPI_DB_PATH", os.path.expanduser("~/rappi-deal-hunter/rappi-deals.db"))
        checks = run_doctor(db_path=db_path, check_network=getattr(args, "network", False))
        print(format_doctor_output(checks))
        return

    if args.command == "account":
        from .account import get_account_status
        import json
        if args.action == "status":
            try:
                status = get_account_status(config)
                print(json.dumps(status, indent=2))
            except Exception as e:
                from .errors import classify_error
                err = classify_error(e)
                print(f"Error checking account: {err}", file=sys.stderr)
        return
        
    conn = setup_db()
    
    if args.command == "db":
        import os
        db_path = os.environ.get("RAPPI_DB_PATH", os.path.expanduser("~/rappi-deal-hunter/rappi-deals.db"))
        
        if args.action == "status":
            import json
            print(json.dumps(db_status(db_path), indent=2))
        elif args.action == "integrity":
            print(db_integrity(db_path))
        elif args.action == "backup":
            path = backup_db(db_path)
            print(f"Backup created at {path}")
        elif args.action == "vacuum":
            db_vacuum(db_path)
            print("Vacuum complete")
        return
        
    elif args.command == "runs":
        c = conn.cursor()
        c.execute("SELECT run_id, started_at, finished_at, status FROM runs ORDER BY started_at DESC LIMIT ?", (args.last,))
        results = [{"run_id": r[0], "started_at": r[1], "finished_at": r[2], "status": r[3]} for r in c.fetchall()]
        print_results(results, format="table")
        return
        
    elif args.command == "stats":
        import json
        import os
        db_path = os.environ.get("RAPPI_DB_PATH", os.path.expanduser("~/rappi-deal-hunter/rappi-deals.db"))
        print(json.dumps(db_status(db_path), indent=2))
        return
        
    elif args.command in ("watch"):
        c = conn.cursor()
        if args.action == "add":
            c.execute("INSERT INTO watchlist (query, target_price, created_at) VALUES (?, ?, ?)",
                      (args.query_or_id, args.below, datetime.now().isoformat()))
            conn.commit()
            print("Added to watchlist")
        elif args.action == "list":
            c.execute("SELECT id, query, target_price, enabled FROM watchlist")
            results = [{"id": r[0], "query": r[1], "target_price": r[2], "enabled": r[3]} for r in c.fetchall()]
            print_results(results, format="table")
        elif args.action == "remove":
            c.execute("DELETE FROM watchlist WHERE id = ?", (args.query_or_id,))
            conn.commit()
        elif args.action in ["enable", "disable"]:
            val = 1 if args.action == "enable" else 0
            c.execute("UPDATE watchlist SET enabled = ? WHERE id = ?", (val, args.query_or_id))
            conn.commit()
        return
        
    # Crawler commands
    if args.command in ("discover", "update", "restaurants", None):
        if args.command == "restaurants":
            config["vertical"] = ["restaurants"]
            if getattr(args, "restaurant", None):
                config["store"] = args.restaurant

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        c = conn.cursor()
        lat, lng = config.get("lat", 19.4326), config.get("lng", -99.1332)
        c.execute('''INSERT INTO runs (run_id, started_at, lat, lng, radius, status) 
                     VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, 'RUNNING')''', 
                  (run_id, lat, lng, config.get("radius", 5.0)))
        conn.commit()
        
        mode = args.command if args.command else "discover"
        print(f"Running mode: {mode}", file=sys.stderr)
        
        try:
            if mode == "discover":
                state, reqs = run_discover(config, lat, lng, conn, run_id, dry_run=config.get("dry_run"))
            else:
                state, reqs = run_update(config, lat, lng, conn, run_id, dry_run=config.get("dry_run"))
        except Exception as exc:
            # Preserve already-committed observations; mark run as PARTIAL
            from .errors import classify_error
            err = classify_error(exc)
            state = "PARTIAL"
            print(f"Run interrupted: {err}", file=sys.stderr)
            
        c.execute('''UPDATE runs SET status = ?, finished_at = CURRENT_TIMESTAMP WHERE run_id = ?''', (state, run_id))
        conn.commit()
        
        if config.get("dry_run"):
            print("Dry run completed successfully.", file=sys.stderr)
            
if __name__ == "__main__":
    main()
