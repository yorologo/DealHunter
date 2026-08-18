import sys
import os

bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'rappi-ofertas'))
namespace = {}
with open(bin_path, 'r') as f:
    exec(f.read(), namespace)

calculate_discount = namespace['calculate_discount']

def test_direct_discount():
    p = {"price": 20.0, "real_price": 40.0}
    dp, dpromo, deff, dsrc, pt, pl, ep, erp = calculate_discount(p)
    assert dp == 50.0
    assert deff == 50.0
    assert dsrc == "price"

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
    assert dsrc == "price"

if __name__ == "__main__":
    test_direct_discount()
    test_3x2_bundle()
    test_2x1_bundle()
    test_no_double_count()
    print("All discount tests passed.")
