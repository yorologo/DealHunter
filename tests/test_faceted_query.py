import pytest
import sqlite3
from dealhunter.query_layer import build_faceted_query, get_facet_counts

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    # Schema
    c.execute("""CREATE TABLE observations (id INTEGER PRIMARY KEY, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL, pro_price REAL, pro_discount_effective REAL, limit_info TEXT)""")
    c.execute("""CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER DEFAULT 0, category_source TEXT)""")
    c.execute("""CREATE TABLE stores (store_id TEXT, name TEXT, type TEXT, vertical TEXT, brand TEXT)""")
    c.execute("""CREATE TABLE store_facets (store_id TEXT, facet_type TEXT, raw_value TEXT, source TEXT, last_seen DATETIME)""")
    c.execute("""CREATE TABLE product_memberships (store_id TEXT, product_id TEXT, raw_type TEXT, raw_name TEXT, raw_id TEXT, path TEXT, source TEXT, last_seen DATETIME, semantic_type TEXT, semantic_reason TEXT)""")
    
    # Data
    # Store 1 (vertical: Supermercado, facet: Express)
    c.execute("INSERT INTO stores (store_id, name, type, vertical) VALUES ('s1', 'Store 1', 'market', 'Supermercado')")
    c.execute("INSERT INTO store_facets (store_id, facet_type, raw_value) VALUES ('s1', 'speed', 'Express')")
    
    # Store 2 (vertical: Restaurantes, type: restaurants)
    c.execute("INSERT INTO stores (store_id, name, type, vertical) VALUES ('s2', 'Store 2', 'restaurants', 'Restaurantes')")
    
    # Product 1 (s1): Legacy category 'A', no memberships. Public deal 50%, no pro.
    c.execute("INSERT INTO products (product_id, store_id, name, category) VALUES ('p1', 's1', 'Prod 1', 'Cat A')")
    c.execute("INSERT INTO observations (product_id, store_id, timestamp, price, original_price, discount_effective, availability, has_pro_offer, pro_price, pro_discount_effective) VALUES ('p1', 's1', '2023-01-01', 50, 100, 50, 'AVAILABLE', 0, NULL, NULL)")
    
    # Product 2 (s1): Legacy category 'A', but trusted category 'B'. Pro deal 60%, public 10%.
    c.execute("INSERT INTO products (product_id, store_id, name, category) VALUES ('p2', 's1', 'Prod 2', 'Cat A')")
    c.execute("INSERT INTO observations (product_id, store_id, timestamp, price, original_price, discount_effective, availability, has_pro_offer, pro_price, pro_discount_effective) VALUES ('p2', 's1', '2023-01-01', 90, 100, 10, 'AVAILABLE', 1, 40, 60)")
    c.execute("INSERT INTO product_memberships (product_id, store_id, semantic_type, raw_name) VALUES ('p2', 's1', 'CATEGORY', 'Cat B')")
    
    # Product 3 (s2): Trusted category 'C', Collection 'Col 1'. No deals.
    c.execute("INSERT INTO products (product_id, store_id, name, category) VALUES ('p3', 's2', 'Prod 3', 'Cat A')")
    c.execute("INSERT INTO observations (product_id, store_id, timestamp, price, original_price, discount_effective, availability, has_pro_offer, pro_price, pro_discount_effective) VALUES ('p3', 's2', '2023-01-01', 100, 100, 0, 'AVAILABLE', NULL, NULL, NULL)")
    c.execute("INSERT INTO product_memberships (product_id, store_id, semantic_type, raw_name) VALUES ('p3', 's2', 'CATEGORY', 'Cat C')")
    c.execute("INSERT INTO product_memberships (product_id, store_id, semantic_type, raw_name) VALUES ('p3', 's2', 'COLLECTION', 'Col 1')")
    
    conn.commit()
    return conn

def execute_filters(conn, filters):
    q, count_q, params = build_faceted_query(filters)
    c = conn.cursor()
    c.execute(q, params)
    rows = c.fetchall()
    c.execute(count_q, params)
    total = c.fetchone()[0]
    return rows, total

def test_no_filters(db_conn):
    rows, total = execute_filters(db_conn, {})
    assert len(rows) == 3
    assert total == 3

def test_legacy_category_fallback(db_conn):
    # Cat A should only return p1 because p2 has trusted Cat B
    rows, total = execute_filters(db_conn, {"categories": ["Cat A"]})
    assert len(rows) == 1
    assert rows[0][0] == 'p1'
    
def test_trusted_category_override(db_conn):
    rows, total = execute_filters(db_conn, {"categories": ["Cat B"]})
    assert len(rows) == 1
    assert rows[0][0] == 'p2'

def test_collection(db_conn):
    rows, total = execute_filters(db_conn, {"collections": ["Col 1"]})
    assert len(rows) == 1
    assert rows[0][0] == 'p3'

def test_vertical_and_store_facet(db_conn):
    rows, total = execute_filters(db_conn, {"verticals": ["Supermercado"], "store_facets": ["Express"]})
    assert len(rows) == 2  # p1, p2
    
def test_public_deal_filter(db_conn):
    rows, total = execute_filters(db_conn, {"channel": "PUBLIC", "min_discount": 50})
    assert len(rows) == 1
    assert rows[0][0] == 'p1' # p2 public is only 10%

def test_pro_deal_filter(db_conn):
    rows, total = execute_filters(db_conn, {"channel": "PRO", "min_discount": 50})
    assert len(rows) == 1
    assert rows[0][0] == 'p2' # p2 has pro 60%

def test_pro_unknown(db_conn):
    # p3 has NULL for has_pro_offer. It shouldn't match PRO channel.
    rows, total = execute_filters(db_conn, {"channel": "PRO"})
    assert len(rows) == 1 # Only p2
    assert rows[0][0] == 'p2'

def test_all_channel(db_conn):
    rows, total = execute_filters(db_conn, {"channel": "ALL", "min_discount": 50})
    assert len(rows) == 2 # p1 (public 50) and p2 (pro 60)
    p_ids = [r[0] for r in rows]
    assert 'p1' in p_ids
    assert 'p2' in p_ids

def test_facet_counts(db_conn):
    counts = get_facet_counts(db_conn, {})
    assert "Cat A" in counts["categories"]
    assert "Cat B" in counts["categories"]
    assert "Cat C" in counts["categories"]
    assert "Col 1" in counts["collections"]
    assert "Supermercado" in counts["verticals"]
    assert "Restaurantes" in counts["verticals"]

def test_injection_safety(db_conn):
    # SQL injection attempt
    rows, total = execute_filters(db_conn, {"categories": ["' OR 1=1 --"]})
    assert len(rows) == 0


def test_mn_duplicates(db_conn):
    c = db_conn.cursor()
    # Add another facet to s1
    c.execute("INSERT INTO store_facets (store_id, facet_type, raw_value) VALUES ('s1', 'food', 'Food')")
    db_conn.commit()
    
    rows, total = execute_filters(db_conn, {"store_facets": ["Express", "Food"]})
    # p1 and p2 belong to s1.
    # The facets should OR together, and product should not be duplicated.
    assert len(rows) == 2
    assert total == 2

def test_and_across_dimensions(db_conn):
    # s1: Supermercado, s2: Restaurantes
    # categories: [Cat A] (p1, p3)
    # verticals: [Restaurantes]
    # Result should be ONLY p3.
    rows, total = execute_filters(db_conn, {"categories": ["Cat C"], "verticals": ["Restaurantes"]})
    assert len(rows) == 1
    assert rows[0][0] == 'p3'

def test_pagination(db_conn):
    # Create 30 products in s2
    c = db_conn.cursor()
    for i in range(10, 40):
        c.execute(f"INSERT INTO products (product_id, store_id, name, category) VALUES ('p{i}', 's2', 'Prod {i}', 'Cat X')")
        c.execute(f"INSERT INTO observations (product_id, store_id, timestamp, price, original_price, discount_effective, availability) VALUES ('p{i}', 's2', '2023-01-01', 100, 100, 0, 'AVAILABLE')")
    db_conn.commit()
    
    rows, total = execute_filters(db_conn, {"categories": ["Cat X"], "limit": 10, "offset": 0})
    assert len(rows) == 10
    assert total == 30
    
    rows2, _ = execute_filters(db_conn, {"categories": ["Cat X"], "limit": 10, "offset": 10})
    assert len(rows2) == 10
    # ensure no overlap
    ids1 = set([r[0] for r in rows])
    ids2 = set([r[0] for r in rows2])
    assert not ids1.intersection(ids2)

def test_facet_counts_exclude_dim(db_conn):
    c = db_conn.cursor()
    counts = get_facet_counts(db_conn, {"categories": ["Cat B"]})
    # If we filter by Cat B, we only see p2.
    # Verticals for p2 is Supermercado.
    assert counts["verticals"] == ["Supermercado"]
    # But since we EXCLUDE the categories dimension in the category count query, 
    # we should STILL see Cat A and Cat B available for Supermercado.
    # Wait, Cat A and Cat B are in s1. So we should see both.
    assert "Cat A" in counts["categories"]
    assert "Cat B" in counts["categories"]

