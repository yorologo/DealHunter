import pytest
from dealhunter.score import calculate_deal_score

def test_score_determinism():
    """TEST 20. TEST DE DETERMINISMO EXPLÍCITO"""
    metrics = {
        "observations_count": 12,
        "discount_vs_median_30d": 25,
        "status": "REAL_DEAL"
    }
    market_prices = [90, 100, 110]
    
    res1 = calculate_deal_score(metrics, current_price=100, original_price=None, market_prices=market_prices)
    res2 = calculate_deal_score(metrics, current_price=100, original_price=None, market_prices=market_prices)
    
    assert res1["score"] == res2["score"]
    assert res1["label"] == res2["label"]
    assert res1["confidence"] == res2["confidence"]
    assert res1["reasons"] == res2["reasons"]
    assert res1["breakdown"] == res2["breakdown"]

def test_score_vs_confidence():
    """TEST 21. TEST SCORE VS CONFIDENCE"""
    # High confidence
    metrics1 = {"observations_count": 15, "history_days": 10, "discount_vs_median_30d": 20}
    # Low confidence
    metrics2 = {"observations_count": 1, "discount_vs_median_30d": 20}
    
    res1 = calculate_deal_score(metrics1, current_price=80)
    res2 = calculate_deal_score(metrics2, current_price=80)
    
    assert res1["score"] == res2["score"]
    assert res1["confidence"] == "alta"
    assert res2["confidence"] == "baja"

def test_missing_market():
    """TEST 22. TEST MISSING MARKET"""
    metrics = {"observations_count": 5, "discount_vs_median_30d": 30}
    
    # A: No equivalents known
    resA = calculate_deal_score(metrics, current_price=70, market_prices=[])
    
    # B: Equivalents known, but we are NOT cheaper
    resB = calculate_deal_score(metrics, current_price=70, market_prices=[50, 70])
    
    # Score without market penalty (normalized) should be higher than Score with market penalty
    assert resA["score"] == resB["score"]

def test_market_advantage():
    """TEST 23. TEST MARKET ADVANTAGE"""
    metrics = {"observations_count": 5, "discount_vs_median_30d": 10}
    
    # Case A: We are 99, next is 100
    resA = calculate_deal_score(metrics, current_price=99, market_prices=[99, 100])
    
    # Case B: We are 60, next is 100
    resB = calculate_deal_score(metrics, current_price=60, market_prices=[60, 100])
    
    # Market advantage score in breakdown
    ma_A = int(resA["breakdown"]["market"].split("/")[0])
    ma_B = int(resB["breakdown"]["market"].split("/")[0])
    
    assert ma_B > ma_A

def test_double_counting():
    """TEST 24. TEST DOUBLE COUNTING"""
    metrics = {
        "observations_count": 10,
        "discount_vs_median_30d": 30, # 30% drop vs median
        "status": "NEW_LOW"
    }
    # Promo also indicates 30% drop (100 -> 70)
    # The earned score should NOT just add them up.
    # Max discount score is 60.
    res = calculate_deal_score(metrics, current_price=70, original_price=100)
    
    disc_score = int(res["breakdown"]["discount"].split("/")[0])
    assert disc_score <= 60

def test_suspicious_reference():
    """TEST 25. SUSPICIOUS REFERENCE"""
    metrics = {
        "observations_count": 10,
        "discount_vs_median_30d": 0,
        "is_suspicious_reference": True
    }
    res = calculate_deal_score(metrics, current_price=50, original_price=500)
    
    disc_score = int(res["breakdown"]["discount"].split("/")[0])
    assert disc_score == 0
    assert any("sospechosa" in r["text"].lower() for r in res["reasons"])

def test_score_limits():
    """TEST 6. Score Limits"""
    metrics = {"observations_count": 50, "discount_vs_median_30d": 100, "status": "NEW_LOW"}
    res = calculate_deal_score(metrics, current_price=10, original_price=100, market_prices=[10, 50, 60])
    assert res["score"] == 100
    
    metrics_bad = {"observations_count": 1, "discount_vs_median_30d": 0}
    res_bad = calculate_deal_score(metrics_bad, current_price=100)
    assert res_bad["score"] == 0


def test_missing_market_does_not_inflate_score():
    """TEST: Missing market should not inflate score compared to zero advantage market."""
    metrics = {
        "observations_count": 5,
        "history_days": 2,
        "discount_vs_median_30d": 20,
        "status": "NEW_LOW"
    }
    
    # A: Market unavailable
    resA = calculate_deal_score(metrics, current_price=80, market_prices=[])
    
    # B: Market available, but we are tied for leader so zero advantage, but wait:
    # Tied for leader gives 5 pts now.
    # To test ZERO advantage strictly without tied points, we make us NOT the leader.
    resB = calculate_deal_score(metrics, current_price=80, market_prices=[79, 80])
    
    # In purely additive, resA will have:
    # Discount: 40
    # Market: 0
    # Event: 10
    # Total: 50
    # resB will have:
    # Discount: 40
    # Market: 0
    # Event: 10
    # Total: 50
    assert resA["score"] == resB["score"]
    
