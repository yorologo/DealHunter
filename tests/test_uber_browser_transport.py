
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from dealhunter.providers.uber_eats.browser_transport import (
    UberBrowserTransport,
    READY,
    BROWSER_NOT_RUNNING
)
from dealhunter.providers.uber_eats.parser import UberEatsParser

FAKE_VERSION = b'{"Browser": "Chrome/151.0.7922.174", "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/xyz"}'

SAMPLE_GETSTORE_RESPONSE = {
    "status": "success",
    "data": {
        "uuid": "test-uuid-1234",
        "title": "Test Store",
        "isOpen": True,
        "isOrderable": True,
        "sections": [
            {"uuid": "sec-1", "title": "Bebidas"},
            {"uuid": "sec-2", "title": "Botanas"},
        ],
        "catalogSectionsMap": {
            "test-uuid-1234": [
                {
                    "type": "HORIZONTAL_GRID",
                    "payload": {
                        "standardItemsPayload": {
                            "title": {"text": "Bebidas"},
                            "catalogItems": [
                                {
                                    "uuid": "prod-1",
                                    "title": "Coca Cola 600ml",
                                    "price": 2500,
                                    "isSoldOut": False,
                                    "imageUrl": "https://img.test/coca.jpg",
                                    "itemDescription": "Refresco",
                                    "priceTagline": {"accessibilityText": ""},
                                    "promoInfo": {},
                                },
                                {
                                    "uuid": "prod-2",
                                    "title": "Agua Natural 1L",
                                    "price": 1500,
                                    "isSoldOut": False,
                                    "imageUrl": "https://img.test/agua.jpg",
                                    "itemDescription": "",
                                    "priceTagline": {},
                                    "promoInfo": {},
                                }
                            ],
                        }
                    },
                }
            ]
        },
        "catalogSectionPagingInfo": None,
    },
}

def make_mock_urlopen(status=200, body=FAKE_VERSION):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    return MagicMock(return_value=mock_resp)

class TestHealth:
    def test_health_ready(self):
        transport = UberBrowserTransport()
        with patch("urllib.request.urlopen", make_mock_urlopen()):
            assert transport.health() == READY

    def test_health_browser_not_running(self):
        transport = UberBrowserTransport()
        with patch("urllib.request.urlopen", side_effect=Exception("refused")):
            assert transport.health() == BROWSER_NOT_RUNNING

    def test_get_browser_info(self):
        transport = UberBrowserTransport()
        with patch("urllib.request.urlopen", make_mock_urlopen()):
            info = transport.get_browser_info()
            assert info["browser"] == "Chrome/151.0.7922.174"

class TestCapture:
    @pytest.mark.asyncio
    async def test_capture_store_success(self):
        transport = UberBrowserTransport()
        transport._ws = AsyncMock()

        async def mock_fetch_page(store_uuid, offset):
            return {
                "storeTitle": "Test Store",
                "sections": [{"uuid": "s1", "title": "A"}],
                "catalogSectionsMap": {
                    "s1": [{"type": "VERTICAL_GRID", "payload": {"standardItemsPayload": {"catalogItems": [{"uuid": "p1"}, {"uuid": "p2"}]}}}]
                },
                "pagingInfo": None
            }

        transport._fetch_store_page = mock_fetch_page
        result = await transport.capture_store("test-uuid")

        assert result["status"] == "success"
        assert result["products_raw"] == 2
        assert result["completeness"] == "COMPLETE"
        assert result["raw_payload"]["title"] == "Test Store"

    @pytest.mark.asyncio
    async def test_capture_store_pagination(self):
        transport = UberBrowserTransport()
        transport._ws = AsyncMock()
        call_count = 0

        async def mock_fetch_page(store_uuid, offset):
            nonlocal call_count
            call_count += 1
            if offset == 0:
                return {
                    "storeTitle": "Paginated",
                    "sections": [{"uuid": "s1"}],
                    "catalogSectionsMap": {
                        "s1": [{"type": "VERTICAL_GRID", "payload": {"standardItemsPayload": {"catalogItems": [{"uuid": f"p{i}"} for i in range(15)]}}}]
                    },
                    "pagingInfo": {"offset": 7, "isFirstPage": True},
                }
            elif offset == 7:
                return {
                    "sections": [{"uuid": "s2"}],
                    "catalogSectionsMap": {
                        "s2": [{"type": "VERTICAL_GRID", "payload": {"standardItemsPayload": {"catalogItems": [{"uuid": f"q{i}"} for i in range(10)]}}}]
                    },
                    "pagingInfo": {"offset": 14, "isFirstPage": False},
                }
            else:
                return {"sections": [], "catalogSectionsMap": {}, "pagingInfo": None}

        transport._fetch_store_page = mock_fetch_page
        result = await transport.capture_store("test-uuid", max_pages=5)
        assert result["products_raw"] == 25  # 15 + 10
        assert call_count == 3  # offset 0, 7, 14 (empty)

class TestFailureIsolation:
    @pytest.mark.asyncio
    async def test_disconnect_handled(self):
        transport = UberBrowserTransport()
        transport._ws = AsyncMock()
    
        async def mock_fetch_page(store_uuid, offset):
            raise ConnectionError("WebSocket closed")
    
        transport._fetch_store_page = mock_fetch_page
        result = await transport.capture_store("test-uuid")
        assert result["status"] == "empty"

class TestParserIntegration:
    def test_parse_sample_response(self):
        parser = UberEatsParser()
        parsed = parser.parse_store(SAMPLE_GETSTORE_RESPONSE["data"])
        assert parsed["store"]["provider"] == "uber_eats"
        assert parsed["store"]["raw_store_id"] == "test-uuid-1234"
        assert len(parsed["products"]) == 2
        assert parsed["products"][0]["price"] == 25.0
        assert parsed["products"][0]["category"] == "Bebidas"

    def test_normalizer_observation(self):
        from dealhunter.providers.uber_eats.normalizer import UberEatsNormalizer
        normalizer = UberEatsNormalizer()
        product = {
            "raw_store_id": "store-1",
            "raw_product_id": "prod-1",
            "name": "Test",
            "price": 25.0,
            "reference_price": 30.0,
            "reference_price_source": "accessibility",
            "promotion_uuid": None,
            "availability": "AVAILABLE",
        }
        obs = normalizer.normalize_observation(product, run_id=1)
        assert obs["price"] == 25.0
        assert obs["original_price"] == 30.0
        assert obs["stock"] == 1
        assert obs["discount_price"] > 0
        assert "provider" not in obs


class TestTargetStability:
    @pytest.mark.asyncio
    @patch("dealhunter.providers.uber_eats.browser_transport.UberBrowserTransport.connect")
    @patch("dealhunter.providers.uber_eats.browser_transport.UberBrowserTransport._install_csrf_interceptor")
    @patch("dealhunter.providers.uber_eats.browser_transport.UberBrowserTransport._check_login_state")
    async def test_ensure_ready_waits_for_stable_execution_context(self, mock_check, mock_install, mock_connect):
        transport = UberBrowserTransport()
        transport._ws = AsyncMock()
        transport._session_id = "test-session"
        
        # Simulate send_session calls
        # 1. Page.navigate
        # 2. Runtime.evaluate loops
        call_count = 0
        async def mock_send_session(method, params=None):
            nonlocal call_count
            if method == "Page.navigate":
                return {}
            if method == "Runtime.evaluate":
                call_count += 1
                # Return false for the first 2 calls (simulating redirect / loading)
                if call_count < 3:
                    return {"result": {"value": False}}
                # Return true on the 3rd call
                return {"result": {"value": True}}
            return {}
            
        transport._send_session = AsyncMock(side_effect=mock_send_session)
        
        # Also patch asyncio.sleep to not actually sleep in tests
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await transport.ensure_ready()
            
            # verify it polled until true
            assert call_count == 3
            # verify it slept between polls (plus the final sleep(1))
            assert mock_sleep.call_count == 4
