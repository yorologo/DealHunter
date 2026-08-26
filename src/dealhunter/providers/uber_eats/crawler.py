import asyncio
import logging
from .runtime import ChromiumRuntime
from .browser_transport import UberBrowserTransport
from .feed_v1 import parse_feed_v1
from .parser import UberEatsParser
from .normalizer import UberEatsNormalizer

logger = logging.getLogger(__name__)

async def _run_uber_sync_async(config, lat, lng, conn, run_id):
    rt = ChromiumRuntime()
    logger.info("Starting Chromium Runtime for Uber Sync...")
    try:
        rt.start()
    except Exception as e:
        logger.error(f"Failed to start Chromium Runtime: {e}")
        return "FAILED_FINAL", 0

    transport = UberBrowserTransport()
    try:
        await transport.ensure_ready()
    except Exception as e:
        logger.error(f"Failed to connect transport: {e}")
        rt.stop()
        return "FAILED_RETRYABLE", 0
        
    reqs = 0
    state = "COMPLETE"

    try:
        # Discovery: Use getFeedV1 to find stores in range
        logger.info(f"Discovering Uber Eats stores at {lat}, {lng}...")
        try:
            feed_data = await transport.fetch_feed_v1(lat, lng)
            reqs += 1
        except Exception as e:
            logger.error(f"Failed to fetch feed: {e}")
            return "FAILED_RETRYABLE", reqs
            
        stores = parse_feed_v1(feed_data)
        logger.info(f"Discovered {len(stores)} stores via feed.")
        if not stores:
            logger.warning("No stores found in feed. Session might be invalid or out of range.")
            return "PARTIAL", reqs
            
        parser = UberEatsParser()
        normalizer = UberEatsNormalizer()
        


        for s in stores:
            # Sync store
            logger.info(f"Syncing store: {s['name']} ({s['uuid']})")
            
            c = conn.cursor()
            c.execute('''INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)
                         VALUES (?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP, ?)
                         ON CONFLICT(provider, store_id) DO UPDATE SET last_seen_at=CURRENT_TIMESTAMP''',
                      ("uber_eats", s['uuid'], s['name'], s['name'], "RESTAURANT" if s.get('type') == 'restaurant' else "GROCERY", "restaurant" if s.get('type') == 'restaurant' else "market"))
            conn.commit()

            offset = 0
            items_found = 0
            while True:
                try:
                    store_data = await transport.fetch_store_v1(s['uuid'], offset=offset)
                    reqs += 1
                except Exception as e:
                    logger.error(f"Failed to fetch store {s['uuid']} offset {offset}: {e}")
                    state = "PARTIAL"
                    break

                parsed = parser.parse_store(store_data)
                prods = parsed.get("products", [])
                
                    
                for p in prods:
                    norm_p = normalizer.normalize_product(p)
                    norm_o = normalizer.normalize_observation(p, run_id)
                    
                    c.execute('''INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                 ON CONFLICT(provider, store_id, product_id) DO UPDATE SET 
                                 name=excluded.name, image=excluded.image, category=excluded.category''',
                              ("uber_eats", norm_p['store_id'], norm_p['product_id'], norm_p['name'], norm_p.get('brand', ''), norm_p.get('image', ''), norm_p.get('category', ''), 'uber_eats_grid'))
                    
                    c.execute('''INSERT INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, availability, stock)
                                 VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (run_id, "uber_eats", norm_p['store_id'], norm_p['product_id'], norm_o.get('price'), norm_o.get('original_price'), norm_o.get('discount_price', 0), norm_o.get('discount_promotion', 0), norm_o.get('discount_effective', 0), norm_o.get('discount_source'), norm_o.get('promotion_type'), norm_o.get('promotion_label'), norm_o.get('availability', 'AVAILABLE'), norm_o.get('stock', 1)))
                    conn.commit()
                    items_found += 1
                    
                paging = store_data.get("paging", {})
                next_offset = paging.get("offset")
                if next_offset and next_offset > offset:
                    offset = next_offset
                else:
                    break
                    
            logger.info(f"Finished store {s['name']}. Extracted {items_found} items.")

    except Exception as e:
        logger.exception("Error during Uber sync")
        state = "FAILED_FINAL"
    finally:
        await transport.close()
        rt.stop()

    return state, reqs

def run_uber_sync(config, lat, lng, conn, run_id):
    return asyncio.run(_run_uber_sync_async(config, lat, lng, conn, run_id))
