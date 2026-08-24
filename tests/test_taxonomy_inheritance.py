import pytest
import asyncio
from unittest.mock import patch, MagicMock
from dealhunter.catalog_sync import CPGCatalogAdapter, CoverageReport

@pytest.fixture
def cpg_adapter():
    return CPGCatalogAdapter(MagicMock())

def test_product_inherits_raw_ancestor_context(cpg_adapter):
    html = b'''<html><script id="__NEXT_DATA__" type="application/json">{"corridors": [{"name": "Bebidas", "type": "corridor", "id": "c1", "products": [{"id": "p1", "name": "Coca", "price": 20}]}]}</script></html>'''
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.geturl.return_value = "https://www.rappi.com.mx/tiendas/123"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        report = CoverageReport()
        items = asyncio.run(cpg_adapter.fetch_full_catalog("123", report))
        
        assert len(items) == 1
        p = items[0]
        assert p["id"] == "p1"
        assert "memberships" in p
        assert len(p["memberships"]) == 1
        
        m = p["memberships"][0]
        assert m["raw_name"] == "Bebidas"
        assert m["raw_type"] == "corridor"
        assert m["raw_id"] == "c1"
        assert m["source"] == "provider"
        assert m["path"] == ["Bebidas"]

def test_product_preserves_multiple_memberships(cpg_adapter):
    html = b'''<html><script id="__NEXT_DATA__" type="application/json">{"corridors": [{"name": "Bebidas", "type": "corridor", "products": [{"id": "p1", "name": "Coca", "price": 20}]}, {"name": "Promos", "type": "corridor", "products": [{"id": "p1", "name": "Coca", "price": 20}]}]}</script></html>'''
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.geturl.return_value = "https://www.rappi.com.mx/tiendas/123"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        report = CoverageReport()
        items = asyncio.run(cpg_adapter.fetch_full_catalog("123", report))
        
        assert len(items) == 1
        p = items[0]
        assert len(p["memberships"]) == 2
        names = [m["raw_name"] for m in p["memberships"]]
        assert "Bebidas" in names
        assert "Promos" in names

def test_duplicate_membership_is_deduplicated(cpg_adapter):
    html = b'''<html><script id="__NEXT_DATA__" type="application/json">{"corridors": [{"name": "Bebidas", "type": "corridor", "products": [{"id": "p1", "name": "Coca", "price": 20}, {"id": "p1", "name": "Coca", "price": 20}]}]}</script></html>'''
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.geturl.return_value = "https://www.rappi.com.mx/tiendas/123"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        report = CoverageReport()
        items = asyncio.run(cpg_adapter.fetch_full_catalog("123", report))
        
        assert len(items) == 1
        p = items[0]
        assert len(p["memberships"]) == 1

def test_legacy_category_contract_unchanged(cpg_adapter):
    html = b'''<html><script id="__NEXT_DATA__" type="application/json">{"corridors": [{"name": "Bebidas", "type": "corridor", "products": [{"id": "p1", "name": "Coca", "price": 20, "category": "Refrescos"}]}]}</script></html>'''
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.geturl.return_value = "https://www.rappi.com.mx/tiendas/123"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        report = CoverageReport()
        items = asyncio.run(cpg_adapter.fetch_full_catalog("123", report))
        
        p = items[0]
        assert p["category"] == "Refrescos"
