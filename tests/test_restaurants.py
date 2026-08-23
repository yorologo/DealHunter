"""Tests for Restaurant support in DealHunter v2.2."""

import os
import sys
import sqlite3
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.crawler import run_discover, VERTICALS

MOCK_RESTAURANTS_RESPONSE = {
    "stores": [
        {
            "store_id": "r1",
            "store_name": "Burger Joint",
            "parent_store_type": "restaurants",
            "products": [
                {
                    "product_id": "p1",
                    "name": "Hamburguesa Clasica",
                    "category_name": "Hamburguesas",
                    "price": 100.0,
                    "real_price": 100.0,
                    "in_stock": True,
                    "stock": None,
                    "has_toppings": True
                },
                {
                    "product_id": "p2",
                    "name": "Combo Hamburguesa + Papas",
                    "category_name": "Combos",
                    "price": 120.0,
                    "real_price": 150.0,
                    "in_stock": True,
                    "stock": None
                },
                {
                    "product_id": "p3",
                    "name": "Malteada",
                    "category_name": "Bebidas",
                    "price": 50.0,
                    "real_price": 50.0,
                    "in_stock": False,
                    "stock": None
                }
            ]
        },
        {
            "store_id": "m1",
            "store_name": "Supermercado Falso",
            "parent_store_type": "market",
            "products": [
                {
                    "product_id": "p4",
                    "name": "Hamburguesa Congelada",
                    "price": 50.0,
                    "in_stock": True,
                    "stock": 10
                }
            ]
        }
    ]
}

def _make_test_db():
    from dealhunter.db import setup_db
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    conn = setup_db(db_path)
    return conn, db_path

@patch('dealhunter.crawler.fetch_unified_search')
def test_restaurant_detection(mock_fetch):
    """Test that only restaurants are imported when vertical is restaurants."""
    mock_fetch.return_value = MOCK_RESTAURANTS_RESPONSE
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('rest_run1', CURRENT_TIMESTAMP, 'RUNNING')")
    
    config = {
        "vertical": ["restaurants"],
        "query": ["hamburguesa"],
        "max_requests": 1,
        "max_runtime": 3600,
        "dry_run": False
    }
    
    run_discover(config, 19.4, -99.1, conn, "rest_run1")
    
    c.execute("SELECT store_id FROM stores")
    stores = [r[0] for r in c.fetchall()]
    assert "r1" in stores
    assert "m1" not in stores # Market store should be excluded

@patch('dealhunter.crawler.fetch_unified_search')
def test_restaurant_products(mock_fetch):
    """Test parsing of normal, discounted, out-of-stock, and modified items."""
    mock_fetch.return_value = MOCK_RESTAURANTS_RESPONSE
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('rest_run2', CURRENT_TIMESTAMP, 'RUNNING')")
    
    config = {"vertical": ["restaurants"], "query": ["hamburguesa"], "max_requests": 1, "max_runtime": 3600}
    run_discover(config, 19.4, -99.1, conn, "rest_run2")
    
    c.execute("SELECT product_id, price, original_price, discount_effective, stock, availability FROM observations ORDER BY product_id")
    obs = c.fetchall()
    
    assert len(obs) == 2
    
    # p1: Clasica (no discount, stock=NULL)
    assert obs[0][0] == "p1"
    assert obs[0][1] == 100.0
    assert obs[0][2] == 100.0
    assert obs[0][3] == 0.0
    assert obs[0][4] is None # stock
    assert obs[0][5] == "AVAILABLE"
    
    # p2: Combo (discounted)
    assert obs[1][0] == "p2"
    assert obs[1][1] == 120.0
    assert obs[1][2] == 150.0
    assert round(obs[1][3], 1) == 20.0 # (1 - 120/150) * 100
    assert obs[1][4] is None
    assert obs[1][5] == "AVAILABLE"

@patch('dealhunter.crawler.fetch_unified_search')
def test_restaurant_filters(mock_fetch):
    """Test min_discount and query filters applied to restaurants."""
    mock_fetch.return_value = MOCK_RESTAURANTS_RESPONSE
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('rest_run3', CURRENT_TIMESTAMP, 'RUNNING')")
    
    config = {
        "vertical": ["restaurants"],
        "query": ["hamburguesa"],
        "min_discount": 10,
        "max_requests": 1,
        "max_runtime": 3600
    }
    run_discover(config, 19.4, -99.1, conn, "rest_run3")
    
    c.execute("SELECT product_id FROM observations")
    obs = c.fetchall()
    assert len(obs) == 2

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nRestaurant tests: {passed} total, {passed} passed, 0 failed.")
