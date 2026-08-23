import asyncio
import json
import sqlite3
import time
import urllib.request
import urllib.error
import sys
import os

sys.path.insert(0, os.path.abspath('src'))
from dealhunter.auth import RappiSessionProvider

# Baseline configuration
LAT = 19.432608  # Defaulting to some config or test coordinates if not set?
LNG = -99.133209
try:
    from dealhunter.config import load_config
    cfg = load_config()
    LAT = cfg.get('crawler', {}).get('default_lat', LAT)
    LNG = cfg.get('crawler', {}).get('default_lng', LNG)
except Exception:
    pass

def get_known_stores():
    conn = sqlite3.connect('rappi-deals.db')
    c = conn.cursor()
    c.execute("SELECT store_id FROM stores")
    stores = set(row[0] for row in c.fetchall())
    conn.close()
    return stores

class NativeExperiment:
    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng
        self.provider = RappiSessionProvider()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Origin": "https://www.rappi.com.mx"
        }
        if self.provider.context and self.provider.context._access_token:
            self.headers["Authorization"] = f"Bearer {self.provider.context._access_token}"

    def make_request(self, method, url, payload=None):
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            start = time.time()
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read().decode('utf-8')
                duration = time.time() - start
                return response.getcode(), body, duration
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', errors='ignore'), time.time() - start
        except Exception as e:
            return 0, str(e), 0.0

if __name__ == "__main__":
    known = get_known_stores()
    print(f"Known stores: {len(known)}")
    exp = NativeExperiment(LAT, LNG)
    print("Testing /api/web-gateway/web/home/v2")
    payload = {"lat": LAT, "lng": LNG, "is_pro": False}
    status, body, duration = exp.make_request('POST', 'https://services.mxgrability.rappi.com/api/web-gateway/web/home/v2', payload)
    print(f"Status: {status}, Duration: {duration:.2f}s")
    if status == 200:
        with open('experiments/native_discovery/home_v2.json', 'w') as f:
            f.write(body)
        print("Saved home_v2.json")
    
    print("Testing /api/web-gateway/web/restaurants-bus/v1/page")
    payload = {"lat": LAT, "lng": LNG, "page": 0, "limit": 50, "store_type": "restaurant"}
    status, body, duration = exp.make_request('POST', 'https://services.mxgrability.rappi.com/api/web-gateway/web/restaurants-bus/v1/page', payload)
    print(f"Status: {status}, Duration: {duration:.2f}s")
    if status == 200:
        with open('experiments/native_discovery/restaurants_v1.json', 'w') as f:
            f.write(body)
        print("Saved restaurants_v1.json")
        
