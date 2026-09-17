import os
import sys
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.config import get_merged_config


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = get_merged_config(None)
    assert cfg["min_discount"] == 0
    assert cfg["top"] == 50
    assert cfg["lat"] is None
    assert cfg["lng"] is None


def test_cli_override(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    args = argparse.Namespace(min_discount=40, top=20, lat=19.5, lng=-99.2)
    cfg = get_merged_config(args)
    assert cfg["min_discount"] == 40
    assert cfg["top"] == 20
    assert cfg["lat"] == 19.5
    assert cfg["lng"] == -99.2

from dealhunter.cli import build_parser
from dealhunter.config import save_config


def _parsed_discover(*argv):
    return build_parser().parse_args(["discover", *argv])


def test_cli_boolean_unset_preserves_lower_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({"dry_run": True, "compact": True, "only_nxm": True, "desc": False})
    cfg = get_merged_config(_parsed_discover())
    assert cfg["dry_run"] is True
    assert cfg["compact"] is True
    assert cfg["only_nxm"] is True
    assert cfg["desc"] is False


def test_cli_boolean_explicit_true_overrides_lower_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({"dry_run": False, "compact": False, "only_nxm": False})
    cfg = get_merged_config(_parsed_discover("--dry-run", "--compact", "--only-nxm"))
    assert cfg["dry_run"] is True
    assert cfg["compact"] is True
    assert cfg["only_nxm"] is True


def test_cli_boolean_explicit_false_overrides_lower_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({"dry_run": True, "compact": True, "only_nxm": True})
    cfg = get_merged_config(_parsed_discover("--no-dry-run", "--no-compact", "--no-only-nxm"))
    assert cfg["dry_run"] is False
    assert cfg["compact"] is False
    assert cfg["only_nxm"] is False


def test_sort_direction_cli_is_explicit_and_mutually_exclusive(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({"desc": True})
    assert get_merged_config(_parsed_discover("--asc"))["desc"] is False

    save_config({"desc": False})
    assert get_merged_config(_parsed_discover("--desc"))["desc"] is True

    with __import__("pytest").raises(SystemExit):
        _parsed_discover("--asc", "--desc")


def test_profile_global_cli_precedence_for_boolean(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({
        "dry_run": False,
        "profiles": {"audit": {"dry_run": True}},
    })
    assert get_merged_config(_parsed_discover(), "audit")["dry_run"] is True
    assert get_merged_config(_parsed_discover("--no-dry-run"), "audit")["dry_run"] is False


def test_non_boolean_precedence_is_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config({
        "min_discount": 10,
        "max_requests": 900,
        "profiles": {"audit": {"min_discount": 20, "max_requests": 800}},
    })
    cfg = get_merged_config(_parsed_discover("--min-discount", "30"), "audit")
    assert cfg["min_discount"] == 30
    assert cfg["max_requests"] == 800


def test_runtime_consumed_cli_options_are_part_of_config_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = get_merged_config(_parsed_discover(
        "--min-price", "5", "--max-price", "50",
        "--promo", "NxM", "--min-promo-discount", "15",
        "--discovery-mode", "normal",
    ))
    assert cfg["min_price"] == 5
    assert cfg["max_price"] == 50
    assert cfg["promo"] == ["NxM"]
    assert cfg["min_promo_discount"] == 15
    assert cfg["discovery_mode"] == "normal"


def test_location_parser_requires_complete_valid_pair():
    import pytest
    from dealhunter.config import parse_location

    assert parse_location("20.5", "-103.4") == (20.5, -103.4)
    for lat, lng in ((None, None), ("20", None), (None, "-103"), ("x", "-103"), ("91", "-103"), ("20", "-181")):
        with pytest.raises(ValueError):
            parse_location(lat, lng)


def test_discovery_mode_authority_is_shared_with_cli():
    import pytest
    from dealhunter.config import DISCOVERY_MODES

    assert DISCOVERY_MODES == ("normal", "deep", "full")
    for mode in DISCOVERY_MODES:
        assert _parsed_discover("--discovery-mode", mode).discovery_mode == mode
    with pytest.raises(SystemExit):
        _parsed_discover("--discovery-mode", "custom")
