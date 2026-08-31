import pytest
from dealhunter.historico import compare_with_anchor
from dealhunter.db import setup_db
from datetime import datetime

def test_compare_provider_legacy(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = setup_db(db_path)
    
    # Insert one product and observation
    conn.execute("INSERT INTO stores (provider, store_id, name) VALUES ('rappi', 's1', 'Store 1')")
    conn.execute("INSERT INTO products (provider, product_id, store_id, name, normalized_name) VALUES ('rappi', 'p1', 's1', 'Prod 1', 'prod 1')")
    conn.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r1', '2024-01-01', 'SUCCESS')")
    conn.execute("INSERT INTO observations (run_id, provider, product_id, store_id, price, timestamp) VALUES ('r1', 'rappi', 'p1', 's1', 100, '2026-08-30')")
    conn.commit()
    
    # Missing provider, should resolve
    res = compare_with_anchor(db_path, None, 's1', 'p1')
    assert len(res["matches"]) == 1
    assert res["matches"][0]["provider"] == "rappi"
    
    # Ambiguous product
    conn.execute("INSERT INTO stores (provider, store_id, name) VALUES ('uber_eats', 's1', 'Store 1')")
    conn.execute("INSERT INTO products (provider, product_id, store_id, name, normalized_name) VALUES ('uber_eats', 'p1', 's1', 'Prod 1', 'prod 1')")
    conn.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r1', '2024-01-01', 'SUCCESS')")
    conn.execute("INSERT INTO observations (run_id, provider, product_id, store_id, price, timestamp) VALUES ('r1', 'uber_eats', 'p1', 's1', 100, '2026-08-30')")
    conn.commit()
    
    # Now provider is None -> ambiguous -> should return empty
    res2 = compare_with_anchor(db_path, None, 's1', 'p1')
    assert len(res2) == 0
    
    # With provider -> returns only the match
    res3 = compare_with_anchor(db_path, 'uber_eats', 's1', 'p1')
    assert len(res3["matches"]) == 1
    assert res3["matches"][0]["provider"] == "uber_eats"

