from dealhunter.score import calculate_deal_score

def test_score_excellent_history():
    metrics = {
        "status": "NEW_LOW",
        "observations_count": 12,
        "discount_vs_median_30d": 35,
        "is_suspicious_reference": False
    }
    res = calculate_deal_score(metrics, 100, 150, 100, 5)
    assert res["score"] >= 90
    assert "Excepcional" in res["label"]
    assert res["confidence"] == "alta"

def test_score_suspicious_discount():
    metrics = {
        "status": "NORMAL",
        "observations_count": 8,
        "discount_vs_median_30d": 0,
        "is_suspicious_reference": True
    }
    # 90% "discount" but suspicious
    res = calculate_deal_score(metrics, 10, 100, 10, 1)
    # Evidence=7, Hist=0, Promo=0, Timing=0, Market=10 -> Total 17
    assert res["score"] < 50
    assert any("descartado" in r["text"].lower() for r in res["reasons"])

def test_score_insufficient_history():
    metrics = {
        "status": "INSUFFICIENT_HISTORY",
        "observations_count": 1,
        "discount_vs_median_30d": 0
    }
    res = calculate_deal_score(metrics, 80, 100, 80, 1)
    # Evidence=2, Hist=0, Promo=20, Timing=0, Market=5 -> Total 27
    assert res["confidence"] == "baja"
    assert res["score"] < 50

def test_score_new_low_monotonicity():
    metrics_normal = {
        "status": "NORMAL",
        "observations_count": 10,
        "discount_vs_median_30d": 15
    }
    metrics_new_low = dict(metrics_normal, status="NEW_LOW")
    
    score_normal = calculate_deal_score(metrics_normal, 100, None, None, 1)["score"]
    score_new_low = calculate_deal_score(metrics_new_low, 100, None, None, 1)["score"]
    assert score_new_low > score_normal

def test_score_price_worse():
    metrics = {
        "status": "NORMAL",
        "observations_count": 10,
        "discount_vs_median_30d": 20
    }
    # Better price in market vs Worse price in market
    score_better = calculate_deal_score(metrics, 100, None, 100, 3)["score"]
    score_worse = calculate_deal_score(metrics, 120, None, 100, 3)["score"]
    assert score_worse < score_better

def test_score_limits():
    metrics = {
        "status": "NEW_LOW",
        "observations_count": 100,
        "discount_vs_median_30d": 100
    }
    res = calculate_deal_score(metrics, 10, 100, 10, 10)
    assert res["score"] == 100

def test_score_determinism():
    metrics = {"status": "REAL_DEAL", "observations_count": 15, "discount_vs_median_30d": 25}
    res1 = calculate_deal_score(metrics, 100, 150, 100, 4)
    res2 = calculate_deal_score(metrics, 100, 150, 100, 4)
    assert res1 == res2
