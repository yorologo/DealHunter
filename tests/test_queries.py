from unittest.mock import patch
import sqlite3
import pytest
from dealhunter.web.queries import (
    get_catalog,
    get_deals,
    get_product_detail,
    get_stores,
    search_local,
)
from dealhunter.historico import compare_with_anchor

from tests.helpers.db import insert_store, insert_product, insert_observation, insert_alert, insert_watchlist
import sqlite3

def test_get_product_detail_mapping(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    
    insert_store(conn, 's1', 'MyStore', 'market', 'BrandStore')
    insert_product(conn, 'p1', 's1', 'Test Product', 'MyBrand', 'MyCat', quantity=500, unit='g', normalized_quantity=0.5, normalized_unit='kg', pack_count=1, fingerprint='fp', has_toppings=0)
    insert_observation(conn, run_id='r1', store_id='s1', product_id='p1', price=100.0, original_price=150.0, stock=10, timestamp='2023-01-01T12:00:00Z', discount_effective=0, discount_promotion=0, discount_price=0, availability='AVAILABLE')
    conn.commit()
    conn.close()
    
    p = get_product_detail(current_schema_db_path, 'rappi', 's1', 'p1')
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

@patch("dealhunter.config.get_merged_config")
def test_get_catalog_sorting(mock_config, current_schema_db_path):
    mock_config.return_value = {
        "provider": {"rappi": {"enabled": True}, "uber_eats": {"enabled": True}},
        "comparison": {"inactive_membership_offers": "show_but_exclude"},
        "membership": {"rappi_pro": {"status": "active"}, "uber_one": {"status": "active"}}
    }
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


@patch("dealhunter.config.get_merged_config")
def test_web_queries_keep_colliding_provider_ids_isolated(mock_config, current_schema_db_path):
    mock_config.return_value = {
        "provider": {"rappi": {"enabled": True}, "uber_eats": {"enabled": True}},
        "membership": {"rappi_pro": {"status": "active"}, "uber_one": {"status": "active"}}
    }
    conn = sqlite3.connect(current_schema_db_path)
    insert_store(conn, 'shared', 'Rappi Shared', 'market', provider='rappi')
    insert_store(conn, 'shared', 'Uber Shared', 'market', provider='uber_eats')
    insert_product(
        conn, 'same-product', 'shared', 'Rappi Product', 'Rappi Brand', 'Rappi Cat',
        normalized_quantity=1.0, normalized_unit='kg', provider='rappi',
    )
    insert_product(
        conn, 'same-product', 'shared', 'Uber Product', 'Uber Brand', 'Uber Cat',
        normalized_quantity=2.0, normalized_unit='kg', provider='uber_eats',
    )
    insert_observation(
        conn, run_id='shared-run', store_id='shared', product_id='same-product',
        price=100.0, original_price=120.0, timestamp='2026-08-01T12:00:00Z',
        availability='AVAILABLE', provider='rappi',
    )
    insert_observation(
        conn, run_id='shared-run', store_id='shared', product_id='same-product',
        price=999.0, original_price=1000.0, timestamp='2026-08-01T13:00:00Z',
        availability='AVAILABLE', provider='uber_eats',
    )
    insert_alert(
        conn, 'same-product', 'shared', 'NEW_LOW', provider='rappi',
    )
    insert_alert(
        conn, 'same-product', 'shared', 'PRICE_DROP', provider='uber_eats',
    )
    conn.execute("UPDATE alerts SET price = 100 WHERE provider = 'rappi'")
    conn.execute("UPDATE alerts SET price = 999 WHERE provider = 'uber_eats'")
    conn.commit()
    conn.close()

    detail = get_product_detail(
        current_schema_db_path, 'rappi', 'shared', 'same-product'
    )
    assert detail['product_name'] == 'Rappi Product'
    assert [alert['alert_type'] for alert in detail['alerts']] == ['NEW_LOW']

    catalog = get_catalog(
        current_schema_db_path, {"providers": ["rappi"]}, "price_asc", 1, 10
    )
    assert catalog['total'] == 1
    assert catalog['items'][0]['provider'] == 'rappi'
    assert catalog['items'][0]['current_price'] == 100.0
    assert catalog['items'][0]['metrics']['current_price'] == 100.0

    uber_catalog = get_catalog(
        current_schema_db_path, {"store": "uber_eats::shared"}, "price_asc", 1, 10
    )
    assert uber_catalog['total'] == 1
    assert uber_catalog['items'][0]['provider'] == 'uber_eats'
    assert uber_catalog['items'][0]['current_price'] == 999.0

    results = search_local(
        current_schema_db_path, 'Product', {"providers": ["uber_eats"]}
    )
    assert [product['provider'] for product in results['products']] == ['uber_eats']
    assert [product['name'] for product in results['products']] == ['Uber Product']

    stores = get_stores(
        current_schema_db_path, filters={"providers": ["uber_eats"]}
    )
    assert [(store['provider'], store['name']) for store in stores] == [
        ('uber_eats', 'Uber Shared')
    ]

    rappi_deals = get_deals(
        current_schema_db_path,
        {"providers": ["rappi"], "tab": "PRICE_DROP"},
        "recent",
        1,
    )
    uber_deals = get_deals(
        current_schema_db_path,
        {"providers": ["uber_eats"], "tab": "PRICE_DROP"},
        "recent",
        1,
    )
    assert rappi_deals['total'] == 0
    assert uber_deals['total'] == 1
    assert uber_deals['items'][0]['data']['provider'] == 'uber_eats'


def test_anchor_compare_uses_provider_in_product_and_store_identity(current_schema_db_path):
    conn = sqlite3.connect(current_schema_db_path)
    for provider, store_id, store_name in (
        ('rappi', 's1', 'Rappi Anchor Store'),
        ('uber_eats', 's1', 'Uber Collision Store'),
        ('rappi', 's2', 'Rappi Match Store'),
        ('uber_eats', 's2', 'Uber Match Store'),
    ):
        insert_store(conn, store_id, store_name, 'market', provider=provider)

    common = {
        'name': 'Coca Cola Original 2 L',
        'brand': 'Coca Cola',
        'normalized_name': 'coca cola original 2 l',
        'quantity': 2,
        'unit': 'L',
        'normalized_quantity': 2000,
        'normalized_unit': 'ml',
        'pack_count': 1,
        'fingerprint': 'coca-original-2l',
    }
    insert_product(conn, 'p1', 's1', provider='rappi', **common)
    insert_product(
        conn, 'p1', 's1', name='Coca Cola Zero 600 ml', brand='Coca Cola',
        normalized_name='coca cola zero 600 ml', quantity=600, unit='ml',
        normalized_quantity=600, normalized_unit='ml', pack_count=1,
        fingerprint='coca-zero-600', provider='uber_eats',
    )
    insert_product(conn, 'p2', 's2', provider='rappi', **common)
    insert_product(conn, 'p2', 's2', provider='uber_eats', **common)

    for provider, store_id, product_id, price in (
        ('rappi', 's1', 'p1', 30),
        ('uber_eats', 's1', 'p1', 5),
        ('rappi', 's2', 'p2', 28),
        ('uber_eats', 's2', 'p2', 27),
    ):
        insert_observation(
            conn, run_id='compare-run', store_id=store_id, product_id=product_id,
            price=price, timestamp='2026-08-01T12:00:00Z', provider=provider,
        )
    conn.commit()
    conn.close()

    result = compare_with_anchor(current_schema_db_path, 'rappi', 's1', 'p1')
    identities = {
        (match['provider'], match['store_id'], match['product_id'])
        for match in result['matches']
    }

    assert ('rappi', 's1', 'p1') in identities
    assert ('uber_eats', 's1', 'p1') not in identities
    assert ('rappi', 's2', 'p2') in identities
    assert ('uber_eats', 's2', 'p2') in identities
