import pytest
from dealhunter.delivery import matches_canary_watch, format_event
from tests.helpers.db import insert_product, insert_store

def test_matches_canary_watch_new_deal():
    # 50% discount should match
    assert matches_canary_watch({
        'event_type': 'NEW_DEAL',
        'after_value': '50.0'
    }) == True

    # 40% discount should NOT match
    assert matches_canary_watch({
        'event_type': 'NEW_DEAL',
        'after_value': '40.0'
    }) == False

def test_matches_canary_watch_pro_deal():
    # Pro 50% discount should match
    assert matches_canary_watch({
        'event_type': 'PRO_DEAL_APPEARED',
        'metadata': {'pro_discount_effective': 50.0}
    }) == True

def test_format_event_new_deal():
    ev = {
        'event_type': 'NEW_DEAL',
        'after_value': '55.5',
        'product_id': 'p1',
        'store_id': 's1'
    }
    msg = format_event(ev)
    assert "55.5%" in msg
    assert "p1" in msg


def test_format_event_uses_provider_scoped_names(current_schema_db):
    insert_store(
        current_schema_db, 'shared', name='Rappi Store', provider='rappi'
    )
    insert_store(
        current_schema_db, 'shared', name='Uber Store', provider='uber_eats'
    )
    insert_product(
        current_schema_db, 'shared-product', 'shared', name='Rappi Product',
        provider='rappi',
    )
    insert_product(
        current_schema_db, 'shared-product', 'shared', name='Uber Product',
        provider='uber_eats',
    )
    current_schema_db.commit()

    msg = format_event(
        {
            'provider': 'uber_eats',
            'event_type': 'NEW_DEAL',
            'after_value': '50.0',
            'product_id': 'shared-product',
            'store_id': 'shared',
        },
        current_schema_db.cursor(),
    )

    assert 'Uber Product' in msg
    assert 'Uber Store' in msg
    assert 'Rappi Product' not in msg
    assert 'Rappi Store' not in msg
