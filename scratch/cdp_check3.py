import asyncio
import sys
sys.path.append("src")
from dealhunter.providers.uber_eats.browser_transport import UberBrowserTransport

async def main():
    transport = UberBrowserTransport()
    if transport.health() != "READY":
        print("Browser not ready")
        return
        
    await transport.connect()
    print("Navigating to ubereats.com...")
    await transport.navigate("https://www.ubereats.com/")
    
    # Wait for navigation
    await asyncio.sleep(5)
    
    # Evaluate login status
    resp = await transport.send_command("Runtime.evaluate", {
        "expression": "document.body.innerText.substring(0, 500)"
    })
    
    print("Page snippet:", resp.get("result", {}).get("result", {}).get("value", ""))
    
    await transport.close()

asyncio.run(main())
