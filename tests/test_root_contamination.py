import pytest
from dealhunter.catalog_sync import CPGCatalogAdapter, AuthenticatedHttpClient, CoverageReport
import asyncio

class MockResponse:
    def __init__(self, data):
        self.data = data
    def read(self):
        return self.data
    def geturl(self):
        return "https://www.rappi.com.mx/restaurantes/123"
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

import urllib.request
import json
import re

def test_restaurant_root_contamination(monkeypatch):
    payload = {
        "id": "1923782439",
        "name": "VELMA BOX ZAPOPAN - Lomas de Zapopan",
        "type": "store",
        "corridors": [
            {
                "id": "c1",
                "name": "Sushi",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 100
                    }
                ]
            }
        ]
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
    
    def mock_urlopen(*args, **kwargs):
        return MockResponse(html.encode("utf-8"))
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    client = AuthenticatedHttpClient(None)
    adapter = CPGCatalogAdapter(client)
    report = CoverageReport()
    
    items = asyncio.run(adapter.fetch_full_catalog("1923782439", report))
    
    assert len(items) == 1
    mems = [m["raw_name"] for m in items[0]["memberships"]]
    print("Memberships found:", mems)
    
    assert "VELMA BOX ZAPOPAN - Lomas de Zapopan" not in mems
    assert "Sushi" in mems

def test_restaurant_menu_root_contamination(monkeypatch):
    from dealhunter.catalog_sync import RestaurantMenuAdapter
    
    payload = {
        "id": "1923782439",
        "name": "VELMA BOX ZAPOPAN - Lomas de Zapopan",
        "type": "merchant",
        "corridors": [
            {
                "id": "c1",
                "name": "Sushi",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 100
                    }
                ]
            }
        ]
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
    def mock_urlopen(*args, **kwargs):
        return MockResponse(html.encode("utf-8"))
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    adapter = RestaurantMenuAdapter(None)
    report = CoverageReport()
    
    items = asyncio.run(adapter.fetch_menu("1923782439", report))
    assert len(items) == 1
    mems = [m["raw_name"] for m in items[0]["memberships"]]
    print("Memberships found in menu:", mems)
    
    assert "VELMA BOX ZAPOPAN - Lomas de Zapopan" not in mems
    assert "Sushi" in mems
