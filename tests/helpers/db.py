import sqlite3
from dealhunter.db import setup_db
import pytest

def create_current_schema_db(db_path):
    """Creates a DB using the current canonical schema."""
    conn = setup_db(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def insert_store(conn, store_id, name="Test Store", type="market", brand=None, vertical=None, status="ACTIVE", provider="rappi"):
    conn.execute(
        "INSERT INTO stores (provider, store_id, name, type, brand, vertical, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (provider, store_id, name, type, brand, vertical, status)
    )

def insert_product(conn, product_id, store_id, name="Test Product", brand=None, 
                   category=None, category_source="unknown", has_toppings=0,
                   quantity=None, unit=None, normalized_quantity=None, normalized_unit=None, 
                   fingerprint=None, pack_count=None, image=None, normalized_name=None, provider="rappi"):
    conn.execute(
        """INSERT INTO products (
            provider, product_id, store_id, name, brand, category, category_source, has_toppings,
            quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count, image, normalized_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (provider, product_id, store_id, name, brand, category, category_source, has_toppings,
         quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count, image, normalized_name)
    )

def insert_observation(conn, run_id, store_id, product_id, price, original_price=None, stock=1, 
                       timestamp="2024-01-01T12:00:00Z", discount_price=None, discount_promotion=None, 
                       discount_effective=None, discount_source=None, promotion_type=None, 
                       promotion_label=None, availability="IN_STOCK", query_term=None,
                       has_pro_offer=None, pro_price=None, pro_discount_effective=None, limit_info=None, provider="rappi"):
    conn.execute(
        """INSERT INTO observations (
            run_id, provider, store_id, product_id, price, original_price, stock, timestamp, 
            discount_price, discount_promotion, discount_effective, discount_source, 
            promotion_type, promotion_label, availability, query_term,
            has_pro_offer, pro_price, pro_discount_effective, limit_info
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, provider, store_id, product_id, price, original_price, stock, timestamp,
         discount_price, discount_promotion, discount_effective, discount_source,
         promotion_type, promotion_label, availability, query_term,
         has_pro_offer, pro_price, pro_discount_effective, limit_info)
    )

def insert_store_facet(conn, store_id, facet_type, raw_value, source="test", last_seen="2024-01-01T12:00:00Z", provider="rappi"):
    conn.execute(
        "INSERT INTO store_facets (provider, store_id, facet_type, raw_value, source, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
        (provider, store_id, facet_type, raw_value, source, last_seen)
    )

def insert_membership(conn, store_id, product_id, raw_type, raw_name, raw_id=None, path=None, source="test", last_seen="2024-01-01T12:00:00Z", semantic_type=None, semantic_reason=None, provider="rappi"):
    conn.execute(
        """INSERT INTO product_memberships (
            provider, store_id, product_id, raw_type, raw_name, raw_id, path, source, last_seen, semantic_type, semantic_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (provider, store_id, product_id, raw_type, raw_name, raw_id, path, source, last_seen, semantic_type, semantic_reason)
    )

def insert_run(conn, run_id, started_at, finished_at=None, lat=None, lng=None, radius=None, vertical=None, status="SUCCESS", crawler_mode=None, coverage_complete=0, run_metadata=None, source="CLI"):
    conn.execute(
        """INSERT INTO runs (
            run_id, started_at, finished_at, lat, lng, radius, vertical, status, crawler_mode, coverage_complete, run_metadata, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, started_at, finished_at, lat, lng, radius, vertical, status, crawler_mode, coverage_complete, run_metadata, source)
    )

def insert_alert(conn, product_id, store_id, alert_type, triggered_at="2024-01-01T12:00:00Z", provider="rappi"):
    conn.execute(
        "INSERT INTO alerts (provider, product_id, store_id, alert_type, triggered_at) VALUES (?, ?, ?, ?, ?)",
        (provider, product_id, store_id, alert_type, triggered_at)
    )

def insert_watchlist(conn, query, enabled=1, target_price=None):
    conn.execute(
        "INSERT INTO watchlist (query, enabled, target_price) VALUES (?, ?, ?)",
        (query, enabled, target_price)
    )
