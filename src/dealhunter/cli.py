import argparse
import math
import sys
from .config import get_merged_config, save_config, load_config
from .db import setup_db, db_status, db_integrity, db_vacuum, backup_db
from .crawler import run_discover, run_update
from .historico import analyze_history, compare_stores
from .output import print_results
from .doctor import run_doctor, format_doctor_output
from datetime import datetime

VERSION = "2.8.1"
LOCATION_CHANGE_WARNING_METERS = 500.0


def _require_location(parser, config):
    """Return an explicit crawl location or stop before creating a run."""
    lat = config.get("lat")
    lng = config.get("lng")
    if lat is None or lng is None:
        parser.error(
            "Crawler location is required. Set both --lat/--lng or save lat/lng "
            "in the DealHunter config."
        )
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        parser.error("Crawler lat/lng must be numeric.")
    if not -90 <= lat <= 90 or not -180 <= lng <= 180:
        parser.error("Crawler lat/lng are outside valid coordinate ranges.")
    return lat, lng


def _distance_m(lat1, lng1, lat2, lng2):
    """Great-circle distance for detecting a meaningful context change."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lng / 2) ** 2
    )
    return 6_371_000 * 2 * math.asin(math.sqrt(a))


def _warn_on_location_change(conn, lat, lng):
    """Warn on a new crawl context; never mutate or delete history."""
    row = conn.execute(
        """SELECT lat, lng FROM runs
           WHERE lat IS NOT NULL AND lng IS NOT NULL
           ORDER BY started_at DESC LIMIT 1"""
    ).fetchone()
    if not row:
        return
    distance = _distance_m(float(row[0]), float(row[1]), lat, lng)
    if distance >= LOCATION_CHANGE_WARNING_METERS:
        print(
            "WARNING: LOCATION_CONTEXT_CHANGED "
            f"({distance:.0f} m from the most recent captured context). "
            "Existing history was preserved; review comparability explicitly.",
            file=sys.stderr,
        )


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


    auth_parser = subparsers.add_parser("auth", help="Authentication utilities")
    auth_parser.add_argument("provider", choices=["rappi"], help="Provider to authenticate")
    auth_parser.add_argument("--mobile", action="store_true", help="Start mobile auth importer")
    auth_parser.add_argument("--diagnose", action="store_true", help="Run auth diagnostic (mobile only)")
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

    crawler_commands = ("discover", "update", "restaurants", None)
    location = None
    if args.command == "auth":
        if args.provider == "rappi":
            from .auth import RappiSessionProvider, LocalAuthImporter

            prov = RappiSessionProvider()
            is_diagnose = getattr(args, "diagnose", False)
            
            if getattr(args, "mobile", False):
                print(f"[*] Mobile authentication {'diagnostic' if is_diagnose else 'import'} started")
                try:
                    importer = LocalAuthImporter(prov, host="127.0.0.1", port=0, is_mobile=True, diagnose=is_diagnose)
                    importer.start()
                except Exception as e:
                    print(f"[!] Failed to bind local server: {e}")
                    return

                print(f"[*] Local endpoint: http://127.0.0.1:{importer.port}/{'diagnose' if is_diagnose else 'import'}")
                print("[*] Bookmarklet generated below")
                
                if is_diagnose:
                    bookmarklet = """javascript:(async function(){
  if (window.location.hostname !== 'www.rappi.com.mx' && window.location.hostname !== 'rappi.com.mx') {
    alert('DealHunter: this diagnostic must be executed on rappi.com.mx');
    return;
  }
  function isJWT(str) {
    if (typeof str !== 'string') return false;
    const parts = str.split('.');
    if (parts.length !== 3) return false;
    try {
      JSON.parse(atob(parts[0].replace(/-/g, '+').replace(/_/g, '/')));
      JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      return true;
    } catch(e) { return false; }
  }
  function extractJWT(str) {
    const parts = str.split('.');
    try {
      const header = JSON.parse(atob(parts[0].replace(/-/g, '+').replace(/_/g, '/')));
      const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      return {header, payload};
    } catch(e) { return null; }
  }
  function classifyValue(val) {
    if (val === null || val === undefined || val === '') return {type: 'EMPTY'};
    if (isJWT(val)) return {type: 'JWT', jwt: extractJWT(val)};
    try {
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) return {type: 'JSON_ARRAY', parsed};
      if (typeof parsed === 'object' && parsed !== null) return {type: 'JSON_OBJECT', parsed};
    } catch(e) {}
    if (/^[A-Za-z0-9+/=]+$/.test(val) && val.length > 20) return {type: 'BASE64_LIKE'};
    if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val)) return {type: 'UUID_LIKE'};
    return {type: 'TEXT'};
  }
  function findNestedJWTs(obj, path = "$") {
    let found = [];
    if (typeof obj === 'string') {
      if (isJWT(obj)) found.push({path, type: 'JWT_EMBEDDED', jwt: extractJWT(obj), raw: obj});
    } else if (Array.isArray(obj)) {
      obj.forEach((v, i) => found.push(...findNestedJWTs(v, path + "[" + i + "]")));
    } else if (typeof obj === 'object' && obj !== null) {
      for (const [k, v] of Object.entries(obj)) {
        found.push(...findNestedJWTs(v, path + "." + k));
      }
    }
    return found;
  }
  const report = {
    origin: location.origin, hostname: location.hostname, userAgent: navigator.userAgent,
    localStorage: [], sessionStorage: [], cookies: [], indexedDB: []
  };
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i); const value = localStorage.getItem(key);
    const classification = classifyValue(value);
    const entry = {key, length: value ? value.length : 0, type: classification.type, raw: value};
    if (classification.type === 'JWT') entry.jwt = classification.jwt;
    else if (classification.type === 'JSON_OBJECT' || classification.type === 'JSON_ARRAY') entry.nested = findNestedJWTs(classification.parsed);
    report.localStorage.push(entry);
  }
  for (let i = 0; i < sessionStorage.length; i++) {
    const key = sessionStorage.key(i); const value = sessionStorage.getItem(key);
    const classification = classifyValue(value);
    const entry = {key, length: value ? value.length : 0, type: classification.type, raw: value};
    if (classification.type === 'JWT') entry.jwt = classification.jwt;
    else if (classification.type === 'JSON_OBJECT' || classification.type === 'JSON_ARRAY') entry.nested = findNestedJWTs(classification.parsed);
    report.sessionStorage.push(entry);
  }
  const cookies = document.cookie.split(';');
  for (const c of cookies) {
    if (!c.trim()) continue;
    const parts = c.split('='); const key = parts[0].trim(); const value = parts.slice(1).join('=').trim();
    const classification = classifyValue(value);
    const entry = {key, length: value ? value.length : 0, type: classification.type, raw: value};
    if (classification.type === 'JWT') entry.jwt = classification.jwt;
    report.cookies.push(entry);
  }
  try {
    if (window.indexedDB && indexedDB.databases) {
      const dbs = await indexedDB.databases();
      for (const dbInfo of dbs) {
        const dbMeta = {name: dbInfo.name, version: dbInfo.version, stores: []};
        try {
          const db = await new Promise((resolve, reject) => {
            const req = indexedDB.open(dbInfo.name);
            req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error);
          });
          for (let i = 0; i < db.objectStoreNames.length; i++) dbMeta.stores.push(db.objectStoreNames[i]);
          db.close();
        } catch(e) { dbMeta.error = e.toString(); }
        report.indexedDB.push(dbMeta);
      }
    } else { report.indexedDB = 'IndexedDB enumeration unavailable in this browser.'; }
  } catch(e) { report.indexedDB = 'Error reading IndexedDB: ' + e; }
  const payload = JSON.stringify(report);
  window.location.href = 'http://127.0.0.1:__PORT__/diagnose#' + btoa(unescape(encodeURIComponent(payload)));
})();""".replace('__PORT__', str(importer.port))
                else:
                    bookmarklet = """javascript:(function(){
  if (window.location.hostname !== 'www.rappi.com.mx' && window.location.hostname !== 'rappi.com.mx') {
    alert('DealHunter: this bookmarklet must be executed on rappi.com.mx');
    return;
  }
  function isJWT(str) {
    if (typeof str !== 'string') return false;
    const p = str.split('.'); if (p.length !== 3) return false;
    try { JSON.parse(atob(p[0].replace(/-/g, '+').replace(/_/g, '/'))); JSON.parse(atob(p[1].replace(/-/g, '+').replace(/_/g, '/'))); return true; } catch(e) { return false; }
  }
  function ext(str) {
    try { return JSON.parse(atob(str.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))); } catch(e) { return null; }
  }
  function findJ(obj) {
    let f = [];
    if (typeof obj === 'string') { if (isJWT(obj)) f.push(obj); }
    else if (Array.isArray(obj)) { obj.forEach(v => f.push(...findJ(v))); }
    else if (typeof obj === 'object' && obj !== null) { for (const v of Object.values(obj)) f.push(...findJ(v)); }
    return f;
  }
  let c = [];
  function scan(s) {
    for (let i = 0; i < s.length; i++) {
      const v = s.getItem(s.key(i));
      if (isJWT(v)) c.push(v);
      else { try { c.push(...findJ(JSON.parse(v))); } catch(e) {} }
    }
  }
  scan(localStorage); scan(sessionStorage);
  document.cookie.split(';').forEach(ck => {
    const v = ck.split('=').slice(1).join('=').trim();
    if (isJWT(v)) c.push(v);
  });
  let valid = [];
  Array.from(new Set(c)).forEach(t => {
    const p = ext(t);
    if (p && p.exp && (p.exp * 1000 > Date.now())) valid.push(t);
  });
  if (valid.length === 0) { alert('DealHunter: No active session found.'); return; }
  valid.sort((a,b) => b.length - a.length);
  var pay = JSON.stringify({nonce: '__NONCE__', token: valid[0]});
  window.location.href = 'http://127.0.0.1:__PORT__/import#' + btoa(unescape(encodeURIComponent(pay)));
})();""".replace('__NONCE__', importer.nonce).replace('__PORT__', str(importer.port))
                
                print("\n" + bookmarklet.replace("\n", "") + "\n")
                
                print("1. Open https://www.rappi.com.mx/ and sign in.")
                print("2. Create a browser bookmark named \"DH Import\".")
                print("3. Paste the bookmarklet above into the bookmark URL field.")
                print("4. While viewing Rappi, type \"DH Import\" in the address bar and select the bookmark.")
                print("5. Return to Termux.\n")
                
                print("[*] Waiting for local browser...")
                
                try:
                    if importer.serve_with_timeout(300):
                        print("[+] Local server stopped")
                    else:
                        print("\n[!] Authentication operation timed out")
                except KeyboardInterrupt:
                    importer.server.shutdown()
                    importer.server.server_close()
                    print("\nCancelled.")
            else:
                if is_diagnose:
                    print("Diagnostics is currently only supported in mobile mode (--mobile --diagnose)")
                    return
                # Desktop flow
                try:
                    importer = LocalAuthImporter(prov, host="127.0.0.1", port=5050, is_mobile=False)
                    importer.start()
                except OSError as e:
                    print(f"\n[!] Could not bind to port 5050. Ensure no other instances are running.")
                    return
                    
                print("To securely authenticate without exposing your tokens:")
                print("1. Open www.rappi.com.mx in your browser and login.")
                print("2. Open Developer Tools (F12) -> Console")
                print("3. Paste this code to send the session securely to DealHunter:")
                print("\nfetch('http://127.0.0.1:5050/commit', {")
                print("  method: 'POST',")
                print("  headers: {'Content-Type': 'application/json'},")
                print("  body: JSON.stringify({nonce: '__NONCE__', token: localStorage.getItem('access_token')})".replace('__NONCE__', importer.nonce))
                print("}).then(() => console.log('DealHunter Auth OK!')).catch(e => console.error(e));\n")
                
                print(f"[*] Waiting for session data on port 5050...")
                try:
                    if importer.serve_with_timeout(300):
                        print("[+] Local server stopped")
                    else:
                        print("\n[!] Authentication operation timed out")
                except KeyboardInterrupt:
                    importer.server.shutdown()
                    importer.server.server_close()
                    print("\nCancelled.")
        return

    if args.command in crawler_commands:
        location = _require_location(parser, config)
        
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
    if args.command in crawler_commands:
        if args.command == "restaurants":
            config["vertical"] = ["restaurants"]
            if getattr(args, "restaurant", None):
                config["store"] = args.restaurant

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        c = conn.cursor()
        lat, lng = location
        _warn_on_location_change(conn, lat, lng)
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
