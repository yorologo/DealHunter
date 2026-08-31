import pytest
from dealhunter.db import setup_db
import tempfile
import os
import sqlite3

def test_trust_contract_parity():
    # 4. TEST FIDELITY GATE & 3. TRUST CONTRACT
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "trust.db")
    
    conn = setup_db(db)
    c = conn.cursor()
    
    # 1. Valid SUCCESS run
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('r_success', '2026-08-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r_success', 'rappi', 's1', 'p1', 100.0)")
    
    # 2. Valid PARTIAL run
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('r_partial', '2026-08-01', 'PARTIAL')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r_partial', 'rappi', 's1', 'p2', 100.0)")
    
    # 3. Invalid FAILED run
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('r_failed', '2026-08-01', 'FAILED')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r_failed', 'rappi', 's1', 'p3', 100.0)")
    
    # 4. Orphan (no run_id in runs)
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r_orphan', 'rappi', 's1', 'p4', 100.0)")
    
    # 5. Missing run_id (NULL)
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES (NULL, 'rappi', 's1', 'p5', 100.0)")
    
    # 6. Legacy run_d8c5dbb90f34 without run_id inserted
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('run_d8c5dbb90f34', 'rappi', 's1', 'p6', 100.0)")
    
    conn.commit()
    
    c.execute("SELECT product_id FROM trusted_observations")
    trusted_pids = {r[0] for r in c.fetchall()}
    
    assert 'p1' in trusted_pids
    assert 'p2' in trusted_pids
    assert 'p3' not in trusted_pids
    assert 'p4' not in trusted_pids
    assert 'p5' not in trusted_pids
    assert 'p6' not in trusted_pids

def test_market_category_sql():
    # CATEGORY_MARKET_SQL
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "cat.db")
    conn = setup_db(db)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('s1', 'A', 'market')")
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('s2', 'B', 'restaurants')")
    conn.commit()
    
    from dealhunter.web.queries import get_available_categories
    cats = get_available_categories(db, vertical="market")
    
    # Just verify no SQL syntax error on LOWER(s.type)
    assert True

def test_uber_restaurant_index():
    # UBER_RESTAURANT_INDEX
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "uber.db")
    conn = setup_db(db)
    c = conn.cursor()
    c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('uber_eats', 's1', 'Uber Rest', 'RESTAURANT')")
    c.execute("INSERT INTO products (provider, store_id, product_id, name) VALUES ('uber_eats', 's1', 'p1', 'Food')")
    conn.commit()
    
    from dealhunter.web.queries import get_restaurants_home
    stores = get_restaurants_home(db)
    assert any(s["provider"] == "uber_eats" and s["store_id"] == "s1" for s in stores)

def test_restaurant_metrics_trust_policy():
    # RESTAURANT_TRUST_POLICY
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "trust2.db")
    conn = setup_db(db)
    c = conn.cursor()
    c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('rappi', 's1', 'Rest', 'restaurant')")
    c.execute("INSERT INTO products (provider, product_id, store_id, name) VALUES ('rappi', 'p1', 's1', 'Dish')")
    
    # 1 valid observation
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('r1', '2026-08-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp, availability) VALUES ('r1', 'rappi', 's1', 'p1', 10.0, '2026-08-01', 'AVAILABLE')")
    
    # 1 orphan observation (untrusted)
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp, availability) VALUES ('orphan', 'rappi', 's1', 'p1', 5.0, '2026-08-02', 'AVAILABLE')")
    
    conn.commit()
    
    from dealhunter.web.queries import get_restaurants_home
    stores = get_restaurants_home(db)
    assert len(stores) == 1
    # If trust policy is applied, max_obs or similar metrics will ignore the orphan. 
    # Actually get_restaurants_home counts available dishes using trusted_observations
    assert stores[0]["available_dishes"] == 1

