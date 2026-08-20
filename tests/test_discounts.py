import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.discounts import calculate_discount

def test_price_final_field_contract():
    # Final price wins when explicitly valid (within threshold)
    p = {"price": 82.0, "real_price": 100.0, "have_discount": True, "discount": 0.20}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert ep == 82.0 # 82 wins over 80 (since it's within threshold margin of error / discrepancy resolution)
    assert dsrc == "explicit"

def test_discount_same_currency():
    p = {"price": 80.0, "real_price": 100.0, "have_discount": True, "discount": 0.20}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert ep == 80.0
    assert erp == 100.0
    assert deff == 20.0
    assert dsrc == "explicit"

def test_cross_currency_discount_rejected():
    # Price is 6.18 USD, real is 117 MXN. Discount is 0.50
    # It should reconstruct to 58.5
    p = {"price": 6.18, "real_price": 117.0, "have_discount": True, "discount": 0.50}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert ep == 58.5
    assert erp == 117.0
    assert deff == 50.0
    assert dsrc == "reconstructed"

def test_real_extreme_discount_allowed():
    # 80% discount
    p = {"price": 20.0, "real_price": 100.0, "have_discount": True, "discount": 0.80}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert ep == 20.0
    assert deff == 80.0
    assert dsrc == "explicit"
    
def test_missing_reference_has_no_discount():
    # original_price <= current
    p = {"price": 100.0, "real_price": 100.0, "have_discount": True, "discount": 0.0}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert deff == 0.0
    assert ep == 100.0
    
def test_price_rounding():
    # 117 * (1 - 0.3) = 81.9
    p = {"price": 11.2, "real_price": 117.0, "have_discount": True, "discount": 0.30}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert ep == 81.9
    assert dsrc == "reconstructed"

def test_direct_discount():
    p = {"price": 20.0, "real_price": 40.0}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert dp == 50.0
    assert deff == 50.0
    assert dsrc == "explicit"

def test_3x2_bundle():
    p = {"price": 10.0, "real_price": 10.0, "discounts_bundle": {"deal": [{"promotion_value": 3, "units_condition": 2}]}}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert abs(deff - 33.33) < 0.1
    assert dsrc == "bundle"

def test_2x1_bundle():
    p = {"price": 10.0, "real_price": 10.0, "discounts_bundle": {"deal": [{"promotion_value": 2, "units_condition": 1}]}}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert deff == 50.0
    assert pt == "NxM"

def test_no_double_count():
    p = {"price": 5.0, "real_price": 10.0, "discounts_bundle": {"deal": [{"promotion_value": 3, "units_condition": 2}]}}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert dp == 50.0
    assert abs(dpromo - 33.33) < 0.1
    assert deff == 50.0
    assert dsrc == "explicit"

