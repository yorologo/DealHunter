from dealhunter.discounts import calculate_discount

def test_existing_2x1_unchanged():
    p = {
        "price": 50.0,
        "real_price": 50.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 2, "units_condition": 1}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "NxM"
    assert deff == 50.0
    assert not extra["is_pro_exclusive"]

def test_existing_3x2_unchanged():
    p = {
        "price": 50.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 3, "units_condition": 2}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "NxM"
    assert abs(deff - 33.33) < 0.1
    assert not extra["is_pro_exclusive"]

def test_standard_50_unchanged():
    p = {
        "price": 50.0,
        "real_price": 50.0,
        "discount": 50.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff == 50.0
    assert ptype == "Direct"

def test_below_50_negative_control():
    p = {
        "price": 70.0,
        "real_price": 50.0,
        "discount": 30.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff == 30.0

def test_progressive_second_unit():
    p = {
        "price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    # 2 units = 1 + 0.5 = 1.5. Cost = 150 instead of 200. Discount = 25%.
    assert ptype == "PROGRESSIVE"
    assert deff == 25.0
    assert ep == 150.0
    assert er == 200.0

def test_progressive_unknown_math():
    p = {
        "price": 100.0,
        "discounts_bundle": {
            "progressive": {"some_complex": "struct"}
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "PROGRESSIVE_UNKNOWN"
    assert deff is None
    assert extra["progressive"] is not None

def test_pro_exclusive_detected():
    p = {
        "price": 100.0,
        "is_prime_exclusive": True,
        "PrimeDiscount": 30.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert extra["is_pro_exclusive"] is True
    assert extra["pro_price"] == 70.0

def test_multiple_promotions_order_independent():
    # Deal 1: 3x2 (33%) vs Deal 2: 2nd unit -50% (25%)
    # NxM wins
    p1 = {
        "price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2}],
            "deal": [{"promotion_value": 3, "units_condition": 2}]
        }
    }
    p2 = {
        "price": 100.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 3, "units_condition": 2}],
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2}]
        }
    }
    _, _, deff1, _, ptype1, _, _, _, _ = calculate_discount(p1)
    _, _, deff2, _, ptype2, _, _, _, _ = calculate_discount(p2)
    assert deff1 == deff2
    assert ptype1 == ptype2 == "NxM"

def test_promotion_limits_preserved():
    p = {
        "price": 100.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 2, "units_condition": 1, "limit": 2}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert extra["limit"] == 2
