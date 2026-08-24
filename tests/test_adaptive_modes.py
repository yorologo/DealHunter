import pytest
import json
from unittest.mock import patch, MagicMock
from dealhunter.catalog_sync import MerchantDiscovery, CoverageReport
from dealhunter.auth import AuthenticatedHttpClient, RappiSessionProvider
import string
import asyncio

class MockResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status
    def read(self):
        return json.dumps(self.data).encode('utf-8')
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def make_stores(count, query):
    # Generates unique dummy stores to return
    return [{"store_id": f"{query}_{i}", "store_name": f"Store {query} {i}", "parent_store_type": "market"} for i in range(count)]

@pytest.fixture
def mock_urlopen():
    with patch('urllib.request.urlopen') as m:
        yield m
        
@pytest.fixture
def discovery():
    prov = RappiSessionProvider()
    client = AuthenticatedHttpClient(prov)
    return MerchantDiscovery(client)

def test_normal_mode(discovery, mock_urlopen):
    # NORMAL mode: Top 10 expanded.
    # 26 depth 1 queries. If we return 30 stores for 'a', 'b', 'c'...
    def side_effect(req, *args, **kwargs):
        if getattr(req, "data", None) is None:
            raise Exception("A5 mock failure")
        payload = json.loads(req.data.decode('utf-8'))
        q = payload["query"]
        if len(q) == 1:
            # deterministic count: 'a' gets 26, 'b' gets 25... 'z' gets 1
            idx = string.ascii_lowercase.index(q)
            count = 26 - idx
            return MockResponse({"stores": make_stores(count, q)})
        else:
            return MockResponse({"stores": make_stores(5, q)})
            
    mock_urlopen.side_effect = side_effect
    report = CoverageReport()
    
    merchants = asyncio.run(discovery.discover_merchants(20.0, -103.0, report, discovery_mode="normal"))
    
    # 26 depth 1 + 10 depth 1 expanded (10 * 26) = 286 requests
    assert report.authenticated_requests == 287
    assert mock_urlopen.call_count == 287

def test_deep_mode(discovery, mock_urlopen):
    def side_effect(req, *args, **kwargs):
        if getattr(req, "data", None) is None:
            raise Exception("A5 mock failure")
        payload = json.loads(req.data.decode('utf-8'))
        q = payload["query"]
        if len(q) == 1:
            idx = string.ascii_lowercase.index(q)
            return MockResponse({"stores": make_stores(idx, q)})
        else:
            return MockResponse({"stores": []})
            
    mock_urlopen.side_effect = side_effect
    report = CoverageReport()
    
    asyncio.run(discovery.discover_merchants(20.0, -103.0, report, discovery_mode="deep"))
    
    # 26 depth 1 + 20 * 26 = 546 requests
    assert report.authenticated_requests == 547
    assert mock_urlopen.call_count == 547

def test_full_mode(discovery, mock_urlopen):
    # Full mode expands anything >= 30.
    def side_effect(req, *args, **kwargs):
        if getattr(req, "data", None) is None:
            raise Exception("A5 mock failure")
        payload = json.loads(req.data.decode('utf-8'))
        q = payload["query"]
        if len(q) == 1:
            # make 2 queries return 30, the rest 10
            if q in ['a', 'b']:
                return MockResponse({"stores": make_stores(30, q)})
            return MockResponse({"stores": make_stores(10, q)})
        else:
            return MockResponse({"stores": []})
            
    mock_urlopen.side_effect = side_effect
    report = CoverageReport()
    
    asyncio.run(discovery.discover_merchants(20.0, -103.0, report, discovery_mode="full"))
    
    # 26 depth 1 + 2 * 26 = 78 requests
    assert report.authenticated_requests == 79

def test_fewer_than_k_parents_available(discovery, mock_urlopen):
    # If API fails for almost all letters, we might have < K parents.
    def side_effect(req, *args, **kwargs):
        if getattr(req, "data", None) is None:
            raise Exception("A5 mock failure")
        payload = json.loads(req.data.decode('utf-8'))
        q = payload["query"]
        if len(q) == 1 and q in ['a', 'b', 'c']:
            return MockResponse({"stores": make_stores(10, q)})
        import urllib.error
        raise urllib.error.HTTPError(req.full_url, 401, "Auth Error", {}, None)
        
    mock_urlopen.side_effect = side_effect
    report = CoverageReport()
    
    asyncio.run(discovery.discover_merchants(20.0, -103.0, report, discovery_mode="normal"))
    
    # 26 queries depth 1. Only 3 succeed.
    # It tries to expand Top 10, but only 3 are available. So 3 * 26 = 78 depth 2.
    # Total = 26 + 78 = 104
    assert report.authenticated_requests == 105
    assert report.http_401 == 101

def test_deterministic_ordering(discovery, mock_urlopen):
    # All letters return exactly 10 items.
    def side_effect(req, *args, **kwargs):
        if getattr(req, "data", None) is None:
            raise Exception("A5 mock failure")
        payload = json.loads(req.data.decode('utf-8'))
        q = payload["query"]
        if len(q) == 1:
            return MockResponse({"stores": make_stores(10, "fixed")})
        else:
            return MockResponse({"stores": []})
            
    mock_urlopen.side_effect = side_effect
    report = CoverageReport()
    
    asyncio.run(discovery.discover_merchants(20.0, -103.0, report, discovery_mode="normal"))
    
    # 26 queries depth 1. Top 10 will be picked. Since all have 10 raw_count,
    # it must sort alphabetically and pick 'a' through 'j'.
    # Total = 26 + 10 * 26 = 286
    assert report.authenticated_requests == 287
    
    # Check deduplication
    assert report.merchants_discovered == 10 # all returned "Store fixed X"

