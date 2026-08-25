import sqlite3
import pytest
from dealhunter.web.queries import get_product_detail, get_catalog

from tests.helpers.db import insert_store, insert_product, insert_observation, insert_alert, insert_watchlist
import sqlite3

def test_get_product_detail_mapping(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    
    insert_store(conn, 's1', 'MyStore', 'market', 'BrandStore')
    insert_product(conn, 'p1', 's1', 'Test Product', 'MyBrand', 'MyCat', quantity=500, unit='g', normalized_quantity=0.5, normalized_unit='kg', pack_count=1, fingerprint='fp', has_toppings=0)
    insert_observation(conn, run_id='r1', store_id='s1', product_id='p1', price=100.0, original_price=150.0, stock=10, timestamp='2023-01-01T12:00:00Z', discount_effective=0, discount_promotion=0, discount_price=0, availability='AVAILABLE')
    conn.commit()
    conn.close()
    
    p = get_product_detail(current_schema_db_path, 's1', 'p1')
    assert p["product_name"] == "Test Product"
    assert p["store_name"] == "MyStore"
    assert p["store_type"] == "market"
    assert p["brand"] == "MyBrand"
    assert p["category"] == "MyCat"
    assert p["quantity"] == 500
    assert p["unit"] == "g"
    assert p["normalized_quantity"] == 0.5
    assert p["normalized_unit"] == "kg"
    assert p["pack_count"] == 1

def test_get_catalog_sorting(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    
    insert_store(conn, 's1', 'MyStore', 'market', 'BrandStore')
    insert_product(conn, 'p1', 's1', 'P1', '', '', quantity=1.0, normalized_quantity=1.0, pack_count=1)
    insert_observation(conn, run_id='r1', store_id='s1', product_id='p1', price=90.0, original_price=100.0, stock=10, timestamp='2023-01-01T12:00:00Z', discount_effective=10.0, availability='AVAILABLE')
    insert_product(conn, 'p2', 's1', 'P2', '', '', quantity=1.0, normalized_quantity=1.0, pack_count=1)
    insert_observation(conn, run_id='r1', store_id='s1', product_id='p2', price=50.0, original_price=100.0, stock=10, timestamp='2023-01-01T12:00:00Z', discount_effective=50.0, availability='AVAILABLE')
    insert_product(conn, 'p3', 's1', 'P3', '', '', quantity=1.0, normalized_quantity=1.0, pack_count=1)
    insert_observation(conn, run_id='r1', store_id='s1', product_id='p3', price=800.0, original_price=1000.0, stock=10, timestamp='2023-01-01T12:00:00Z', discount_effective=20.0, availability='AVAILABLE')
    conn.commit()
    conn.close()
    
    cat_desc = get_catalog(current_schema_db_path, {"vertical": "market"}, "discount", 1, 10)
    assert cat_desc["items"][0]["product_id"] == "p2"
    assert cat_desc["items"][1]["product_id"] == "p3"
    assert cat_desc["items"][2]["product_id"] == "p1"
    
    cat_sav = get_catalog(current_schema_db_path, {"vertical": "market"}, "savings", 1, 10)
    assert cat_sav["items"][0]["product_id"] == "p3"
    assert cat_sav["items"][1]["product_id"] == "p2"
    assert cat_sav["items"][2]["product_id"] == "p1"

