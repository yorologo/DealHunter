import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import pytest
from dealhunter.web.queries import get_catalog, get_available_categories
import sqlite3

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE stores (
        store_id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT
    )''')
    c.execute('''CREATE TABLE products (
        product_id TEXT,
        store_id TEXT,
        name TEXT,
        brand TEXT,
        category TEXT,
        quantity REAL,
        unit TEXT,
        normalized_quantity REAL,
        normalized_unit TEXT,
        pack_count INTEGER,
        PRIMARY KEY (store_id, product_id)
    )''')
    c.execute('''CREATE TABLE observations (
        product_id TEXT,
        store_id TEXT,
        price REAL,
        original_price REAL,
        timestamp TEXT,
        discount_effective REAL,
        promotion_type TEXT,
        promotion_label TEXT,
        availability INTEGER,
        has_toppings INTEGER
    )''')
    conn.commit()
    
    # Store A: Café, Té
    c.execute("INSERT INTO stores VALUES ('A', 'Store A', 'restaurants')")
    c.execute("INSERT INTO products VALUES ('p1', 'A', 'Cafe 1', 'B', 'Café', 1, 'u', 1, 'u', 1)")
    c.execute("INSERT INTO products VALUES ('p2', 'A', 'Te 1', 'B', 'Té', 1, 'u', 1, 'u', 1)")
    c.execute("INSERT INTO observations VALUES ('p1', 'A', 50, 100, '2023-01-01', 50, '', '', 1, 0)")
    c.execute("INSERT INTO observations VALUES ('p2', 'A', 50, 100, '2023-01-01', 50, '', '', 1, 0)")
    
    # Store B: Hamburguesas, Postres
    c.execute("INSERT INTO stores VALUES ('B', 'Store B', 'restaurants')")
    c.execute("INSERT INTO products VALUES ('p3', 'B', 'Burger 1', 'B', 'Hamburguesas', 1, 'u', 1, 'u', 1)")
    c.execute("INSERT INTO products VALUES ('p4', 'B', 'Postre 1', 'B', 'Postres', 1, 'u', 1, 'u', 1)")
    c.execute("INSERT INTO observations VALUES ('p3', 'B', 50, 100, '2023-01-01', 50, '', '', 1, 0)")
    c.execute("INSERT INTO observations VALUES ('p4', 'B', 50, 100, '2023-01-01', 50, '', '', 1, 0)")
    
    conn.commit()
    conn.close()
    return str(db_path)

def test_zero_stores_means_all(test_db):
    filters = {"store": []}
    res = get_catalog(test_db, filters, sort="score", page=1)
    # Check if we get products from both stores
    store_ids = {r["store_id"] for r in res["items"]}
    assert store_ids == {"A", "B"}

def test_multiple_stores_use_union_categories(test_db):
    # This refers to get_available_categories logic
    cats = get_available_categories(test_db, store_ids=["A", "B"])
    assert set(cats) == {"Café", "Té", "Hamburguesas", "Postres"}

def test_multiple_stores_filter_with_or(test_db):
    filters = {"store": ["A", "B"]}
    res = get_catalog(test_db, filters, sort="score", page=1)
    store_ids = {r["store_id"] for r in res["items"]}
    assert store_ids == {"A", "B"}
    
def test_multiple_categories_filter_with_or(test_db):
    filters = {"category": ["Café", "Hamburguesas"]}
    res = get_catalog(test_db, filters, sort="score", page=1)
    cats = {r["category"] for r in res["items"]}
    assert set(cats) == {"Café", "Hamburguesas"}

def test_store_and_category_groups_use_and(test_db):
    # stores=[A], categories=[Café, Hamburguesas] -> Only Café because A doesn't have Hamburguesas
    filters = {"store": ["A"], "category": ["Café", "Hamburguesas"]}
    res = get_catalog(test_db, filters, sort="score", page=1)
    cats = {r["category"] for r in res["items"]}
    assert set(cats) == {"Café"}
    
def test_invalid_selected_category_is_removed(test_db):
    # Wait, the UI logic is tested? We can simulate the endpoint or just logic
    # If the user has category=Hamburguesas in the query param but changed to store=A
    # Usually this is handled by frontend or endpoint, but we can verify that the result filters out.
    filters = {"store": ["A"], "category": ["Hamburguesas"]}
    res = get_catalog(test_db, filters, sort="score", page=1)
    # Should be empty since A doesn't have Hamburguesas
    assert len(res["items"]) == 0
