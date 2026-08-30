import pytest
import sqlite3
import tempfile
import os
from dealhunter.db import setup_db

@pytest.fixture
def collision_db():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    conn = setup_db(path)
    c = conn.cursor()
    
    # Insert Rappi s1/p1
    c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('rappi', 's1', 'Rappi Store 1', 'market')")
    c.execute("INSERT INTO products (provider, store_id, product_id, name, category) VALUES ('rappi', 's1', 'p1', 'Rappi Product 1', 'Cat A')")
    
    # Insert Uber s1/p1
    c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('uber_eats', 's1', 'Uber Store 1', 'market')")
    c.execute("INSERT INTO products (provider, store_id, product_id, name, category) VALUES ('uber_eats', 's1', 'p1', 'Uber Product 1', 'Cat B')")
    

    # Insert runs
    c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run1', '2026-08-01T09:00:00Z')")
    c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run2', '2026-08-02T09:00:00Z')")
    
    # Observations Rappi
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability) VALUES ('run1', 'rappi', 's1', 'p1', 100.0, 100.0, 10, '2026-08-01T10:00:00Z', 'AVAILABLE')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability, discount_effective) VALUES ('run2', 'rappi', 's1', 'p1', 50.0, 100.0, 10, '2026-08-02T10:00:00Z', 'AVAILABLE', 50.0)")
    
    # Observations Uber
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability) VALUES ('run1', 'uber_eats', 's1', 'p1', 200.0, 200.0, 10, '2026-08-01T11:00:00Z', 'AVAILABLE')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability, discount_effective) VALUES ('run2', 'uber_eats', 's1', 'p1', 150.0, 200.0, 10, '2026-08-02T11:00:00Z', 'AVAILABLE', 25.0)")
    
    conn.commit()
    yield path
    conn.close()
    os.unlink(path)

def test_history_collision(collision_db):
    conn = sqlite3.connect(collision_db)
    c = conn.cursor()
    # History Rappi
    c.execute("SELECT id, price, provider FROM observations WHERE provider='rappi' ORDER BY timestamp ASC")
    rappi_obs = c.fetchall()
    assert len(rappi_obs) == 2
    assert rappi_obs[0][1] == 100.0
    assert rappi_obs[1][1] == 50.0
    
    # History Uber
    c.execute("SELECT id, price, provider FROM observations WHERE provider='uber_eats' ORDER BY timestamp ASC")
    uber_obs = c.fetchall()
    assert len(uber_obs) == 2
    assert uber_obs[0][1] == 200.0
    assert uber_obs[1][1] == 150.0

from dealhunter.alerts_engine import DealWatcher
from dealhunter.config import get_merged_config

def test_alerts_collision(collision_db):
    watcher = DealWatcher(collision_db, config=get_merged_config(None), price_drop_threshold=10.0)
    events = watcher.process_run("run2")
    
    drop_events = [e for e in events if e['event_type'] in ('PRICE_DROP', 'DISCOUNT_INCREASED')]
    new_deal_events = [e for e in events if e['event_type'] == 'NEW_DEAL']
    
    # Uber generated a PRICE_DROP (200 -> 150 is 25%)
    # Rappi generated a NEW_DEAL (100 -> 50 is 50%, crossed 50%)
    assert len(drop_events) == 1
    assert len(new_deal_events) == 1
    
    assert drop_events[0]['provider'] == 'uber_eats'
    assert new_deal_events[0]['provider'] == 'rappi'

    assert watcher.persist_events(events) == len(events)
    rows = watcher.conn.execute(
        "SELECT DISTINCT provider FROM alert_events ORDER BY provider"
    ).fetchall()
    assert rows == [('rappi',), ('uber_eats',)]


def test_alert_run_scope_does_not_mark_other_provider_out_of_stock(collision_db):
    conn = sqlite3.connect(collision_db)
    conn.execute(
        "INSERT INTO runs (run_id, started_at) VALUES ('run3', '2026-08-03T09:00:00Z')"
    )
    conn.execute(
        """INSERT INTO observations
           (run_id, provider, store_id, product_id, price, original_price, stock,
            timestamp, availability, discount_effective)
           VALUES ('run3', 'rappi', 's1', 'p1', 45.0, 100.0, 10,
                   '2026-08-03T10:00:00Z', 'AVAILABLE', 55.0)"""
    )
    conn.commit()
    conn.close()

    watcher = DealWatcher(collision_db, config=get_merged_config(None), price_drop_threshold=10.0)
    events = watcher.process_run("run3")

    assert events
    assert all(event['provider'] == 'rappi' for event in events)
    assert not any(
        event['event_type'] == 'OUT_OF_STOCK' and event['provider'] == 'uber_eats'
        for event in events
    )
