import pytest
from dealhunter.price_intelligence import compute_price_metrics

def test_promotion_vs_real_value():
    # Tienda A: 50% discount announced (actual 100, original 200). Median 102.
    obs_a = [
        {"price": 95, "original_price": 95, "timestamp": "t0"},
        {"price": 104, "original_price": 104, "timestamp": "t1"},
        {"price": 102, "original_price": 102, "timestamp": "t2"},
        {"price": 100, "original_price": 200, "timestamp": "t3"},
    ]
    
    # Tienda B: 20% discount announced (actual 80, original 100). Median 100.
    obs_b = [
        {"price": 70, "original_price": 70, "timestamp": "t0"},
        {"price": 100, "original_price": 100, "timestamp": "t1"},
        {"price": 100, "original_price": 100, "timestamp": "t1.5"},
        {"price": 100, "original_price": 100, "timestamp": "t2"},
        {"price": 80, "original_price": 100, "timestamp": "t3"},
    ]
    
    # We will simulate dates to pass the delta_days > 1 rule
    from datetime import datetime, timedelta
    now = datetime.now()
    for i, o in enumerate(obs_a):
        o["timestamp"] = now - timedelta(days=5-i*2)
    for i, o in enumerate(obs_b):
        o["timestamp"] = now - timedelta(days=5-i*2)
        
    metrics_a = compute_price_metrics(obs_a)
    metrics_b = compute_price_metrics(obs_b)
    
    # A is NORMAL (discount vs median is small) and SUSPICIOUS
    assert metrics_a["status"] == "NORMAL"
    assert metrics_a["is_suspicious_reference"] == True
    
    # B is REAL_DEAL (20% discount vs median 100)
    assert metrics_b["status"] == "REAL_DEAL"
    
    # We prove that if we compared A and B solely by current price, B wins (80 < 100)
    # despite A screaming "50% off!"
    assert metrics_b["current_price"] < metrics_a["current_price"]

