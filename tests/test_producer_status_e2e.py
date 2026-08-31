import pytest
import sqlite3
import os
from unittest.mock import patch
from dealhunter.cli import main
from dealhunter.db import setup_db

def test_rappi_producer_completed_flow(tmp_path):
    db = tmp_path / "test.db"
    os.environ["RAPPI_DB_PATH"] = str(db)
    conn = setup_db(str(db))
    conn.commit()
    conn.close()

    def mock_run_zone_inventory(config, lat, lng, conn_obj, run_id, dry_run=False):
        c = conn_obj.cursor()
        c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES (?, 'rappi', 's1', 'p1', 100.0, '2023-01-01T12:00:00Z')", (run_id,))
        conn_obj.commit()
        return "COMPLETED", 1

    with patch('dealhunter.auth.RappiSessionProvider') as MockProvider, \
         patch('dealhunter.account.SessionStatus') as MockStatus, \
         patch('dealhunter.cli.get_merged_config', return_value={'lat': 4.0, 'lng': -74.0, 'radius': 1500, 'vertical': 'general', 'catalog_sync': {'enabled': True}}), \
         patch('dealhunter.crawler_zone.run_zone_inventory', side_effect=mock_run_zone_inventory):
         
        mock_provider = MockProvider.return_value
        import asyncio
        async def mock_is_auth(): return True
        mock_provider.is_authenticated = mock_is_auth
        
        mock_status = MockStatus.return_value
        mock_status.get_current.return_value = {"status": "VALID"}
        
        main(['sync', '--provider', 'rappi'])
        
    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    c.execute("SELECT status FROM runs")
    runs = c.fetchall()
    assert len(runs) == 1
    assert runs[0][0] == 'SUCCESS'
    
    c.execute("SELECT provider, product_id, price FROM trusted_observations")
    obs = c.fetchall()
    assert len(obs) == 1
    assert obs[0] == ('rappi', 'p1', 100.0)
    conn.close()

def test_uber_producer_complete_flow(tmp_path):
    db = tmp_path / "test.db"
    os.environ["RAPPI_DB_PATH"] = str(db)
    conn = setup_db(str(db))
    conn.commit()
    conn.close()

    def mock_run_uber_sync(config, lat, lng, conn_obj, run_id):
        c = conn_obj.cursor()
        c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES (?, 'uber_eats', 's1', 'p1', 100.0, '2023-01-01T12:00:00Z')", (run_id,))
        conn_obj.commit()
        return "COMPLETE", 1

    with patch('dealhunter.cli.get_merged_config', return_value={'lat': 4.0, 'lng': -74.0, 'radius': 1500, 'vertical': 'general', 'providers': {'uber_eats': {'enabled': True}}}), \
         patch('dealhunter.providers.uber_eats.crawler.run_uber_sync', side_effect=mock_run_uber_sync):
         
        main(['sync', '--provider', 'uber_eats'])
        
    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    c.execute("SELECT status FROM runs")
    runs = c.fetchall()
    assert len(runs) == 1
    assert runs[0][0] == 'SUCCESS'
    
    c.execute("SELECT provider, product_id, price FROM trusted_observations")
    obs = c.fetchall()
    assert len(obs) == 1
    assert obs[0] == ('uber_eats', 'p1', 100.0)
    conn.close()

