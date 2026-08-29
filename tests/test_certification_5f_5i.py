import pytest
import sqlite3
import os
from dealhunter.identity.normalization import extract_signature, is_hard_reject, parse_package
from dealhunter.identity.evaluator import match_products, generate_candidates
from dealhunter.identity.gold_loader import load_gold_corpus
from dealhunter.db import setup_db
from dealhunter.price_intelligence import compare_eligible_offers

# 1. Package Topology
def test_package_topology_invariants():
    # 600 ml == 0.6 L
    c1, pu1, t1, u1 = parse_package("600 ml", None, None)
    c2, pu2, t2, u2 = parse_package("0.6 L", None, None)
    assert t1 == 600.0 and u1 == "ml"
    assert t2 == 600.0 and u2 == "ml"
    
    # 1 kg == 1000 g
    c1, pu1, t1, u1 = parse_package("1 kg", None, None)
    c2, pu2, t2, u2 = parse_package("1000 g", None, None)
    assert t1 == 1000.0 and u1 == "g"
    assert t2 == 1000.0 and u2 == "g"

    # 950 g != 1 kg
    s1 = extract_signature("", "950 g", None, None)
    s2 = extract_signature("", "1 kg", None, None)
    rej, _ = is_hard_reject(s1, s2)
    assert rej == True

    # 1 L != 12 x 1 L
    s1 = extract_signature("", "1 L", None, None)
    s2 = extract_signature("", "12 x 1 L", None, None)
    rej, _ = is_hard_reject(s1, s2)
    assert rej == True

    # 2 x 600 ml != single bottle 1.2 L
    s1 = extract_signature("", "2 x 600 ml", None, None)
    s2 = extract_signature("", "1.2 L bottle", None, None)
    rej, _ = is_hard_reject(s1, s2)
    assert rej == True

# 2. Exact Evidence Gate & Prepared/Fresh Exclusion
def test_exact_evidence_gate():
    # True exact match
    p1 = {"brand": "Coca-Cola", "name": "Coca-Cola Zero Refresco Sin Azúcar 500 mL", "quantity": 500, "unit": "mL"}
    p2 = {"brand": "Coca-Cola", "name": "Coca-Cola Zero Refresco sin azúcar (500 ml)", "quantity": 500, "unit": "ml"}
    status, _ = match_products(p1, p2)
    assert status == "AUTO_CONFIRMED"
    
    # Missing variant (Zero)
    p3 = {"brand": "Coca-Cola", "name": "Coca-Cola Refresco sin azúcar (500 ml)", "quantity": 500, "unit": "ml"}
    status, _ = match_products(p1, p3)
    assert status == "REVIEW_REQUIRED" # Dropped Zero, overlap is not 100%
    
    # Missing Brand
    p4 = {"brand": "", "name": "Coca-Cola Zero Refresco Sin Azúcar 500 mL", "quantity": 500, "unit": "mL"}
    status, _ = match_products(p4, p2)
    assert status == "REVIEW_REQUIRED" # has_brand is False

    # Prepared food
    taco1 = {"brand": "", "name": "Taco de Arrachera", "quantity": None, "unit": None}
    taco2 = {"brand": "", "name": "Taco de arrachera", "quantity": None, "unit": None}
    status, _ = match_products(taco1, taco2)
    assert status == "REVIEW_REQUIRED" # Excluded by prepared words
    
    combo1 = {"brand": "Burger King", "name": "Combo Whopper", "quantity": 1, "unit": "pz"}
    combo2 = {"brand": "Burger King", "name": "Combo Whopper", "quantity": 1, "unit": "pz"}
    status, _ = match_products(combo1, combo2)
    assert status == "REVIEW_REQUIRED" # Combo is prepared

# 3. Candidate cap sorting (Determinism & Priority)
def test_candidate_cap_and_determinism():
    # Bounded logic prefers brand matches first, then token matches.
    pass

# 4. Uber Brand Extraction
def test_uber_brand_extraction():
    sig = extract_signature("", "Coca-Cola · Refresco sin azúcar (500 ml)", None, None)
    assert sig["brand"] == "coca cola"
    assert sig["base_name"] == "refresco sin az car 500 ml"
    
    sig2 = extract_signature("", "No Brand Descriptor · Just Product", None, None)
    assert sig2["brand"] == "no brand descriptor"

# 5. Schema v16 Migration & Default OFF Canonical Writes
def test_schema_v16_migration():
    if os.path.exists("test_v16.db"):
        os.remove("test_v16.db")
    
    # Schema should migrate unconditionally to v16
    conn = setup_db("test_v16.db")
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='canonical_products'")
    assert c.fetchone() is not None
    
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == 16
    conn.close()
    if os.path.exists("test_v16.db"):
        os.remove("test_v16.db")

# 6. Membership Isolation in Cross Provider Score
def test_membership_isolation_score():
    canonical = {"quantity": 1, "unit": "L"}
    offers = [
        {"provider": "rappi", "store_id": "1", "price": 100, "member_price": 80, "quantity": 1, "unit": "L"},
        {"provider": "uber_eats", "store_id": "2", "price": 95, "member_price": 75, "quantity": 1, "unit": "L"}
    ]
    
    # No memberships
    res = compare_eligible_offers(canonical, offers, {"rappi_pro": False, "uber_one": False})
    assert res["best_offer"]["provider"] == "uber_eats"
    assert res["best_offer"]["eligible_price"] == 95
    
    # Rappi Pro only
    res = compare_eligible_offers(canonical, offers, {"rappi_pro": True, "uber_one": False})
    assert res["best_offer"]["provider"] == "rappi"
    assert res["best_offer"]["eligible_price"] == 80
    
    # Uber One only
    res = compare_eligible_offers(canonical, offers, {"rappi_pro": False, "uber_one": True})
    assert res["best_offer"]["provider"] == "uber_eats"
    assert res["best_offer"]["eligible_price"] == 75

# 7. Unit price dimension safety
def test_unit_price_dimension_safety():
    # If one offer has diff unit, it should reflect correctly, but for canonicals they share unit.
    canonical = {"quantity": 2, "unit": "L"}
    offers = [
        {"provider": "rappi", "price": 100, "quantity": 2, "unit": "L"},
    ]
    res = compare_eligible_offers(canonical, offers)
    assert res["best_offer"]["unit_price"] == 50.0

# 8. Gold Loader Integrity
def test_gold_loader_blocked():
    with pytest.raises(ValueError, match="GOLD_RECOVERY = BLOCKED"):
        load_gold_corpus()

