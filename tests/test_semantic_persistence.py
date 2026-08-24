import pytest
import sqlite3
import os
import datetime
from dealhunter.db import setup_db, CURRENT_SCHEMA_VERSION
from dealhunter.core import process_and_insert_product

def get_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def test_migration_v10_to_v11(tmp_path):
    db_path = str(tmp_path / "test_migration.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Setup v10
    c.execute("CREATE TABLE schema_version (version INTEGER)")
    c.execute("INSERT INTO schema_version VALUES (10)")
    c.execute('''CREATE TABLE product_memberships (
        store_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        raw_type TEXT,
        raw_name TEXT NOT NULL,
        raw_id TEXT,
        path TEXT,
        source TEXT,
        last_seen DATETIME,
        UNIQUE(store_id, product_id, raw_type, raw_name, path)
    )''')
    c.execute('''INSERT INTO product_memberships (store_id, product_id, raw_type, raw_name, path)
                 VALUES ('s1', 'p1', 'corridor', 'Sushi', 'Sushi')''')
    conn.commit()
    conn.close()
    
    # Run setup_db to trigger migration
    setup_db(db_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] in [11, 12, 13, 14]
    
    # Check legacy data was preserved and got default values
    c.execute("SELECT semantic_type, semantic_reason FROM product_memberships WHERE raw_name='Sushi'")
    row = c.fetchone()
    assert row[0] == 'UNKNOWN'
    assert row[1] == 'not_classified'
    conn.close()

def test_semantic_persistence_rules(tmp_path):
    db_path = str(tmp_path / "test_persistence.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, store_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (product_id TEXT PRIMARY KEY, store_id TEXT)''')
    
    seen = set()
    now = get_now()
    
    # 1. new provider membership persists CATEGORY
    p1 = {
        "id": "p1", "name": "Prod 1", "price": 100,
        "category": "Cervezas", "category_source": "provider",
        "memberships": [{"raw_name": "Cervezas", "raw_type": "corridor", "path": ["Cervezas"]}]
    }
    process_and_insert_product(p1, 1, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type, semantic_reason FROM product_memberships WHERE product_id='p1'")
    row = c.fetchone()
    assert row == ('CATEGORY', 'matches_provider_category')
    
    # 2. new collection persists COLLECTION
    seen.clear()
    p2 = {
        "id": "p2", "name": "Prod 2", "price": 100,
        "category": "Cervezas", "category_source": "provider",
        "memberships": [{"raw_name": "Ofertas", "raw_type": "corridor", "path": ["Ofertas"]}]
    }
    process_and_insert_product(p2, 1, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type, semantic_reason FROM product_memberships WHERE product_id='p2'")
    row = c.fetchone()
    assert row == ('COLLECTION', 'known_rappi_collection')
    
    # 3. ambiguous persists UNKNOWN
    seen.clear()
    p3 = {
        "id": "p3", "name": "Prod 3", "price": 100,
        "category": "Cervezas", "category_source": "provider",
        "memberships": [{"raw_name": "Nueva Seccion", "raw_type": "corridor", "path": ["Nueva Seccion"]}]
    }
    process_and_insert_product(p3, 1, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type, semantic_reason FROM product_memberships WHERE product_id='p3'")
    row = c.fetchone()
    assert row == ('UNKNOWN', 'insufficient_evidence')
    
    # 4. Multi-membership stores independent semantic types
    seen.clear()
    p4 = {
        "id": "p4", "name": "Prod 4", "price": 100,
        "category": "Cervezas", "category_source": "provider",
        "memberships": [
            {"raw_name": "Cervezas", "raw_type": "corridor", "path": ["Cervezas"]},
            {"raw_name": "Ofertas", "raw_type": "corridor", "path": ["Ofertas"]}
        ]
    }
    process_and_insert_product(p4, 1, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT raw_name, semantic_type FROM product_memberships WHERE product_id='p4' ORDER BY raw_name")
    rows = c.fetchall()
    assert rows == [('Cervezas', 'CATEGORY'), ('Ofertas', 'COLLECTION')]
    
    # 5. same membership UNKNOWN -> CATEGORY on re-observation
    seen.clear()
    p5 = {
        "id": "p5", "name": "Prod 5", "price": 100,
        "category": "", # Inferred -> UNKNOWN
        "memberships": [{"raw_name": "Sushi", "raw_type": "corridor", "path": ["Sushi"]}]
    }
    process_and_insert_product(p5, 1, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type FROM product_memberships WHERE product_id='p5'")
    assert c.fetchone()[0] == 'UNKNOWN'
    
    # Re-observation with provider
    seen.remove("s1_p5")
    p5_new = {
        "id": "p5", "name": "Prod 5", "price": 100,
        "category": "Sushi", "category_source": "provider", # Provider -> CATEGORY
        "memberships": [{"raw_name": "Sushi", "raw_type": "corridor", "path": ["Sushi"]}]
    }
    process_and_insert_product(p5_new, 2, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type FROM product_memberships WHERE product_id='p5'")
    assert c.fetchone()[0] == 'CATEGORY'
    
    # 6. same membership CATEGORY -> UNKNOWN if evidence disappears
    seen.remove("s1_p5")
    p5_lost = {
        "id": "p5", "name": "Prod 5", "price": 100,
        "category": "", "category_source": "unknown", # Evidence lost
        "memberships": [{"raw_name": "Sushi", "raw_type": "corridor", "path": ["Sushi"]}]
    }
    process_and_insert_product(p5_lost, 3, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type FROM product_memberships WHERE product_id='p5'")
    assert c.fetchone()[0] == 'UNKNOWN'
    
    # 7. Complete reconciliation still removes stale membership
    seen.remove("s1_p5")
    p5_empty = {
        "id": "p5", "name": "Prod 5", "price": 100,
        "category": "", "category_source": "unknown",
        "memberships": [] # Empty memberships in full run removes old ones
    }
    process_and_insert_product(p5_empty, 4, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT COUNT(*) FROM product_memberships WHERE product_id='p5'")
    assert c.fetchone()[0] == 0

    # 8. conflict persists UNKNOWN (simulate by passing conflicting data)
    seen.clear()
    p8 = {
        "id": "p8", "name": "Prod 8", "price": 100,
        "category": "Cervezas", "category_source": "provider",
        "memberships": [{"raw_name": "Ofertas", "raw_type": "corridor", "path": ["Ofertas"]}]
    }
    # But wait, Ofertas is always COLLECTION.
    # What causes conflicting_evidence? 
    # 'Ofertas' as raw_name AND category='Ofertas' provider? 
    # Let's test that:
    p8["category"] = "Ofertas"
    process_and_insert_product(p8, 1, "s1", "Store 1", {}, None, conn, seen)
    c.execute("SELECT semantic_type, semantic_reason FROM product_memberships WHERE product_id='p8'")
    row = c.fetchone()
    assert row == ('UNKNOWN', 'conflicting_evidence')
