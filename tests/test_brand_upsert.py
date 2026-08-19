import os
import sys
import tempfile
import sqlite3
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.db import setup_db
from dealhunter.crawler import run_update
from dealhunter.normalization import parse_product_name, generate_fingerprint

class DummyConfig:
    pass

def test_trademark_to_brand_upsert():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    conn = setup_db(db_path)
    
    # Insert an existing product WITHOUT brand
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('s1', 'Test Store', 'market')")
    c.execute('''INSERT INTO products (product_id, store_id, name, brand, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint)
                 VALUES ('p1', 's1', 'Coca Cola 2 L', '', 'coca cola', 2, 'L', 2, 'L', 'coca cola|2|L')''')
    conn.commit()
    
    # Mock network request to return the same product WITH trademark
    import dealhunter.crawler as crawler_mod
    original_fetch = crawler_mod.fetch_unified_search
    
    def mock_fetch(query, lat, lng):
        print(f"Mock called with query: {query}")
        return {
            "stores": [
                {
                    "store_id": "s1",
                    "store_name": "Test Store",
                    "store_brand_name": "Test",
                    "parent_store_type": "market",
                    "products": [
                        {
                            "product_id": "p1",
                            "name": "Coca Cola 2 L",
                            "trademark": "Coca-Cola",
                            "price": 40.0,
                            "real_price": 40.0,
                            "in_stock": True,
                            "image": "img1.jpg"
                        }
                    ]
                }
            ]
        }
        
    crawler_mod.fetch_unified_search = mock_fetch
    
    try:
        cfg = {
            "location": {"lat": 0, "lng": 0},
            "market": {"radius": 1000},
            "general": {"filters": {"exclude": []}}
        }
        
        # We need a query in observation config or run_update looks up DB
        # run_update looks at past observations. We need to create one.
        c.execute('''INSERT INTO observations (run_id, store_id, product_id, price, timestamp, query_term, availability) 
                     VALUES ('old_run', 's1', 'p1', 40.0, '2020-01-01', 'coca cola', 'AVAILABLE')''')
        conn.commit()
        
        import time
        original_sleep = time.sleep
        time.sleep = lambda x: None
        
        try:
            run_update(cfg, 0, 0, conn, "new_run", dry_run=False)
        finally:
            time.sleep = original_sleep
        
        # Check if brand was enriched
        c.execute("SELECT brand, normalized_name, fingerprint FROM products WHERE product_id = 'p1'")
        row = c.fetchone()
        assert row is not None
        assert row[0] == "Coca-Cola" # Original raw brand should be preserved
        assert row[1] == "coca cola" # Canonical name
        assert row[2] == "coca-cola|coca-cola|2.0|l" or row[2] == "coca-cola|coca-cola|2|l"
        
    finally:
        crawler_mod.fetch_unified_search = original_fetch
        conn.close()
        os.remove(db_path)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
