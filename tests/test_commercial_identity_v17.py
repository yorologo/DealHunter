import sqlite3

from dealhunter.commerce import classify_store
from dealhunter.db import CURRENT_SCHEMA_VERSION, setup_db
from dealhunter.query_layer import build_faceted_query
from tests.helpers.db import insert_observation, insert_product, insert_store


def _rows(conn, filters):
    query, count_query, params = build_faceted_query(filters)
    rows = conn.execute(query, params).fetchall()
    count = conn.execute(count_query, params).fetchone()[0]
    return rows, count


def test_schema_v17_commercial_and_browse_contract(current_schema_db):
    assert CURRENT_SCHEMA_VERSION >= 17
    tables = {
        r[0]
        for r in current_schema_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"merchants", "merchant_locations", "browse_nodes", "browse_mappings"} <= tables

    store_cols = {
        r[1] for r in current_schema_db.execute("PRAGMA table_info(stores)")
    }
    assert {"merchant_id", "location_id", "commerce_type", "catalog_domain"} <= store_cols

    index_cols = [
        r[2]
        for r in current_schema_db.execute("PRAGMA index_info(idx_obs_provider_history)")
    ]
    assert index_cols == ["provider", "store_id", "product_id", "timestamp", "id"]


def test_structured_commerce_mapping_never_uses_display_name():
    assert classify_store("RESTAURANT") == ("RESTAURANT", "MENU")
    assert classify_store("GROCERY") == ("SUPERMARKET", "RETAIL")
    assert classify_store("Farmatodo") == ("PHARMACY", "RETAIL")
    assert classify_store("mystery", display_name="Farmacia Super Restaurante") == (
        "UNKNOWN",
        "UNKNOWN",
    )


def test_commercial_filters_are_or_within_and_across_dimensions(current_schema_db):
    conn = current_schema_db
    conn.execute(
        "INSERT INTO merchants (merchant_id, name, source) VALUES ('m1', 'Merchant One', 'reviewed')"
    )
    conn.execute(
        "INSERT INTO merchant_locations (location_id, merchant_id, name, source) "
        "VALUES ('l1', 'm1', 'North', 'reviewed'), ('l2', 'm1', 'South', 'reviewed')"
    )
    insert_store(conn, "r1", name="Rappi North", provider="rappi")
    insert_store(conn, "u1", name="Uber South", provider="uber_eats")
    insert_store(conn, "r2", name="Other", provider="rappi")
    conn.execute(
        "UPDATE stores SET merchant_id='m1', location_id='l1', commerce_type='SUPERMARKET', catalog_domain='RETAIL' "
        "WHERE provider='rappi' AND store_id='r1'"
    )
    conn.execute(
        "UPDATE stores SET merchant_id='m1', location_id='l2', commerce_type='SUPERMARKET', catalog_domain='RETAIL' "
        "WHERE provider='uber_eats' AND store_id='u1'"
    )
    conn.execute(
        "UPDATE stores SET commerce_type='PHARMACY', catalog_domain='RETAIL' "
        "WHERE provider='rappi' AND store_id='r2'"
    )
    for provider, store, product, brand in [
        ("rappi", "r1", "p1", "Logitech"),
        ("uber_eats", "u1", "p2", "Razer"),
        ("rappi", "r2", "p3", "Other"),
    ]:
        insert_product(conn, product, store, brand=brand, provider=provider)
        insert_observation(
            conn,
            run_id=f"run-{product}",
            store_id=store,
            product_id=product,
            price=100,
            provider=provider,
            availability="AVAILABLE",
        )
    conn.commit()

    rows, count = _rows(
        conn,
        {
            "merchant_ids": ["m1"],
            "location_ids": ["l1", "l2"],
            "providers": ["rappi", "uber_eats"],
            "commerce_types": ["SUPERMARKET"],
            "catalog_domains": ["RETAIL"],
            "brands": ["Logitech", "Razer"],
        },
    )
    assert count == 2
    assert {row[0] for row in rows} == {"p1", "p2"}

    rows, count = _rows(
        conn,
        {"merchant_ids": ["m1"], "exclude_location_ids": ["l2"]},
    )
    assert count == 1
    assert rows[0][0] == "p1"


def test_browse_taxonomy_mapping_and_unclassified(current_schema_db):
    conn = current_schema_db
    insert_store(conn, "s1", provider="rappi")
    for product in ("mapped", "unmapped"):
        insert_product(conn, product, "s1", provider="rappi")
        insert_observation(
            conn,
            run_id=f"run-{product}",
            store_id="s1",
            product_id=product,
            price=10,
            provider="rappi",
            availability="AVAILABLE",
        )
    conn.execute(
        "INSERT INTO product_memberships "
        "(provider, store_id, product_id, raw_type, raw_name, path, source, semantic_type) "
        "VALUES ('rappi','s1','mapped','corridor','Teclados','[\"Electrónica\", \"Teclados\"]','provider','CATEGORY')"
    )
    conn.execute(
        "INSERT INTO browse_nodes (browse_node_id, parent_id, level, name, active) VALUES "
        "('electronics',NULL,'DEPARTMENT','Electrónica',1),"
        "('computing','electronics','SECTION','Computación',1),"
        "('keyboards','computing','CATEGORY','Teclados',1)"
    )
    conn.execute(
        "INSERT INTO browse_mappings "
        "(provider, raw_type, raw_name, raw_path, browse_node_id, source) "
        "VALUES ('rappi','corridor','Teclados','[\"Electrónica\", \"Teclados\"]','keyboards','reviewed')"
    )
    conn.commit()

    rows, count = _rows(conn, {"browse_node_ids": ["electronics"]})
    assert count == 1
    assert rows[0][0] == "mapped"

    rows, count = _rows(conn, {"browse_node_ids": ["UNCLASSIFIED"]})
    assert count == 1
    assert rows[0][0] == "unmapped"


def test_unknown_existing_store_does_not_get_merchant_or_name_based_commerce(tmp_path):
    path = tmp_path / "current.db"
    conn = setup_db(str(path))
    conn.execute(
        "INSERT INTO stores (provider, store_id, name, type, vertical) "
        "VALUES ('rappi','s1','Farmacia Super Restaurante','mystery','unknown')"
    )
    conn.commit()
    row = conn.execute(
        "SELECT merchant_id, location_id, commerce_type, catalog_domain FROM stores "
        "WHERE provider='rappi' AND store_id='s1'"
    ).fetchone()
    assert row == (None, None, "UNKNOWN", "UNKNOWN")
    conn.close()


def test_new_facets_are_contextual_and_provider_safe(current_schema_db):
    from dealhunter.query_layer import get_facet_counts

    conn = current_schema_db
    conn.execute("INSERT INTO merchants (merchant_id, name, source) VALUES ('m1','Merchant One','reviewed')")
    conn.execute("INSERT INTO merchant_locations (location_id, merchant_id, name, source) VALUES ('l1','m1','North','reviewed'),('l2','m1','South','reviewed')")
    for provider, store_id, location_id, brand in [
        ('rappi', 'r1', 'l1', 'Logitech'),
        ('uber_eats', 'u1', 'l2', 'Razer'),
    ]:
        insert_store(conn, store_id, name=location_id, provider=provider)
        conn.execute(
            "UPDATE stores SET merchant_id='m1', location_id=?, commerce_type='SUPERMARKET', catalog_domain='RETAIL' WHERE provider=? AND store_id=?",
            (location_id, provider, store_id),
        )
        insert_product(conn, f'p-{store_id}', store_id, brand=brand, provider=provider)
        insert_observation(
            conn,
            run_id=f'run-{store_id}',
            store_id=store_id,
            product_id=f'p-{store_id}',
            price=100,
            provider=provider,
            availability='AVAILABLE',
        )
    conn.commit()

    facets = get_facet_counts(
        conn,
        {
            'merchant_ids': ['m1'],
            'commerce_types': ['SUPERMARKET'],
            'catalog_domains': ['RETAIL'],
        },
    )
    assert facets['merchants'] == [{'id': 'm1', 'name': 'Merchant One'}]
    assert {item['id'] for item in facets['locations']} == {'l1', 'l2'}
    assert facets['commerce_types'] == ['SUPERMARKET']
    assert facets['catalog_domains'] == ['RETAIL']
    assert facets['brands'] == ['Logitech', 'Razer']

    facets = get_facet_counts(conn, {'providers': ['rappi']})
    assert {item['id'] for item in facets['locations']} == {'l1'}
    assert facets['brands'] == ['Logitech']


def test_browse_facets_return_only_mapped_nodes_in_scope(current_schema_db):
    from dealhunter.query_layer import get_facet_counts

    conn = current_schema_db
    insert_store(conn, 's1', provider='rappi')
    insert_product(conn, 'p1', 's1', provider='rappi')
    insert_observation(conn, run_id='run1', store_id='s1', product_id='p1', price=10, provider='rappi', availability='AVAILABLE')
    conn.execute("INSERT INTO product_memberships (provider,store_id,product_id,raw_type,raw_name,path,source,semantic_type) VALUES ('rappi','s1','p1','corridor','Teclados','[\"Teclados\"]','provider','CATEGORY')")
    conn.execute("INSERT INTO browse_nodes (browse_node_id,parent_id,level,name) VALUES ('electronics',NULL,'DEPARTMENT','Electrónica'),('keyboards','electronics','CATEGORY','Teclados')")
    conn.execute("INSERT INTO browse_mappings (provider,raw_type,raw_name,raw_path,browse_node_id,source) VALUES ('rappi','corridor','Teclados','[\"Teclados\"]','keyboards','reviewed')")
    conn.commit()

    facets = get_facet_counts(conn, {})
    assert facets['browse_nodes'] == [
        {'id': 'keyboards', 'parent_id': 'electronics', 'level': 'CATEGORY', 'name': 'Teclados'}
    ]
