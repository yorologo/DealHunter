from dealhunter.discounts import calculate_discount

def test_existing_2x1_unchanged():
    p = {
        "price": 50.0,
        "real_price": 50.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 2, "units_condition": 1}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "NxM"
    assert deff == 50.0
    assert not extra["has_pro_offer"]

def test_public_and_pro_coexist():
    p = {
        "price": 80.0,
        "real_price": 100.0,
        "have_discount": True,
        "discount": 0.20,
        "is_prime_exclusive": True,
        "PrimeDiscount": 40.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    # Public channel
    assert deff == 20.0
    assert ptype == "Direct"
    # Pro channel
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 40.0
    assert extra["pro_discount_effective"] == 60.0

def test_pro_only_60():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "is_prime_exclusive": True,
        "PrimeDiscount": 60.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff is None or deff == 0.0 # Public effective discount shouldn't exist
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 40.0
    assert extra["pro_discount_effective"] == 60.0
    assert extra["pro_promo_type"] == "Direct"

def test_public_nxm_pro_price_coexist():
    p = {
        "price": 50.0,
        "real_price": 50.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 3, "units_condition": 2}]
        },
        "is_pro_exclusive": True,
        "PrimeDiscount": 10.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "NxM"
    assert abs(deff - 33.33) < 0.1
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 40.0
    assert extra["pro_discount_effective"] == 20.0

def test_public_progressive_pro_coexist():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2}]
        },
        "is_pro_exclusive": True,
        "PrimeDiscount": 40.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "PROGRESSIVE"
    assert deff == 25.0
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 60.0
    assert extra["pro_discount_effective"] == 40.0

def test_pro_progressive():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2, "is_pro_exclusive": True}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff is None or deff == 0.0
    assert extra["has_pro_offer"] is True
    assert extra["pro_discount_effective"] == 25.0
    assert extra["pro_promo_type"] == "PROGRESSIVE"

def test_promotion_ordering():
    # Deal 1: Pro 50%, Deal 2: Public 20%
    p = {
        "price": 80.0,
        "real_price": 100.0,
        "discount": 0.20,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 1, "is_pro_exclusive": True}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff == 20.0
    assert ptype == "Direct"
    assert extra["pro_discount_effective"] == 50.0

def test_malformed_pro_does_not_contaminate_public():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": "abc", "units_condition": 2, "is_pro_exclusive": True}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff is None or deff == 0.0


def test_progressive_unknown_math():
    from dealhunter.discounts import calculate_discount
    p = {
        "price": 100.0,
        "discounts_bundle": {
            "progressive": {"some_complex": "struct"}
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "PROGRESSIVE_UNKNOWN"
    assert deff is None
    assert extra["progressive"] is not None

def test_promotion_limits_preserved():
    from dealhunter.discounts import calculate_discount
    p = {
        "price": 100.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 2, "units_condition": 1, "limit": 2}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert extra["limit"] == 2

import sqlite3

def test_unavailable_preserves_unknown():
    db_conn = sqlite3.connect(':memory:')
    c = db_conn.cursor()
    c.execute("""CREATE TABLE observations (id INTEGER PRIMARY KEY, run_id TEXT, store_id TEXT, product_id TEXT, 
                 price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, 
                 discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, 
                 promotion_label TEXT, query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL, 
                 pro_price REAL, pro_discount_effective REAL, limit_info TEXT, UNIQUE(run_id, store_id, product_id))""")
    c.execute("""CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
                     normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT,
                     fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER DEFAULT 0, category_source TEXT, UNIQUE(product_id, store_id))""")
    c.execute("""CREATE TABLE product_memberships (store_id TEXT, product_id TEXT, raw_type TEXT, raw_name TEXT, raw_id TEXT, path TEXT, source TEXT, last_seen DATETIME, UNIQUE(store_id, product_id, raw_type, raw_name, path))""")

    # This requires using the core module to insert, which might be tricky if it needs a full mock
    # Let's test the logic we put in core.py by invoking process_and_insert_product directly
    from dealhunter.core import process_and_insert_product
    
    # Insert a product first
    p = {
        "id": "123",
        "name": "Test",
        "price": 100,
        "is_available": False
    }
    
    # We will test process_and_insert_product with v12 enabled
    import dealhunter.db as db_module
    db_module.CURRENT_SCHEMA_VERSION = 13
    
    run_id = "run-1"
    store_id = "store-1"
    
    process_and_insert_product(p, run_id, store_id, "store", {}, "cat", db_conn, set())
    
    c = db_conn.cursor()
    c.execute("SELECT has_pro_offer FROM observations WHERE product_id='123'")
    res = c.fetchone()
    assert res is not None
    assert res[0] is None # Because it's UNAVAILABLE and no Pro info

def test_available_no_pro_writes_zero():
    from dealhunter.core import process_and_insert_product
    import dealhunter.db as db_module
    db_module.CURRENT_SCHEMA_VERSION = 13
    db_conn = sqlite3.connect(':memory:')
    c = db_conn.cursor()
    c.execute("""CREATE TABLE observations (id INTEGER, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL, pro_price REAL, pro_discount_effective REAL, limit_info TEXT, UNIQUE(run_id, store_id, product_id))""")
    c.execute("""CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
                     normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT,
                     fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER DEFAULT 0, category_source TEXT, UNIQUE(product_id, store_id))""")
    c.execute("""CREATE TABLE product_memberships (store_id TEXT, product_id TEXT, raw_type TEXT, raw_name TEXT, raw_id TEXT, path TEXT, source TEXT, last_seen DATETIME, UNIQUE(store_id, product_id, raw_type, raw_name, path))""")
    
    p = {
        "id": "123",
        "name": "Test",
        "price": 100,
        "is_available": True
    }
    
    process_and_insert_product(p, "run-1", "store-1", "store_name", {}, "cat", db_conn, set())
    c.execute("SELECT has_pro_offer FROM observations")
    res = c.fetchone()
    assert res[0] == 0

def test_available_pro_writes_one():
    from dealhunter.core import process_and_insert_product
    import dealhunter.db as db_module
    db_module.CURRENT_SCHEMA_VERSION = 13
    db_conn = sqlite3.connect(':memory:')
    c = db_conn.cursor()
    c.execute("""CREATE TABLE observations (id INTEGER, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL, pro_price REAL, pro_discount_effective REAL, limit_info TEXT, UNIQUE(run_id, store_id, product_id))""")
    c.execute("""CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
                     normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT,
                     fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER DEFAULT 0, category_source TEXT, UNIQUE(product_id, store_id))""")
    c.execute("""CREATE TABLE product_memberships (store_id TEXT, product_id TEXT, raw_type TEXT, raw_name TEXT, raw_id TEXT, path TEXT, source TEXT, last_seen DATETIME, UNIQUE(store_id, product_id, raw_type, raw_name, path))""")
    
    p = {
        "id": "123",
        "name": "Test",
        "price": 100,
        "is_available": True,
        "is_prime_exclusive": True,
        "PrimeDiscount": 30.0
    }
    
    process_and_insert_product(p, "run-1", "store-1", "store_name", {}, "cat", db_conn, set())
    c.execute("SELECT has_pro_offer FROM observations")
    res = c.fetchone()
    assert res[0] == 1
