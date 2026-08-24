import pytest
from unittest.mock import patch, MagicMock
from dealhunter.catalog_sync import MerchantDiscovery, CoverageReport
import asyncio

class MockResponse:
    def __init__(self, json_data):
        self._json = json_data

    def read(self):
        import json
        return json.dumps(self._json).encode('utf-8')

@pytest.fixture
def mock_urlopen():
    with patch('urllib.request.urlopen') as mock:
        yield mock

@pytest.fixture
def report():
    return CoverageReport()

@pytest.fixture
def discovery():
    return MerchantDiscovery(client=None)


def test_targeted_exact_store_id(discovery, mock_urlopen, report):
    mock_urlopen.return_value.__enter__.return_value = MockResponse({
        "stores": [
            {"store_id": 111, "store_name": "Sushi A", "parent_store_type": "market"},
            {"store_id": 222, "store_name": "Sushi B", "parent_store_type": "restaurants", "vertical_sub_group": "restaurants", "categories": "Sushi", "tags": ["Sushi"]}
        ]
    })
    
    status, store = asyncio.run(discovery.discover_targeted("Sushi", 19.0, -99.0, report, expected_store_id="222"))
    
    assert status == "MATCH_EXACT_STORE_ID"
    assert store is not None
    assert store["store_id"] == "222"
    assert store["name"] == "Sushi B"
    assert store["type"] == "restaurants"
    assert store["vertical_sub_group"] == "restaurants"
    assert store["categories"] == "Sushi"
    assert store["tags"] == ["Sushi"]
    assert report.authenticated_requests == 1


def test_targeted_id_not_found(discovery, mock_urlopen, report):
    mock_urlopen.return_value.__enter__.return_value = MockResponse({
        "stores": [
            {"store_id": 111, "store_name": "Sushi A"},
            {"store_id": 222, "store_name": "Sushi B"}
        ]
    })
    
    status, store = asyncio.run(discovery.discover_targeted("Sushi", 19.0, -99.0, report, expected_store_id="999"))
    
    assert status == "NOT_FOUND"
    assert store is None
    assert report.authenticated_requests == 1


def test_targeted_cpg_metadata_preserved(discovery, mock_urlopen, report):
    mock_urlopen.return_value.__enter__.return_value = MockResponse({
        "stores": [
            {
                "store_id": 1930266218, 
                "store_name": "Turbo Market", 
                "parent_store_type": "chiper_extended",
                "vertical_sub_group": "Turbo"
                # categories and tags absent
            }
        ]
    })
    
    status, store = asyncio.run(discovery.discover_targeted("Turbo", 19.0, -99.0, report, expected_store_id="1930266218"))
    
    assert status == "MATCH_EXACT_STORE_ID"
    assert store["type"] == "chiper_extended"
    assert store["vertical_sub_group"] == "Turbo"
    assert store["categories"] is None
    assert store["tags"] is None
    assert report.authenticated_requests == 1


def test_targeted_no_id_ambiguous(discovery, mock_urlopen, report):
    mock_urlopen.return_value.__enter__.return_value = MockResponse({
        "stores": [
            {"store_id": 111, "store_name": "Sushi A"},
            {"store_id": 222, "store_name": "Sushi B"}
        ]
    })
    
    status, store = asyncio.run(discovery.discover_targeted("Sushi", 19.0, -99.0, report, expected_store_id=None))
    
    assert status == "AMBIGUOUS"
    assert store is None
    assert report.authenticated_requests == 1


def test_targeted_no_id_success(discovery, mock_urlopen, report):
    mock_urlopen.return_value.__enter__.return_value = MockResponse({
        "stores": [
            {"store_id": 111, "store_name": "Sushi A"}
        ]
    })
    
    status, store = asyncio.run(discovery.discover_targeted("Sushi", 19.0, -99.0, report, expected_store_id=None))
    
    assert status == "SUCCESS"
    assert store is not None
    assert store["store_id"] == "111"
    assert report.authenticated_requests == 1


def test_existing_modes_unaffected(discovery, mock_urlopen, report):
    mock_urlopen.return_value.__enter__.return_value = MockResponse({
        "stores": [
            {"store_id": 111, "store_name": "Sushi A"}
        ]
    })
    
    # normal discovery mode
    merchants = asyncio.run(discovery.discover_merchants(19.0, -99.0, report, discovery_mode="normal"))
    assert len(merchants) > 0
    # The normal mode will make 26 + 10*26 requests, testing just that it executes without crashing
    assert report.authenticated_requests > 10
