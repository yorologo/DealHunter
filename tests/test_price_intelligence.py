import pytest
from dealhunter.price_intelligence import compute_price_metrics
from datetime import datetime, timedelta

now = datetime.now()

def make_obs(prices, orig_price=None, days_ago=0, spacing_days=1):
    obs = []
    for i, p in enumerate(prices):
        # space them out by `spacing_days` days
        d = days_ago - ((len(prices) - 1 - i) * spacing_days)
        ts = now + timedelta(days=d)
        obs.append({"price": p, "timestamp": ts, "original_price": orig_price})
    return obs

def test_insufficient_history_one_obs():
    res = compute_price_metrics(make_obs([100]))
    assert res["status"] == "INSUFFICIENT_HISTORY"

def test_insufficient_history_short_time():
    # 3 obs but on the same day
    res = compute_price_metrics(make_obs([100, 100, 100], spacing_days=0))
    assert res["status"] == "INSUFFICIENT_HISTORY"

def test_stable_price_normal():
    res = compute_price_metrics(make_obs([100, 100, 100]))
    assert res["status"] == "NORMAL"
    assert res["price_change"] == 0
    assert res["price_change_percent"] == 0

def test_price_going_up():
    res = compute_price_metrics(make_obs([100, 100, 120]))
    assert res["status"] == "NORMAL"
    assert res["price_change"] == 20
    assert res["price_change_percent"] == pytest.approx(20.0)

def test_new_low():
    res = compute_price_metrics(make_obs([100, 110, 100, 95]))
    assert res["status"] == "NEW_LOW"
    assert res["historical_min"] == 95

def test_real_deal():
    # Median is 100. Price drops to 80 (20% discount vs median 30d)
    # But 80 might also be a new low.
    # To test REAL_DEAL without NEW_LOW, historical min should be lower.
    res = compute_price_metrics(make_obs([70, 100, 100, 100, 80]))
    assert res["status"] == "REAL_DEAL"
    assert res["discount_vs_median_30d"] == pytest.approx(20.0)

def test_good_price():
    # Median is 100. Price drops to 92 (8% discount vs median)
    res = compute_price_metrics(make_obs([90, 100, 100, 100, 92]))
    assert res["status"] == "GOOD_PRICE"
    assert res["discount_vs_median_30d"] == pytest.approx(8.0)

def test_suspicious_reference_price():
    # Median is 100. Max is 110. Original price is 150 (way above max).
    res = compute_price_metrics(make_obs([100, 110, 100], orig_price=150))
    assert res["is_suspicious_reference"] == True
    assert "SUSPICIOUS" in res["reason"]
    
def test_normal_reference_price():
    # Median is 100. Max is 110. Original price is 110.
    res = compute_price_metrics(make_obs([100, 110, 100], orig_price=110))
    assert res["is_suspicious_reference"] == False


# --- NULL price / timestamp regression tests ---

def test_prices_with_none_skipped():
    """[100, None, 90] → uses 100 and 90, no crash."""
    obs = make_obs([100, None, 90])
    res = compute_price_metrics(obs)
    assert res is not None
    assert res["current_price"] == 90
    assert res["historical_min"] == 90
    assert res["historical_max"] == 100
    assert res["previous_price"] == 100  # last valid before current

def test_all_none_prices():
    """[None, None] → no crash, returns None."""
    obs = make_obs([None, None])
    res = compute_price_metrics(obs)
    assert res is None

def test_current_price_none():
    """Last observation has None price → uses last valid price."""
    obs = make_obs([100, 90, None])
    res = compute_price_metrics(obs)
    assert res is not None
    assert res["current_price"] == 90
