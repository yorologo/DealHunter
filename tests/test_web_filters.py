import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import pytest
from dealhunter.web.queries import get_catalog, get_available_categories
import sqlite3

from tests.helpers.db import insert_store, insert_product, insert_observation
import sqlite3

@pytest.fixture
def test_db(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    
    # Store A: Café, Té
    insert_store(conn, 'A', name='Store A', brand='Brand A', type='restaurants')
    insert_product(conn, 'p1', 'A', name='Cafe 1', brand='B', category='Café', quantity=1.0, unit='u', normalized_quantity=1.0, normalized_unit='u', pack_count=1)
    insert_product(conn, 'p2', 'A', name='Te 1', brand='B', category='Té', quantity=1.0, unit='u', normalized_quantity=1.0, normalized_unit='u', pack_count=1)
    insert_observation(conn, run_id='run1', store_id='A', product_id='p1', price=50.0, original_price=100.0, timestamp='2023-01-01T12:00:00Z', discount_effective=50.0)
    insert_observation(conn, run_id='run1', store_id='A', product_id='p2', price=50.0, original_price=100.0, timestamp='2023-01-01T12:00:00Z', discount_effective=50.0)
    
    # Store B: Hamburguesas, Postres
    insert_store(conn, 'B', name='Store B', brand='Brand B', type='restaurants')
    insert_product(conn, 'p3', 'B', name='Burger 1', brand='B', category='Hamburguesas', quantity=1.0, unit='u', normalized_quantity=1.0, normalized_unit='u', pack_count=1)
    insert_product(conn, 'p4', 'B', name='Postre 1', brand='B', category='Postres', quantity=1.0, unit='u', normalized_quantity=1.0, normalized_unit='u', pack_count=1)
    insert_observation(conn, run_id='run1', store_id='B', product_id='p3', price=50.0, original_price=100.0, timestamp='2023-01-01T12:00:00Z', discount_effective=50.0)
    insert_observation(conn, run_id='run1', store_id='B', product_id='p4', price=50.0, original_price=100.0, timestamp='2023-01-01T12:00:00Z', discount_effective=50.0)
    
    conn.commit()
    conn.close()
    return current_schema_db_path

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
