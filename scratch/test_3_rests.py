import asyncio
from dealhunter.providers.uber_eats.browser_transport import UberBrowserTransport

RESTS = [
    "832b0757-ca82-4b62-8232-c1b615a6d22d", # Tony Pepperoni
    "03521919-0ef9-4f94-94c7-39bdfa126298", # Da Fabio Trattoria Pizzeria Bar
    "d3fa2538-6e34-49d4-a6ec-0cb484918bc7", # Pizzahead
]

async def main():
    transport = UberBrowserTransport()
    for rest_id in RESTS:
        print(f"\n--- Testing restaurant {rest_id} ---")
        result = await transport.capture_store(rest_id, max_pages=15)
        print(f"Status: {result.get('status')}")
        print(f"Products Raw: {result.get('products_raw')}")
        print(f"Title: {result.get('raw_payload', {}).get('title')}")
        
asyncio.run(main())
