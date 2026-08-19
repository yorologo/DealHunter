import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.crawler import matches_filters

def test_min_discount():
    assert not matches_filters("Coca Cola", "Coca", "Oxxo", "Bebidas", {"min_discount": 40}, 30, "Direct", 100)
    assert matches_filters("Coca Cola", "Coca", "Oxxo", "Bebidas", {"min_discount": 40}, 45, "Direct", 100)

def test_store_filter():
    assert matches_filters("Leche", "Lala", "Chedraui", "Lacteos", {"store": ["chedraui"]}, 50, "Direct", 20)
    assert not matches_filters("Leche", "Lala", "Oxxo", "Lacteos", {"store": ["chedraui"]}, 50, "Direct", 20)

def test_exclude_store():
    assert not matches_filters("Leche", "Lala", "Chedraui", "Lacteos", {"exclude_store": ["chedraui"]}, 50, "Direct", 20)
    assert matches_filters("Leche", "Lala", "Oxxo", "Lacteos", {"exclude_store": ["chedraui"]}, 50, "Direct", 20)

if __name__ == "__main__":
    test_min_discount()
    test_store_filter()
    test_exclude_store()
    print("Filter tests passed.")
