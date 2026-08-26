import asyncio
import json
import base64
import uuid
from dealhunter.providers.uber_eats.browser_transport import UberBrowserTransport

def decode_uuid(b64u):
    b = base64.urlsafe_b64decode(b64u + '==')
    return str(uuid.UUID(bytes=b))

OXXO_UUID = decode_uuid("ldQv4KStXYCzcZ-zpCjhJA")

async def main():
    transport = UberBrowserTransport()
    res = await transport.capture_store(OXXO_UUID, max_pages=15)
    
    for elements in res["raw_payload"].get("catalogSectionsMap", {}).values():
        for el in elements:
            items = el.get("payload", {}).get("standardItemsPayload", {}).get("catalogItems", [])
            for item in items:
                if not item.get("promoInfo", {}).get("promotionUUID"):
                    print(json.dumps(item, indent=2))
                    return

asyncio.run(main())
