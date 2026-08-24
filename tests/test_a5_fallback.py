import pytest, asyncio
from unittest.mock import patch
from dealhunter.catalog_sync import MerchantDiscovery, CoverageReport
import urllib.error

def test_a5_failure_triggers_fallback():
    class MockClient:
        pass
    discovery = MerchantDiscovery(MockClient())
    report = CoverageReport()
    
    with patch.object(discovery, '_run_context_stores_sync', return_value=([], Exception("A5 Error"))):
        with patch.object(discovery, '_run_query_sync', return_value=([{"store_id": "999", "store_name": "Fallback Store"}], None)) as mock_unified:
            res = asyncio.run(discovery.discover_merchants(0, 0, report, discovery_mode="deep"))
            assert mock_unified.call_count > 0
            assert any(str(s["store_id"]) == "999" for s in res)
            assert report.merchants_discovered >= 1

def test_a5_success_skips_cpg_bfs():
    class MockClient:
        pass
    discovery = MerchantDiscovery(MockClient())
    report = CoverageReport()
    
    with patch.object(discovery, '_run_context_stores_sync', return_value=([{"store_id": "888", "store_name": "A5 Store", "vertical_sub_group": "A5 Group"}], None)):
        with patch.object(discovery, '_run_query_sync', return_value=([], None)) as mock_unified:
            res = asyncio.run(discovery.discover_merchants(0, 0, report, discovery_mode="normal"))
            assert mock_unified.call_count == 0
            assert len(res) == 1
            assert res[0]["store_id"] == "888"

