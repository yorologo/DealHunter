import os
import sys
import tempfile
import sqlite3
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from dealhunter.alerts import AlertEngine
from dealhunter.db import setup_db

def test_alert_engine_types():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    
    conn = setup_db(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO stores VALUES ('s1', 'Soriana', '', 'market')")
    c.execute("INSERT INTO stores VALUES ('s2', 'Chedraui', '', 'market')")
    
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p1', 's1', 'Coca Cola 2 L')") # TARGET
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p2', 's1', 'Galletas')") # NEW_LOW
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p3', 's2', 'Leche')") # PRICE_DROP
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p4', 's2', 'Cereal')") # BACK_IN_STOCK
    
    # Watchlist target for Coca Cola <= 35
    c.execute("INSERT INTO watchlist (query, store_filter, target_price, enabled) VALUES ('Coca Cola', NULL, 35.0, 1)")
    
    now = datetime.now()
    t1 = (now - timedelta(days=2)).isoformat()
    t2 = (now - timedelta(days=1)).isoformat()
    t3 = now.isoformat()
    
    # TARGET_PRICE obs (34 is <= 35)
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r1', 's1', 'p1', 40.0, ?)", (t1,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r2', 's1', 'p1', 34.0, ?)", (t3,))
    
    # NEW_LOW obs
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r1', 's1', 'p2', 50.0, ?)", (t1,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r2', 's1', 'p2', 45.0, ?)", (t2,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r3', 's1', 'p2', 40.0, ?)", (t3,))
    
    # PRICE_DROP obs (100 -> 80 is 20%)
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r1', 's2', 'p3', 100.0, ?)", (t1,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r2', 's2', 'p3', 80.0, ?)", (t3,))
    
    # BACK_IN_STOCK obs
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, availability, timestamp) VALUES ('r1', 's2', 'p4', 60.0, 'UNAVAILABLE', ?)", (t1,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, availability, timestamp) VALUES ('r2', 's2', 'p4', 60.0, 'AVAILABLE', ?)", (t3,))
    
    conn.commit()
    conn.close()
    
    engine = AlertEngine(db_path)
    res = engine.evaluate()
    
    types = {r["alert_type"] for r in res}
    assert "TARGET_PRICE" in types
    assert "NEW_LOW" in types
    assert "PRICE_DROP" in types
    assert "BACK_IN_STOCK" in types
    
    # Seen status test BEFORE deduplication
    all_alerts = engine.get_alerts()
    assert len(all_alerts) >= 4
    for a in all_alerts:
        assert a["seen"] is False

    # Deduplication test
    engine.mark_seen(all=True)
    res2 = engine.evaluate()
    assert len(res2) == 0 # no new alerts!
        
    all_alerts_seen = engine.get_alerts(new_only=True)
    assert len(all_alerts_seen) == 0
    
    # Price drop deeper allows new alert
    conn = setup_db(db_path)
    c = conn.cursor()
    # Coca cola drops to 30
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r4', 's1', 'p1', 30.0, ?)", ((now + timedelta(days=1)).isoformat(),))
    conn.commit()
    conn.close()
    
    res3 = engine.evaluate()
    assert len(res3) >= 1
    assert any(r["alert_type"] == "TARGET_PRICE" for r in res3)
    assert res3[0]["current_price"] == 30.0

if __name__ == "__main__":
    test_alert_engine_types()
    print("Tests passed")
