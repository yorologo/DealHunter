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
