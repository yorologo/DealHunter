import pytest
from dealhunter.delivery import matches_canary_watch, format_event

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
