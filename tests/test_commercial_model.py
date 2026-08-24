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
    assert not extra["has_pro_offer"]

def test_public_and_pro_coexist():
    p = {
        "price": 80.0,
        "real_price": 100.0,
        "have_discount": True,
        "discount": 0.20,
        "is_prime_exclusive": True,
        "PrimeDiscount": 40.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    # Public channel
    assert deff == 20.0
    assert ptype == "Direct"
    # Pro channel
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 40.0
    assert extra["pro_discount_effective"] == 60.0

def test_pro_only_60():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "is_prime_exclusive": True,
        "PrimeDiscount": 60.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff is None or deff == 0.0 # Public effective discount shouldn't exist
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 40.0
    assert extra["pro_discount_effective"] == 60.0
    assert extra["pro_promo_type"] == "Direct"

def test_public_nxm_pro_price_coexist():
    p = {
        "price": 50.0,
        "real_price": 50.0,
        "discounts_bundle": {
            "deal": [{"promotion_value": 3, "units_condition": 2}]
        },
        "is_pro_exclusive": True,
        "PrimeDiscount": 10.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "NxM"
    assert abs(deff - 33.33) < 0.1
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 40.0
    assert extra["pro_discount_effective"] == 20.0

def test_public_progressive_pro_coexist():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2}]
        },
        "is_pro_exclusive": True,
        "PrimeDiscount": 40.0
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert ptype == "PROGRESSIVE"
    assert deff == 25.0
    assert extra["has_pro_offer"] is True
    assert extra["pro_price"] == 60.0
    assert extra["pro_discount_effective"] == 40.0

def test_pro_progressive():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 2, "is_pro_exclusive": True}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff is None or deff == 0.0
    assert extra["has_pro_offer"] is True
    assert extra["pro_discount_effective"] == 25.0
    assert extra["pro_promo_type"] == "PROGRESSIVE"

def test_promotion_ordering():
    # Deal 1: Pro 50%, Deal 2: Public 20%
    p = {
        "price": 80.0,
        "real_price": 100.0,
        "discount": 0.20,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": 50, "units_condition": 1, "is_pro_exclusive": True}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff == 20.0
    assert ptype == "Direct"
    assert extra["pro_discount_effective"] == 50.0

def test_malformed_pro_does_not_contaminate_public():
    p = {
        "price": 100.0,
        "real_price": 100.0,
        "discounts_bundle": {
            "percentage_unit": [{"promotion_value": "abc", "units_condition": 2, "is_pro_exclusive": True}]
        }
    }
    dp, dpromo, deff, dsrc, ptype, plab, ep, er, extra = calculate_discount(p)
    assert deff is None or deff == 0.0

