import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.api import fetch_restaurant_categories

@patch("urllib.request.urlopen")
def test_restaurant_next_data_categories(mock_urlopen):
    html = b'<html><script id="__NEXT_DATA__" type="application/json">{"corridors": [{"name": "Promos", "products": [{"id": 123}, {"id": 456}]}]}</script></html>'
    mock_response = MagicMock()
    mock_response.read.return_value = html
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response
    
    mapping = fetch_restaurant_categories("999")
    assert mapping["123"] == "Promos"
    assert mapping["456"] == "Promos"

@patch("urllib.request.urlopen")
def test_restaurant_category_parser_fallback(mock_urlopen):
    html = b'<html>No next data here</html>'
    mock_response = MagicMock()
    mock_response.read.return_value = html
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response
    
    mapping = fetch_restaurant_categories("999")
    assert mapping == {}
