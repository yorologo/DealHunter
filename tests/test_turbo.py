"""Tests for Turbo support in DealHunter v2.2."""

import os
import sys
import json
import sqlite3
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.crawler import run_discover, VERTICALS

# Mock response that mimics a unified search result containing a Turbo store
MOCK_TURBO_RESPONSE = {
    "stores": [
        {
            "store_id": "1923463011",
            "store_name": "Turbo Fresh-Roma Norte",
            "store_brand_name": "Turbo",
            "parent_store_type": "chiper_home",
            "products": [
                {
                    "product_id": "12345",
                    "name": "Coca Cola Original PET 2000 ml",
                    "trademark": "Coca-Cola",
                    "category_name": "Bebidas",
                    "price": 30.0,
                    "real_price": 40.0,
                    "discount": 25,
                    "in_stock": True,
                    "stock": 10,
                    "image": "coca.jpg"
                },
                {
                    "product_id": "67890",
                    "name": "Papas Sabritas 170g (2x1)",
                    "trademark": "Sabritas",
                    "category_name": "Snacks",
                    "price": 50.0,
                    "real_price": 50.0,
                    "discount": 0,
                    "in_stock": True,
                    "stock": 5,
                    "discounts_bundle": {
                        "deal": [
                            {
                                "promotion_value": 2,
                                "units_condition": 1,
                                "label": "2x1"
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

def _make_test_db():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT)''')
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, PRIMARY KEY (store_id, product_id))''')
    c.execute('''CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME, lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)''')
    c.execute('''CREATE TABLE observations (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, availability TEXT, UNIQUE(run_id, store_id, product_id))''')
    conn.commit()
    return conn, db_path

@patch('dealhunter.crawler.fetch_unified_search')
def test_turbo_store_detection_and_normalization(mock_fetch):
    """Test that Turbo stores and products are properly discovered and normalized."""
    mock_fetch.return_value = MOCK_TURBO_RESPONSE
    
    conn, db_path = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('turbo_run1', CURRENT_TIMESTAMP, 'RUNNING')")
    conn.commit()
    
    config = {
        "vertical": ["turbo"],
        "query": [],
        "max_requests": 1,
        "max_runtime": 3600,
        "min_discount": 0,
        "max_discount": 100,
        "dry_run": False
    }
    
    state, reqs = run_discover(config, 19.4, -99.1, conn, "turbo_run1")
    
    assert "turbo" in VERTICALS, "Turbo vertical should be registered"
    
    # Check that store was saved
    c.execute("SELECT name, type FROM stores WHERE store_id = '1923463011'")
    store = c.fetchone()
    assert store is not None
    assert "Turbo" in store[0]
    assert store[1] == "chiper_home"
    
    # Check that products were normalized and saved
    c.execute("SELECT name, brand FROM products WHERE store_id = '1923463011' ORDER BY product_id")
    products = c.fetchall()
    assert len(products) == 2
    assert products[0][0] == "Coca Cola Original PET 2000 ml"
    
    # Check observations and discounts
    c.execute("SELECT price, original_price, discount_effective, promotion_type FROM observations WHERE run_id = 'turbo_run1' ORDER BY product_id")
    obs = c.fetchall()
    
    # Product 1 (Coca Cola): Direct discount 25%
    assert obs[0][0] == 30.0 # price
    assert obs[0][1] == 40.0 # original_price
    assert obs[0][2] == 25.0 # discount_effective
    assert obs[0][3] == "Direct" # promotion_type
    
    # Product 2 (Sabritas): NxM 2x1 -> 50%
    assert obs[1][0] == 50.0
    assert obs[1][1] == 100.0
    assert obs[1][2] == 50.0
    assert obs[1][3] == "NxM"

@patch('dealhunter.crawler.fetch_unified_search')
def test_turbo_filters(mock_fetch):
    """Test that filters (e.g. min_discount) apply to Turbo products correctly."""
    mock_fetch.return_value = MOCK_TURBO_RESPONSE
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('turbo_run2', CURRENT_TIMESTAMP, 'RUNNING')")
    conn.commit()
    
    config = {
        "vertical": ["turbo"],
        "query": [],
        "max_requests": 1,
        "max_runtime": 3600,
        "min_discount": 40, # should exclude Coca Cola (25%) and keep Sabritas (50%)
        "max_discount": 100,
        "dry_run": False
    }
    
    run_discover(config, 19.4, -99.1, conn, "turbo_run2")
    
    c.execute("SELECT product_id FROM observations WHERE run_id = 'turbo_run2'")
    obs = c.fetchall()
    assert len(obs) == 1
    assert obs[0][0] == "67890" # Only Sabritas

@patch('dealhunter.crawler.fetch_unified_search')
def test_turbo_false_positives(mock_fetch):
    """Test that stores are strictly classified by structured metadata, not just the word 'turbo'."""
    mixed_response = {
        "stores": [
            {
                "store_id": "f1",
                "store_name": "Farmacia con Licuadora Turbo",
                "parent_store_type": "market",
                "products": [{"product_id": "p1", "name": "Licuadora Turbo", "price": 100, "real_price": 200, "in_stock": True, "stock": 5}]
            },
            {
                "store_id": "m1",
                "store_name": "Soriana Turbo",
                "parent_store_type": "market",
                "products": [{"product_id": "p2", "name": "Manzana", "price": 10, "real_price": 20, "in_stock": True, "stock": 5}]
            },
            {
                "store_id": "t1",
                "store_name": "Turbo Fresh",
                "parent_store_type": "chiper_home",
                "products": [{"product_id": "p3", "name": "Agua", "price": 10, "real_price": 20, "in_stock": True, "stock": 5}]
            },
            {
                "store_id": "t2",
                "store_name": "Turbo Store",
                "store_type": "chiper_extended",
                "products": [{"product_id": "p4", "name": "Pan", "price": 10, "real_price": 20, "in_stock": True, "stock": 5}]
            },
            {
                "store_id": "t3",
                "store_name": "Turbo Express",
                "store_type": "chiper_express",
                "products": [{"product_id": "p5", "name": "Jugo", "price": 10, "real_price": 20, "in_stock": True, "stock": 5}]
            }
        ]
    }
    mock_fetch.return_value = mixed_response
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('turbo_run3', CURRENT_TIMESTAMP, 'RUNNING')")
    conn.commit()
    
    config = {
        "vertical": ["turbo"],
        "query": [],
        "max_requests": 1,
        "max_runtime": 3600,
        "dry_run": False
    }
    
    run_discover(config, 19.4, -99.1, conn, "turbo_run3")
    
    # Check that only chiper stores were saved
    c.execute("SELECT store_id FROM stores ORDER BY store_id")
    stores = [r[0] for r in c.fetchall()]
    assert "f1" not in stores
    assert "m1" not in stores
    assert "t1" in stores
    assert "t2" in stores
    assert "t3" in stores
    assert len(stores) == 3

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nTurbo tests: {passed} total, {passed} passed, 0 failed.")
