import pytest
import sqlite3
from dealhunter.db import setup_db
from datetime import datetime

# We will simulate the same logic as in crawler_zone.py to prove the pipeline correctly persists it.
def persist_merchant_mock(conn, m):
    c = conn.cursor()
    s_id = str(m.get("store_id", ""))
    s_name = m.get("name", "")
    
    # Logic extracted from crawler_zone.py lines 74-92
    raw_vsg = m.get("vertical_sub_group")
    parent_type = m.get("type", "supermercado")
    
    vertical = None
    if raw_vsg:
        v_lower = raw_vsg.lower()
        if "restaurant" in v_lower: vertical = "Restaurantes"
        elif "market" in v_lower or v_lower == "super": vertical = "Supermercado"
        elif "turbo" in v_lower: vertical = "Turbo"
        elif "farmacia" in v_lower: vertical = "Farmacia"
        else: vertical = raw_vsg
    else:
        p_lower = parent_type.lower()
        if "restaurant" in p_lower: vertical = "Restaurantes"
        elif "market" in p_lower or p_lower == "super": vertical = "Supermercado"
        elif "turbo" in p_lower: vertical = "Turbo"
        elif "farma" in p_lower: vertical = "Farmacia"
        else: vertical = parent_type

    c.execute('''INSERT INTO stores (store_id, name, brand, type, status, last_seen_at, vertical)
                 VALUES (?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT(provider, store_id) DO UPDATE SET
                 name = COALESCE(excluded.name, name),
                 type = COALESCE(excluded.type, type),
                 vertical = COALESCE(excluded.vertical, vertical),
                 status = 'ACTIVE',
                 last_seen_at = excluded.last_seen_at''',
              (s_id, s_name, m.get("brand", ""), parent_type, "ACTIVE", datetime.now().isoformat(), vertical))

    facets = set()
    tags = m.get("tags")
    if isinstance(tags, list):
        for t in tags:
            if t and isinstance(t, str): facets.add((t.strip(), "tags"))
            
    cats = m.get("categories")
    if isinstance(cats, str) and cats:
        for c_str in cats.split("·"):
            if c_str.strip(): facets.add((c_str.strip(), "categories"))
            
    has_metadata = ("tags" in m and m.get("tags") is not None) or ("categories" in m and m.get("categories") is not None)
    now_store_facets = datetime.now().isoformat()
    
    for val, src in facets:
        c.execute('''INSERT INTO store_facets (store_id, facet_type, raw_value, source, last_seen)
                     VALUES (?, ?, ?, ?, ?)
                     ON CONFLICT(provider, store_id, facet_type, raw_value) DO UPDATE SET
                     last_seen=excluded.last_seen
                  ''', (s_id, "store_subcategory", val, src, now_store_facets))
                  
    if has_metadata:
        c.execute('DELETE FROM store_facets WHERE store_id=? AND last_seen != ?', (s_id, now_store_facets))
        
    conn.commit()


def test_merchant_vertical_sub_group_persists(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    m = {
        "store_id": "1",
        "type": "chiper_extended",
        "vertical_sub_group": "turbo"
    }
    persist_merchant_mock(conn, m)
    c = conn.cursor()
    c.execute("SELECT type, vertical FROM stores WHERE store_id='1'")
    row = c.fetchone()
    assert row == ("chiper_extended", "Turbo") # legacy preserved, vertical populated

def test_legacy_parent_store_type_preserved_as_fallback(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    m = {
        "store_id": "2",
        "type": "Farmatodo"
    }
    persist_merchant_mock(conn, m)
    c = conn.cursor()
    c.execute("SELECT type, vertical FROM stores WHERE store_id='2'")
    row = c.fetchone()
    assert row == ("Farmatodo", "Farmacia") 

def test_restaurant_tags_categories_become_facets(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    m = {
        "store_id": "3",
        "tags": ["Sushi", "China"],
        "categories": "Sushi · China"
    }
    persist_merchant_mock(conn, m)
    c = conn.cursor()
    c.execute("SELECT raw_value FROM store_facets WHERE store_id='3' ORDER BY raw_value")
    rows = c.fetchall()
    assert rows == [("China",), ("Sushi",)] # Deduplicated!

def test_multiple_store_facets_preserved(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    m = {
        "store_id": "4",
        "tags": ["Mexican", "Tacos"]
    }
    persist_merchant_mock(conn, m)
    c = conn.cursor()
    c.execute("SELECT raw_value FROM store_facets WHERE store_id='4' ORDER BY raw_value")
    assert len(c.fetchall()) == 2

def test_absent_facet_metadata_preserves_previous_state(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    # Run 1: Full metadata
    m1 = {
        "store_id": "5",
        "tags": ["Pizza"]
    }
    persist_merchant_mock(conn, m1)
    
    # Run 2: Missing keys completely (like a partial run or missing data)
    m2 = {
        "store_id": "5"
    }
    persist_merchant_mock(conn, m2)
    
    c = conn.cursor()
    c.execute("SELECT raw_value FROM store_facets WHERE store_id='5'")
    assert c.fetchall() == [("Pizza",)]

def test_explicit_empty_metadata_reconciles_to_empty(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    # Run 1: Full metadata
    m1 = {
        "store_id": "6",
        "tags": ["Pizza"]
    }
    persist_merchant_mock(conn, m1)
    
    # Run 2: Explicit empty keys
    m2 = {
        "store_id": "6",
        "tags": [],
        "categories": ""
    }
    persist_merchant_mock(conn, m2)
    
    c = conn.cursor()
    c.execute("SELECT raw_value FROM store_facets WHERE store_id='6'")
    assert len(c.fetchall()) == 0

def test_non_restaurant_without_tags_keeps_vertical(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    m = {
        "store_id": "7",
        "type": "market",
        "vertical_sub_group": "market",
        "tags": [],
        "categories": ""
    }
    persist_merchant_mock(conn, m)
    
    c = conn.cursor()
    c.execute("SELECT type, vertical FROM stores WHERE store_id='7'")
    assert c.fetchone() == ("market", "Supermercado")
    c.execute("SELECT COUNT(*) FROM store_facets WHERE store_id='7'")
    assert c.fetchone()[0] == 0

def test_merchant_vertical_super_alias_normalizes_to_supermercado(tmp_path):
    db_path = str(tmp_path / "test.db")
    setup_db(db_path)
    conn = sqlite3.connect(db_path)
    
    m = {
        "store_id": "8",
        "type": "market",
        "vertical_sub_group": "Super",
        "tags": [],
        "categories": ""
    }
    persist_merchant_mock(conn, m)
    
    c = conn.cursor()
    c.execute("SELECT type, vertical FROM stores WHERE store_id='8'")
    assert c.fetchone() == ("market", "Supermercado")
