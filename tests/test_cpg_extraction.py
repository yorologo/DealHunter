import pytest
from unittest.mock import patch, MagicMock
from dealhunter.catalog_sync import CPGCatalogAdapter, AuthenticatedHttpClient, CoverageReport
import json
import asyncio

def test_cpg_extraction_preserves_memberships():
    async def _run():
        mock_client = MagicMock(spec=AuthenticatedHttpClient)
        html_content = '''<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"fallback": {"some_query": {"components": [{"id": "100", "name": "Botanas", "parent_id": 0, "products": [{"id": "p1", "name": "Papas Fritas", "price": 20}]}, {"id": "101", "name": "Ofertas", "parent_id": 0, "products": [{"id": "p1", "name": "Papas Fritas", "price": 20}]}]}}}}}</script>'''
        mock_response = MagicMock()
        mock_response.read.return_value = html_content.encode('utf-8')
        mock_response.__enter__.return_value = mock_response # context manager mock
        adapter = CPGCatalogAdapter(mock_client)
        report = CoverageReport()
        with patch('urllib.request.urlopen', return_value=mock_response):
            products = await adapter.fetch_full_catalog("123", report)
        
        assert len(products) == 1
        p = products[0]
        assert p["name"] == "Papas Fritas"
        assert "memberships" in p
        assert len(p["memberships"]) == 2
        names = {m["raw_name"] for m in p["memberships"]}
        assert names == {"Botanas", "Ofertas"}
        types = {m["raw_type"] for m in p["memberships"]}
        assert types == {"unknown"}
        
    asyncio.run(_run())

