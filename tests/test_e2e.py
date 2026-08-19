import os
import sys
import subprocess
import tempfile
import sqlite3
import time

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def setup_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, PRIMARY KEY (store_id, product_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME, lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, UNIQUE(run_id, store_id, product_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, store_filter TEXT, target_price REAL, min_discount REAL, created_at DATETIME, enabled INTEGER DEFAULT 1)''')
    
    # insert dummy data
    c.execute("INSERT INTO stores VALUES ('s1', 'Test Store', '', 'supermercado')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'Test Product', '', '')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, discount_effective) VALUES ('r1', 's1', 'p1', 100, '2020-01-01T00:00:00', 0)")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, discount_effective) VALUES ('r2', 's1', 'p1', 50, '2020-01-02T00:00:00', 50)")
    conn.commit()
    conn.close()

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        config_home = os.path.join(tmpdir, "config")
        os.environ["RAPPI_DB_PATH"] = db_path
        os.environ["XDG_CONFIG_HOME"] = config_home
        
        setup_db(db_path)
        
        print("Testing CLI e2e offline...")
        
        # Test help
        res = run_cmd("python3 bin/rappi-ofertas --help")
        assert "DealHunter CLI v" in res.stdout
        
        res = run_cmd("python3 bin/rappi-historico --help")
        assert "min-history-days" in res.stdout
        
        # Test config
        res = run_cmd("python3 bin/rappi-ofertas config set min_discount 40")
        assert res.returncode == 0
        res = run_cmd("python3 bin/rappi-ofertas config get min_discount")
        assert "40" in res.stdout
        
        # Test runs
        res = run_cmd("python3 bin/rappi-ofertas runs")
        assert res.returncode == 0
        
        # Test db stats
        res = run_cmd("python3 bin/rappi-ofertas db status")
        assert res.returncode == 0
        assert "stores" in res.stdout
        
        # Test dry-run discover
        res = run_cmd("python3 bin/rappi-ofertas discover --dry-run")
        if "Dry run completed successfully." not in res.stderr: print("ERR WAS:", res.stderr); assert False
        
        # Test dry-run update
        res = run_cmd("python3 bin/rappi-ofertas update --dry-run")
        if "Dry run completed successfully." not in res.stderr: print("ERR WAS:", res.stderr); assert False
        
        # Test watchlist
        res = run_cmd("python3 bin/rappi-ofertas watch add 'Test' --below 100")
        assert res.returncode == 0
        res = run_cmd("python3 bin/rappi-ofertas watch list")
        assert "Test" in res.stdout
        
        # Test historico output
        res = run_cmd("python3 bin/rappi-historico")
        assert res.returncode == 0
        
        res = run_cmd("python3 bin/rappi-historico --json")
        assert os.path.exists("history-analysis.json")
        
        print("E2E tests passed!")

if __name__ == "__main__":
    main()
