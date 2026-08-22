import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.historico import compare_stores

def test_compare_stores_grouping():
    from dealhunter.db import setup_db
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    conn = setup_db(db_path)
    c = conn.cursor()
    
    # Insert test data
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'Soriana', 'Soriana', 'market')")
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s2', 'Chedraui', 'Chedraui', 'market')")
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s3', 'Turbo', 'Turbo', 'turbo')")
    
    c.execute("INSERT INTO products (product_id, store_id, name, brand, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count) VALUES ('p1', 's1', 'Coca Cola Original 2 L', 'Coca-Cola', 'original', 2, 'L', 2, 'L', 'coca cola|original|2|l', 1)")
    c.execute("INSERT INTO products (product_id, store_id, name, brand, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count) VALUES ('p2', 's2', 'Coca-Cola Refresco Original 2000 ml', 'Coca-Cola', 'refresco original', 2000, 'ml', 2, 'L', 'coca cola|refresco original|2|l', 1)")
    c.execute("INSERT INTO products (product_id, store_id, name, brand, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count) VALUES ('p3', 's3', 'Coca Cola Zero 2 L', 'Coca-Cola', 'zero', 2, 'L', 2, 'L', 'coca cola|zero|2|l', 1)")
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, stock, timestamp) VALUES ('r1', 's1', 'p1', 42.0, 42.0, 10, '2026-08-19T00:00:00')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, stock, timestamp) VALUES ('r1', 's2', 'p2', 45.0, 45.0, 10, '2026-08-19T00:00:00')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, stock, timestamp) VALUES ('r1', 's3', 'p3', 49.0, 49.0, 10, '2026-08-19T00:00:00')")
    
    conn.commit()
    c.execute("INSERT INTO products (product_id, store_id, name, brand, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count) VALUES ('p4', 's1', 'Cacahuete 500 g', 'Marcax', 'cacahuete', 500, 'g', 0.5, 'kg', 'marcax|cacahuete|0.5|kg', 1)")
    c.execute("INSERT INTO products (product_id, store_id, name, brand, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count) VALUES ('p5', 's2', 'Cacahuate 500 g', 'Marcax', 'cacahuate', 500, 'g', 0.5, 'kg', 'marcax|cacahuate|0.5|kg', 1)")
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, stock, timestamp) VALUES ('r1', 's1', 'p4', 20.0, 20.0, 10, '2026-08-19T00:00:00')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, stock, timestamp) VALUES ('r1', 's2', 'p5', 22.0, 22.0, 10, '2026-08-19T00:00:00')")
    
    conn.commit()
    
    # Test fuzzy default
    res2 = compare_stores(db_path, "cacahu")
    assert len({r["GRUPO"] for r in res2}) == 1
    
    # Test no_fuzzy
    res3 = compare_stores(db_path, "cacahu", no_fuzzy=True)
    assert len({r["GRUPO"] for r in res3}) == 2
    
    res = compare_stores(db_path, "coca")
    
    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # p1 and p2 should be in the same group because p1 is EXACT and p2 is HIGH_CONFIDENCE. p3 is a different group
    groups = {}
    for r in res:
        groups[r["GRUPO"]] = groups.get(r["GRUPO"], []) + [r]
        
    assert len(groups) == 2
    
    group_original = [v for k, v in groups.items() if "Original" in k][0]
    group_zero = [v for k, v in groups.items() if "Zero" in k][0]
    
    assert len(group_original) == 2
    assert len(group_zero) == 1
    
    # Check best price in original group
    best = group_original[0]
    assert best["PRECIO"] == "$42.00"
    assert best["TIENDA"] == "Soriana"
    assert best["DIFF"] == "BEST"
    
    second = group_original[1]
    assert second["PRECIO"] == "$45.00"
    assert second["TIENDA"] == "Chedraui"
    assert "7.1%" in second["DIFF"]
    assert second["MATCH"] == "HIGH_CONFIDENCE"
    
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nMulti-store tests: {passed} total, {passed} passed, 0 failed.")
