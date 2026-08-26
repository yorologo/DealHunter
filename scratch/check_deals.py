import asyncio
import json
from dealhunter.providers.uber_eats.browser_transport import UberBrowserTransport
from dealhunter.providers.uber_eats.parser import UberEatsParser

OXXO_ID = "9750bfe0-a4ad-5d80-b371-9fb3a428e124" # "ldQv4KStXYCzcZ-zpCjhJA" decoded is 95d42fe0-a4ad-5d80-b371-9fb3a428e124
# Wait, let's use the one from search_res.json or I can decode "ldQv4KStXYCzcZ-zpCjhJA"
import base64
import uuid

def decode_uuid(b64u):
    b = base64.urlsafe_b64decode(b64u + '==')
    return str(uuid.UUID(bytes=b))

OXXO_UUID = decode_uuid("ldQv4KStXYCzcZ-zpCjhJA")
print("OXXO UUID:", OXXO_UUID)

async def main():
    transport = UberBrowserTransport()
    res = await transport.capture_store(OXXO_UUID, max_pages=100)
    
    parser = UberEatsParser()
    parsed = parser.parse_store(res.get("raw_payload", {}))
    
    print(f"Parsed {len(parsed['products'])} products.")
    deals = [p for p in parsed['products'] if p.get('discount_price', 0) > 0 or p.get('promotion_uuid')]
    print(f"Found {len(deals)} deals.")
    for d in deals[:10]:
        print(f"{d['name']} | Price: {d['price']} | Ref: {d.get('reference_price')} | Promo: {d.get('promotion_uuid')}")

asyncio.run(main())
