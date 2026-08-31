import pytest
from dealhunter.historico import compare_stores, compare_with_anchor, compute_price_metrics, analyze_history
from dealhunter.web.queries import get_product_detail, enrich_products_with_metrics
from dealhunter.db import setup_db

def setup_mock_db(db_path):
    conn = setup_db(db_path)
    c = conn.cursor()
    
    # Insert mock data
    c.execute("INSERT INTO stores (provider, store_id, name, vertical, type) VALUES ('rappi', 's1', 'Store 1', 'market', 'market')")
    c.execute("INSERT INTO products (provider, product_id, store_id, name, normalized_quantity, normalized_unit, category) VALUES ('rappi', 'p1', 's1', 'Pizza', 1.0, 'unidad', 'Food')")
    
    # Runs
    c.execute("INSERT INTO runs (run_id, status) VALUES ('run1', 'SUCCESS')")
    c.execute("INSERT INTO runs (run_id, status) VALUES ('run2', 'SUCCESS')")
    c.execute("INSERT INTO runs (run_id, status) VALUES ('run3', 'SUCCESS')")
    
    # Valid observation
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES ('run1', 'rappi', 's1', 'p1', 100.0, '2023-01-01T12:00:00Z')")
    # NULL timestamp
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES ('run2', 'rappi', 's1', 'p1', 90.0, NULL)")
    # Invalid timestamp
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES ('run3', 'rappi', 's1', 'p1', 80.0, 'invalid-date')")
    
    conn.commit()
    conn.close()

def test_product_detail_null_timestamp(tmp_path):
    db = tmp_path / "test.db"
    setup_mock_db(str(db))
    p = get_product_detail(str(db), 'rappi', 's1', 'p1')
    assert p is not None
    obs = p['observations']
    assert len(obs) == 3
    # Order should be NULL, 2023-..., invalid-date
    assert obs[0]['timestamp'] is None
    assert obs[1]['timestamp'] is not None # Valid date
    assert obs[2]['timestamp'] is None     # Invalid date -> None
    assert p['metrics'] is not None
    assert p['metrics']['current_price'] == 80.0
    
def test_free_compare_null_timestamp(tmp_path):
    db = tmp_path / "test.db"
    setup_mock_db(str(db))
    res = compare_stores(str(db), 'Pizza')
    assert len(res) > 0
    assert res[0]['PRECIO'] == '$80.00'
    assert '1970' not in str(res)
    assert 'now' not in str(res)
    
def test_anchor_compare_null_timestamp(tmp_path):
    db = tmp_path / "test.db"
    setup_mock_db(str(db))
    res = compare_with_anchor(str(db), 'rappi', 's1', 'p1')
    assert res['matches'] != []
    assert '1970' not in str(res)
    
def test_history_null_timestamp(tmp_path):
    db = tmp_path / "test.db"
    setup_mock_db(str(db))
    res = analyze_history(str(db), {})
    assert len(res) > 0
    assert res[0]['current_price'] == 80.0
    
def test_enrich_products_null_timestamp(tmp_path):
    db = tmp_path / "test.db"
    setup_mock_db(str(db))
    products = [{'provider': 'rappi', 'store_id': 's1', 'product_id': 'p1', 'normalized_quantity': 1, 'normalized_unit': 'unidad'}]
    res = enrich_products_with_metrics(str(db), products)
    assert res[0]['metrics']['current_price'] == 80.0

