import pytest
from dealhunter.catalog_sync import RestaurantMenuAdapter, AuthenticatedHttpClient, CoverageReport
import asyncio

class MockResponse:
    def __init__(self, data): self.data = data
    def read(self): return self.data
    def geturl(self): return "http"
    def __enter__(self): return self
    def __exit__(self, *args): pass

import urllib.request
import json

def test_deduplication_merges_promotions(monkeypatch):
    payload = {
        "id": "1923782439",
        "corridors": [
            {
                "id": "c1",
                "name": "Normal",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 63
                    }
                ]
            },
            {
                "id": "c2",
                "name": "Ofertas",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 63,
                        "real_price": 210,
                        "discount": 70,
                        "deal": "70% OFF",
                        "promotion_value": 70,
                        "units_condition": 1
                    }
                ]
            }
        ]
    }
    # fetch_menu actually requests HTML then extracts JSON?
    # Ah! fetch_menu also expects __NEXT_DATA__ in the html!
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: MockResponse(html.encode("utf-8")))
    
    adapter = RestaurantMenuAdapter(AuthenticatedHttpClient(None))
    items = asyncio.run(adapter.fetch_menu("1923782439", CoverageReport()))
    
    assert len(items) == 1
    prod = items[0]
    
    mems = [m["raw_name"] for m in prod["memberships"]]
    assert "Normal" in mems
    assert "Ofertas" in mems
    
    # This should fail because 'real_price' is lost by current deduplication!
    assert prod.get("real_price") == 210
    assert prod.get("discount") == 70

def test_deduplication_merges_promotions_reverse(monkeypatch):
    payload = {
        "id": "1923782439",
        "corridors": [
            {
                "id": "c2",
                "name": "Ofertas",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 63,
                        "real_price": 210,
                        "discount": 70,
                        "deal": "70% OFF",
                        "promotion_value": 70,
                        "units_condition": 1
                    }
                ]
            },
            {
                "id": "c1",
                "name": "Normal",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 63
                    }
                ]
            }
        ]
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: MockResponse(html.encode("utf-8")))
    
    adapter = RestaurantMenuAdapter(AuthenticatedHttpClient(None))
    items = asyncio.run(adapter.fetch_menu("1923782439", CoverageReport()))
    
    assert len(items) == 1
    prod = items[0]
    
    mems = [m["raw_name"] for m in prod["memberships"]]
    assert "Ofertas" in mems
    assert "Normal" in mems
    
    assert prod.get("real_price") == 210
    assert prod.get("discount") == 70

def test_deduplication_merges_nxm(monkeypatch):
    payload = {
        "id": "1923782439",
        "corridors": [
            {
                "id": "c1",
                "name": "Normal",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 63
                    }
                ]
            },
            {
                "id": "c2",
                "name": "Ofertas",
                "type": "corridor",
                "products": [
                    {
                        "id": "p1",
                        "name": "California especial",
                        "price": 63,
                        "deal": "2x1",
                        "promotion_value": 2,
                        "units_condition": 1
                    }
                ]
            }
        ]
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: MockResponse(html.encode("utf-8")))
    
    adapter = RestaurantMenuAdapter(AuthenticatedHttpClient(None))
    items = asyncio.run(adapter.fetch_menu("1923782439", CoverageReport()))
    
    assert len(items) == 1
    prod = items[0]
    
    assert prod.get("deal") == "2x1"
    assert prod.get("promotion_value") == 2
    assert prod.get("units_condition") == 1
