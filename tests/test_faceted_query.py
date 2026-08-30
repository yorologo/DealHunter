import pytest
import sqlite3
from dealhunter.query_layer import build_faceted_query, get_facet_counts
from tests.helpers.db import insert_store, insert_store_facet, insert_product, insert_observation, insert_membership

@pytest.fixture
def db_conn(current_schema_db):
    conn = current_schema_db
    
    # Store 1 (vertical: Supermercado, facet: Express)
    insert_store(conn, 's1', name='Store 1', type='market', vertical='Supermercado')
    insert_store_facet(conn, 's1', 'speed', 'Express')
    
    # Store 2 (vertical: Restaurantes, type: restaurants)
    insert_store(conn, 's2', name='Store 2', type='restaurants', vertical='Restaurantes')
    
    # Product 1 (s1): Legacy category 'A', no memberships. Public deal 50%, no pro.
    insert_product(conn, 'p1', 's1', name='Prod 1', category='Cat A')
    insert_observation(conn, run_id='test', store_id='s1', product_id='p1', price=50, original_price=100, discount_effective=50, availability='AVAILABLE', has_pro_offer=0, timestamp='2023-01-01T00:00:00Z')
    
    # Product 2 (s1): Legacy category 'A', but trusted category 'B'. Pro deal 60%, public 10%.
    insert_product(conn, 'p2', 's1', name='Prod 2', category='Cat A')
    insert_observation(conn, run_id='test', store_id='s1', product_id='p2', price=90, original_price=100, discount_effective=10, availability='AVAILABLE', has_pro_offer=1, pro_price=40, pro_discount_effective=60, timestamp='2023-01-01T00:00:00Z')
    insert_membership(conn, 's1', 'p2', raw_type='CATEGORY', raw_name='Cat B', semantic_type='CATEGORY')
    
    # Product 3 (s2): Trusted category 'C', Collection 'Col 1'. No deals.
    insert_product(conn, 'p3', 's2', name='Prod 3', category='Cat A')
    insert_observation(conn, run_id='test', store_id='s2', product_id='p3', price=100, original_price=100, discount_effective=0, availability='AVAILABLE', timestamp='2023-01-01T00:00:00Z')
    insert_membership(conn, 's2', 'p3', raw_type='CATEGORY', raw_name='Cat C', semantic_type='CATEGORY')
    insert_membership(conn, 's2', 'p3', raw_type='COLLECTION', raw_name='Col 1', semantic_type='COLLECTION')
    
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
    # Add another facet to s1
    insert_store_facet(db_conn, 's1', 'food', 'Food')
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
    for i in range(10, 40):
        insert_product(db_conn, f'p{i}', 's2', name=f'Prod {i}', category='Cat X')
        insert_observation(db_conn, run_id='test', store_id='s2', product_id=f'p{i}', price=100, original_price=100, discount_effective=0, availability='AVAILABLE', timestamp='2023-01-01T00:00:00Z')
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


def test_provider_collision_isolated_in_queries_and_facets(db_conn):
    insert_store(
        db_conn, 's1', name='Uber Store 1', type='market',
        vertical='Supermercado', provider='uber_eats',
    )
    insert_store_facet(
        db_conn, 's1', 'speed', 'Uber Only Facet', provider='uber_eats',
    )
    insert_product(
        db_conn, 'p1', 's1', name='Uber Product 1', category='Uber Legacy',
        provider='uber_eats',
    )
    insert_observation(
        db_conn, run_id='uber-test', store_id='s1', product_id='p1',
        price=777, original_price=800, discount_effective=2.875,
        availability='AVAILABLE', timestamp='2023-01-02T00:00:00Z',
        provider='uber_eats',
    )
    insert_membership(
        db_conn, 's1', 'p1', raw_type='CATEGORY', raw_name='Uber Only Category',
        semantic_type='CATEGORY', provider='uber_eats',
    )
    db_conn.commit()

    rows, total = execute_filters(db_conn, {})
    assert total == 4
    assert len(rows) == 4

    rows, total = execute_filters(db_conn, {"providers": ["uber_eats"]})
    assert total == 1
    assert len(rows) == 1
    assert rows[0][2] == 'Uber Product 1'
    assert rows[0][3] == 'Uber Store 1'
    assert rows[0][8] == 777
    assert rows[0][23] == 'uber_eats'

    rows, total = execute_filters(db_conn, {"categories": ["Uber Only Category"]})
    assert total == 1
    assert rows[0][23] == 'uber_eats'

    rows, total = execute_filters(db_conn, {"store_facets": ["Uber Only Facet"]})
    assert total == 1
    assert rows[0][23] == 'uber_eats'

    rows, total = execute_filters(
        db_conn, {"store_identities": [("uber_eats", "s1")]}
    )
    assert total == 1
    assert rows[0][23] == 'uber_eats'

    rappi_facets = get_facet_counts(db_conn, {"providers": ["rappi"]})
    assert "Uber Only Category" not in rappi_facets["categories"]
    assert "Uber Only Facet" not in rappi_facets["store_facets"]
    assert all(store["provider"] == "rappi" for store in rappi_facets["stores"])
    assert all(store["filter_key"].startswith("rappi::") for store in rappi_facets["stores"])
