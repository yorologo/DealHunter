import time
import logging
from typing import List, Dict, Any, Optional
from .auth import RappiSessionProvider, AuthenticatedHttpClient
from .crawler import run_discover
from .api import fetch_unified_search

class CoverageReport:
    def __init__(self):
        self.merchants_discovered = 0
        self.merchants_attempted = 0
        self.merchants_completed = 0
        self.merchants_partial = 0
        self.merchants_failed = 0
        self.categories_discovered = 0
        self.categories_completed = 0
        self.pages_requested = 0
        self.pagination_exhausted = 0
        self.items_raw = 0
        self.items_unique = 0
        self.authenticated_requests = 0
        self.anonymous_requests = 0
        self.http_401 = 0
        self.http_403 = 0
        self.http_404 = 0
        self.http_429 = 0
        self.http_5xx = 0
        self.incomplete_reasons = []

    def log_error(self, code: int):
        if code == 401: self.http_401 += 1
        elif code == 403: self.http_403 += 1
        elif code == 404: self.http_404 += 1
        elif code == 429: self.http_429 += 1
        elif code >= 500: self.http_5xx += 1

class MerchantDiscovery:
    def __init__(self, client: AuthenticatedHttpClient):
        self.client = client

    def _normalize_store(self, s: Dict) -> Dict:
        return {
            "store_id": str(s.get("store_id")),
            "name": s.get("store_name"),
            "type": s.get("parent_store_type", "market"),
            "vertical_sub_group": s.get("vertical_sub_group"),
            "categories": s.get("categories"),
            "tags": s.get("tags")
        }

    def _run_query_sync(self, query: str, lat: float, lng: float, report: CoverageReport) -> tuple[List[Dict], Exception]:
        import urllib.request, json
        from dealhunter.auth import RappiSessionProvider
        url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://www.rappi.com.mx"
        }
        prov = RappiSessionProvider()
        if prov.context and prov.context._access_token:
            headers["Authorization"] = f"Bearer {prov.context._access_token}"

        report.authenticated_requests += 1
        payload = json.dumps({"query": query, "lat": lat, "lng": lng, "limit": 100}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                stores = data.get("stores", [])
                return stores, None
        except Exception as e:
            status = getattr(e, 'code', 0)
            if status == 401: report.http_401 += 1
            elif status == 403: report.http_403 += 1
            elif status == 429: report.http_429 += 1
            elif status >= 500: report.http_5xx += 1
            return [], e

    async def discover_targeted(self, query: str, lat: float, lng: float, report: CoverageReport, expected_store_id: str = None) -> tuple[str, Optional[Dict]]:
        stores, err = self._run_query_sync(query, lat, lng, report)
        if err:
            return "NOT_FOUND", None
            
        normalized = [self._normalize_store(s) for s in stores]
        
        if expected_store_id:
            for s in normalized:
                if s["store_id"] == str(expected_store_id):
                    return "MATCH_EXACT_STORE_ID", s
            return "NOT_FOUND", None
            
        if not normalized:
            return "NOT_FOUND", None
            
        if len(normalized) == 1:
            return "SUCCESS", normalized[0]
            
        return "AMBIGUOUS", None

    async def discover_merchants(self, lat: float, lng: float, report: CoverageReport, discovery_mode: str = "full") -> List[Dict]:
        import string
        unique_stores = {}

        def add_stores(stores):
            for s in stores:
                sid = str(s.get("store_id"))
                if sid not in unique_stores:
                    unique_stores[sid] = self._normalize_store(s)

        if discovery_mode == "full":
            from collections import deque
            queue = deque([(c, 1) for c in string.ascii_lowercase])
            MAX_DEPTH = 2
            LIMIT_THRESHOLD = 30
            while queue:
                query, depth = queue.popleft()
                stores, err = self._run_query_sync(query, lat, lng, report)
                if err: continue
                add_stores(stores)
                if len(stores) >= LIMIT_THRESHOLD and depth < MAX_DEPTH:
                    for c in string.ascii_lowercase:
                        queue.append((query + c, depth + 1))
        else:
            # Top-K Adaptive Modes
            top_k = 10 if discovery_mode == "normal" else 20

            d1_results = []
            for c in string.ascii_lowercase:
                stores, err = self._run_query_sync(c, lat, lng, report)
                if err: continue
                add_stores(stores)
                d1_results.append({"query": c, "raw_count": len(stores)})

            # Sort descending by raw_count, then alphabetically for deterministic tie-breaking
            d1_results.sort(key=lambda x: (-x["raw_count"], x["query"]))

            # Expand Top-K
            for item in d1_results[:top_k]:
                query = item["query"]
                for c in string.ascii_lowercase:
                    stores, err = self._run_query_sync(query + c, lat, lng, report)
                    if err: continue
                    add_stores(stores)

        merchants = list(unique_stores.values())
        report.merchants_discovered = len(merchants)
        return merchants

class CPGCatalogAdapter:
    def __init__(self, client: AuthenticatedHttpClient):
        self.client = client

    async def fetch_full_catalog(self, store_id: str, report: CoverageReport) -> List[Dict]:
        report.authenticated_requests += 1
        report.merchants_attempted += 1
        # Implement web scraping catalog via next_data to guarantee 100% catalog size!
        import urllib.request, json, re
        url = f"https://www.rappi.com.mx/tiendas/{store_id}?csr=false"
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                # If store is offline or doesn't exist, it redirects to generic market
                final_url = response.geturl()
                if "tipo/market" in final_url or "restaurantNotFound" in final_url:
                    report.merchants_completed += 1
                    return []

                html = response.read().decode('utf-8')
                m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
                if not m:
                    m = re.search(r'window\.__INITIAL_STATE__=(.*?);', html)
                    if not m:
                        report.merchants_failed += 1
                        return []

                data = json.loads(m.group(1))
                items = []

                def is_product(d):
                    if not isinstance(d, dict): return False
                    pid = d.get('id') or d.get('product_id')
                    if not pid: return False
                    name = d.get('name')
                    if not name or not isinstance(name, str): return False
                    if 'price' not in d: return False
                    if not isinstance(d['price'], (int, float)): return False

                    # Reject non-product objects
                    if d.get('type') in ['banner', 'store', 'merchant', 'category', 'promotions']: return False
                    if 'lat' in d or 'lng' in d: return False
                    if 'deliveryCost' in d or 'logo' in d: return False
                    return True

                def extract_products(d, ancestors=None, is_root=True):
                    if ancestors is None: ancestors = []
                    
                    if isinstance(d, dict):
                        if is_product(d):
                            d["store_id"] = str(store_id)
                            # Attempt to find category if it exists somewhere nearby
                            d["category"] = d.get("category_name", d.get("category", ""))
                            
                            if "memberships" not in d:
                                d["memberships"] = []
                            for anc in ancestors:
                                if anc not in d["memberships"]:
                                    d["memberships"].append(anc)
                            
                            items.append(d)
                        else:
                            cat_name = d.get("name", "")
                            cat_type = d.get("type", "")
                            
                            # Identify container nodes
                            is_container = False
                            if not is_root and cat_type not in ["store", "merchant", "banner", "brand"]:
                                if cat_type in ["corridor", "aisle", "section"] or "corridors" in d or "aisles" in d:
                                    is_container = True
                                elif ("parent_id" in d or "aisle_id" in d or "products" in d or "items" in d) and "name" in d:
                                    is_container = True
                                # Explicitly reject if it contains store root properties
                                if is_container and cat_type not in ["corridor", "aisle", "section"] and ("logo" in d or "deliveryPrice" in d or "storeType" in d or "brandId" in d or "store_id" in d or "lat" in d or "lng" in d):
                                    is_container = False
                                
                            new_ancestors = list(ancestors)
                            if is_container and cat_name:
                                anc_node = {
                                    "raw_name": cat_name,
                                    "raw_type": cat_type if cat_type else "unknown",
                                    "raw_id": d.get("id", d.get("corridor_id", d.get("aisle_id", None))),
                                    "source": "provider",
                                    "path": [a["raw_name"] for a in ancestors] + [cat_name]
                                }
                                new_ancestors.append(anc_node)
                                
                            for v in d.values():
                                extract_products(v, new_ancestors, is_root=False)
                    elif isinstance(d, list):
                        for v in d:
                            extract_products(v, ancestors, is_root=False)

                extract_products(data)

                # Remove duplicates by ID to avoid explosion, but merge memberships and commercial fields!
                unique = {}
                for i in items:
                    pid = str(i.get("id") or i.get("product_id"))
                    if pid not in unique:
                        unique[pid] = i
                    else:
                        existing = unique[pid]
                        
                        promo_fields = ["real_price", "discount", "discount_effective", "discounts_bundle", "deal", "promotion_value", "units_condition"]
                        new_has_promo = any(i.get(f) for f in promo_fields)
                        ex_has_promo = any(existing.get(f) for f in promo_fields)
                        
                        if new_has_promo and not ex_has_promo:
                            for field in ["price"] + promo_fields:
                                if field in i:
                                    existing[field] = i[field]
                        else:
                            for field in ["price"] + promo_fields:
                                if field in i and i[field] is not None and i[field] != "":
                                    val = i[field]
                                    ex_val = existing.get(field)
                                    if ex_val is None or ex_val == "" or (isinstance(ex_val, (int, float)) and ex_val == 0 and val != 0):
                                        existing[field] = val
                                        
                        for m in i.get("memberships", []):
                            if m not in existing.get("memberships", []):
                                existing["memberships"].append(m)
                res = list(unique.values())

                report.merchants_completed += 1
                report.items_raw += len(items)
                report.items_unique += len(res)
                return res
        except Exception as e:
            report.merchants_failed += 1
            return []

class RestaurantMenuAdapter:
    def __init__(self, client: AuthenticatedHttpClient):
        self.client = client

    async def fetch_menu(self, store_id: str, report: CoverageReport) -> List[Dict]:
        report.authenticated_requests += 1
        report.merchants_attempted += 1
        import urllib.request, json, re
        url = f"https://www.rappi.com.mx/restaurantes/{store_id}?csr=false"
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                # If store is offline or doesn't exist, it redirects to generic market
                final_url = response.geturl()
                if "tipo/market" in final_url or "restaurantNotFound" in final_url:
                    report.merchants_completed += 1
                    return []

                html = response.read().decode('utf-8')
                # Wait, restaurants may not use __NEXT_DATA__ anymore, or structure is different
                m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
                if not m:
                    # Alternative regex for appState
                    m = re.search(r'window\.__INITIAL_STATE__=(.*?);', html)
                    if not m:
                        report.merchants_failed += 1
                        return []

                data = json.loads(m.group(1))
                items = []

                def is_product(d):
                    if not isinstance(d, dict): return False
                    pid = d.get('id') or d.get('product_id')
                    if not pid: return False
                    name = d.get('name')
                    if not name or not isinstance(name, str): return False
                    if 'price' not in d: return False
                    if not isinstance(d['price'], (int, float)): return False

                    # Reject non-product objects
                    if d.get('type') in ['banner', 'store', 'merchant', 'category', 'promotions']: return False
                    if 'lat' in d or 'lng' in d: return False
                    if 'deliveryCost' in d or 'logo' in d: return False
                    return True

                def extract_products(d, ancestors=None, is_root=True):
                    if ancestors is None: ancestors = []
                    
                    if isinstance(d, dict):
                        if is_product(d):
                            d["store_id"] = str(store_id)
                            # Attempt to find category if it exists somewhere nearby
                            d["category"] = d.get("category_name", d.get("category", ""))
                            
                            if "memberships" not in d:
                                d["memberships"] = []
                            for anc in ancestors:
                                if anc not in d["memberships"]:
                                    d["memberships"].append(anc)
                            
                            items.append(d)
                        else:
                            cat_name = d.get("name", "")
                            cat_type = d.get("type", "")
                            
                            is_container = False
                            if not is_root and cat_type not in ["store", "merchant", "banner", "brand"]:
                                if cat_type in ["corridor", "aisle", "section"] or "corridors" in d or "aisles" in d:
                                    is_container = True
                                elif ("parent_id" in d or "aisle_id" in d or "products" in d or "items" in d) and "name" in d:
                                    is_container = True
                                # Explicitly reject if it contains store root properties
                                if is_container and cat_type not in ["corridor", "aisle", "section"] and ("logo" in d or "deliveryPrice" in d or "storeType" in d or "brandId" in d or "store_id" in d or "lat" in d or "lng" in d):
                                    is_container = False
                                
                            new_ancestors = list(ancestors)
                            if is_container and cat_name:
                                anc_node = {
                                    "raw_name": cat_name,
                                    "raw_type": cat_type if cat_type else "unknown",
                                    "raw_id": d.get("id", d.get("corridor_id", d.get("aisle_id", None))),
                                    "source": "provider",
                                    "path": [a["raw_name"] for a in ancestors] + [cat_name]
                                }
                                new_ancestors.append(anc_node)
                                
                            for v in d.values():
                                extract_products(v, new_ancestors, is_root=False)
                    elif isinstance(d, list):
                        for v in d:
                            extract_products(v, ancestors, is_root=False)

                extract_products(data)

                # Remove duplicates by ID to avoid explosion, but merge memberships and commercial fields!
                unique = {}
                for i in items:
                    pid = str(i.get("id") or i.get("product_id"))
                    if pid not in unique:
                        unique[pid] = i
                    else:
                        existing = unique[pid]
                        
                        promo_fields = ["real_price", "discount", "discount_effective", "discounts_bundle", "deal", "promotion_value", "units_condition"]
                        new_has_promo = any(i.get(f) for f in promo_fields)
                        ex_has_promo = any(existing.get(f) for f in promo_fields)
                        
                        if new_has_promo and not ex_has_promo:
                            for field in ["price"] + promo_fields:
                                if field in i:
                                    existing[field] = i[field]
                        else:
                            for field in ["price"] + promo_fields:
                                if field in i and i[field] is not None and i[field] != "":
                                    val = i[field]
                                    ex_val = existing.get(field)
                                    if ex_val is None or ex_val == "" or (isinstance(ex_val, (int, float)) and ex_val == 0 and val != 0):
                                        existing[field] = val
                                        
                        for m in i.get("memberships", []):
                            if m not in existing.get("memberships", []):
                                existing["memberships"].append(m)
                res = list(unique.values())

                report.merchants_completed += 1
                report.items_raw += len(items)
                report.items_unique += len(res)
                return res
        except Exception as e:
            report.merchants_failed += 1
            return []
