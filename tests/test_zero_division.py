import pytest
from dealhunter.price_intelligence import compute_price_metrics, compare_eligible_offers

def test_non_positive_prices():
    obs = [
        {"price": 100, "original_price": None, "timestamp": None},
        {"price": 90, "original_price": None, "timestamp": None},
        {"price": 0, "original_price": None, "timestamp": None}
    ]
    # compute_price_metrics should use 100 and 90, ignoring 0
    metrics = compute_price_metrics(obs)
    # The current valid price is 90
    assert metrics["current_price"] == 90
    assert metrics["previous_price"] == 100

    obs2 = [
        {"price": 0, "original_price": None, "timestamp": None}
    ]
    metrics2 = compute_price_metrics(obs2)
    assert metrics2 is None

    obs3 = [
        {"price": 100, "original_price": None, "timestamp": None},
        {"price": -1, "original_price": None, "timestamp": None},
        {"price": 90, "original_price": None, "timestamp": None}
    ]
    metrics3 = compute_price_metrics(obs3)
    assert metrics3["previous_price"] == 100

def test_compare_eligible_offers_zero_price():
    offers = [
        {"provider": "rappi", "price": 0, "store_id": "s1", "product_id": "p1"},
        {"provider": "uber", "price": 100, "store_id": "s2", "product_id": "p2"}
    ]
    # Only uber should be eligible
    canonical = {"quantity": 1, "unit": "kg"}
    result = compare_eligible_offers(canonical, offers)
    assert len(result["ranking"]) == 1
    assert result["best_offer"]["provider"] == "uber"

