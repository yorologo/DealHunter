import sqlite3
import pytest
from dealhunter.web.queries import get_catalog

from tests.helpers.db import insert_store, insert_product, insert_observation
import sqlite3

def test_determinism_ties(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    
    insert_store(conn, 's1', 'MyStore', 'market', 'Brand')
    insert_product(conn, 'p1', 's1', 'Prod', '', '', quantity=1.0, normalized_quantity=1.0, pack_count=1)
    
    # Insert two observations with exactly the same timestamp
    insert_observation(conn, run_id='r1', store_id='s1', product_id='p1', timestamp='2026-08-01T12:00:00', price=120.0, original_price=150.0)
    insert_observation(conn, run_id='r2', store_id='s1', product_id='p1', timestamp='2026-08-01T12:00:00', price=99.0, original_price=150.0)
    
    conn.commit()
    conn.close()

    cat = get_catalog(current_schema_db_path, {"store": "s1"}, "price_asc", 1)
    
    # By default, SQLite MAX() on tie returns the last inserted row (which is price 99.0)
    # But let's check if it's 99.0
    assert cat["items"][0]["current_price"] == 99.0


def test_determinism_cross_store(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    
    insert_store(conn, 's1', 'Store A', 'market', 'A')
    insert_store(conn, 's2', 'Store B', 'market', 'B')
    
    # Same product_id '123' in both stores
    insert_product(conn, '123', 's1', 'Prod A', '', '', quantity=1.0, normalized_quantity=1.0, pack_count=1)
    insert_product(conn, '123', 's2', 'Prod B', '', '', quantity=1.0, normalized_quantity=1.0, pack_count=1)
    
    insert_observation(conn, run_id='r1', store_id='s1', product_id='123', timestamp='2026-08-01T12:00:00', price=100.0, original_price=150.0)
    insert_observation(conn, run_id='r1', store_id='s2', product_id='123', timestamp='2026-08-01T12:00:00', price=50.0, original_price=150.0)
    
    conn.commit()
    conn.close()
    
    # Query without store filter, we should get TWO items!
    # Because get_catalog groups by store_id, product_id
    cat = get_catalog(current_schema_db_path, {}, "price_asc", 1)
    
    assert len(cat["items"]) == 2
    assert cat["items"][0]["current_price"] == 50.0
    assert cat["items"][1]["current_price"] == 100.0


