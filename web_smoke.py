import urllib.request
import threading
import time
from dealhunter.web.app import create_app

def run_server():
    app = create_app()
    app.run(port=5001)

thread = threading.Thread(target=run_server, daemon=True)
thread.start()
time.sleep(3)

urls = [
    '/',
    '/stores',
    '/products',
    '/products?provider=rappi',
    '/products?provider=uber_eats',
    '/products?provider=all',
    '/compare',
    '/admin'
]

for url in urls:
    try:
        req = urllib.request.urlopen(f'http://localhost:5001{url}')
        print(f"URL {url} - Status: {req.status}")
    except Exception as e:
        print(f"URL {url} - Error: {e}")
