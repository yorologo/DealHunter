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
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
    from dealhunter.db import setup_db as real_setup
    real_setup(db_path)
    
    # insert dummy data
    c.execute("INSERT INTO stores VALUES ('s1', 'Test Store', '', 'supermercado')")
    c.execute("INSERT INTO products (product_id, store_id, name, brand, image) VALUES ('p1', 's1', 'Test Product', '', '')")
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
        assert "deals" in res.stdout
        
        # Test config
        res = run_cmd("python3 bin/rappi-ofertas config set min_discount 40")
        assert res.returncode == 0
        res = run_cmd("python3 bin/rappi-ofertas config get min_discount")
        assert "40" in res.stdout
        assert run_cmd("python3 bin/rappi-ofertas config set lat 0").returncode == 0
        assert run_cmd("python3 bin/rappi-ofertas config set lng 0").returncode == 0
        
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
        
        res = run_cmd("python3 bin/rappi-historico deals --format json")
        assert "store_id" in res.stdout
        
        print("E2E tests passed!")

if __name__ == "__main__":
    main()
