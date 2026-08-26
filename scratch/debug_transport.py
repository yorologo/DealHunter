import asyncio
import logging
from dealhunter.providers.uber_eats.browser_transport import UberBrowserTransport

logging.basicConfig(level=logging.DEBUG)

async def main():
    transport = UberBrowserTransport()
    res = await transport.capture_store("d3fa2538-6e34-49d4-a6ec-0cb484918bc7", max_pages=1)
    print("FINAL:", res)

asyncio.run(main())
