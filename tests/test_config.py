import os
import sys
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.config import get_merged_config

def test_defaults():
    cfg = get_merged_config(None)
    assert cfg["min_discount"] == 10
    assert cfg["top"] == 50

def test_cli_override():
    args = argparse.Namespace(min_discount=40, top=20)
    cfg = get_merged_config(args)
    assert cfg["min_discount"] == 40
    assert cfg["top"] == 20

if __name__ == "__main__":
    test_defaults()
    test_cli_override()
    print("Config tests passed.")
