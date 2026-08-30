import pytest
from dealhunter.eligibility import EligibilityEngine

def test_provider_disabled():
    config = {
        "providers": {
            "rappi": {"enabled": False}
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", False)
    assert res["visible"] is False
    assert res["ranking_eligible"] is False
    assert "disabled" in res["reason"]

def test_public_offer_provider_enabled():
    config = {
        "providers": {
            "rappi": {"enabled": True}
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", False)
    assert res["visible"] is True
    assert res["ranking_eligible"] is True

def test_membership_active():
    config = {
        "memberships": {
            "rappi_pro": {"status": "active"}
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", True)
    assert res["visible"] is True
    assert res["ranking_eligible"] is True

def test_membership_inactive_exclude():
    config = {
        "memberships": {
            "rappi_pro": {"status": "inactive"}
        },
        "comparison": {
            "inactive_membership_offers": "exclude"
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", True)
    assert res["visible"] is False
    assert res["ranking_eligible"] is False

def test_membership_inactive_show_but_exclude():
    config = {
        "memberships": {
            "rappi_pro": {"status": "inactive"}
        },
        "comparison": {
            "inactive_membership_offers": "show_but_exclude"
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", True)
    assert res["visible"] is True
    assert res["ranking_eligible"] is False

def test_membership_inactive_include():
    config = {
        "memberships": {
            "rappi_pro": {"status": "inactive"}
        },
        "comparison": {
            "inactive_membership_offers": "include"
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", True)
    assert res["visible"] is True
    assert res["ranking_eligible"] is True

def test_membership_unknown():
    config = {
        "memberships": {},
        "comparison": {
            "inactive_membership_offers": "show_but_exclude"
        }
    }
    engine = EligibilityEngine(config)
    res = engine.evaluate("rappi", True)
    assert res["visible"] is True
    assert res["ranking_eligible"] is False

def test_sql_visibility_exclude():
    config = {
        "memberships": {
            "rappi_pro": {"status": "inactive"},
            "uber_one": {"status": "active"}
        },
        "comparison": {
            "inactive_membership_offers": "exclude"
        }
    }
    engine = EligibilityEngine(config)
    sql, params = engine.get_sql_visibility_condition()
    assert "p.provider IN (?,?)" in sql
    assert "NOT (p.provider = 'rappi' AND o.has_pro_offer = 1)" in sql
    assert "NOT (p.provider = 'uber_eats' AND o.has_pro_offer = 1)" not in sql
