from dealhunter.providers.registry import validate_provider
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
    stores_completed = 0
    stores_failed = 0

    try:
        # Discovery: Use getFeedV1 to find stores in range
        logger.info(f"Discovering Uber Eats stores at {lat}, {lng}...")
        stores = []
        for query in ["supermercado", "restaurante"]:
            try:
                feed_data = await transport.fetch_feed_v1(lat, lng, query=query)
                reqs += 1
                q_stores = parse_feed_v1(feed_data)
                for qs in q_stores:
                    if not any(s["uuid"] == qs["uuid"] for s in stores):
                        stores.append(qs)
            except Exception as e:
                logger.error(f"Failed to fetch feed for {query}: {e}")
                # Tolerate partial failure for one query
                
        if not stores and reqs == 0:
            return "FAILED_RETRYABLE", reqs

        logger.info(f"Discovered {len(stores)} stores via feed.")
        if not stores:
            logger.warning("No stores found in feed. Session might be invalid or out of range.")
            return "PARTIAL", reqs

        parser = UberEatsParser()
        normalizer = UberEatsNormalizer()

        for s in stores:
            # Sync store
            logger.info(f"Syncing store: {s['name']} ({s['uuid']})")

            try:
                c = conn.cursor()
                validate_provider('uber_eats')
                c.execute('''INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)
                             VALUES (?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP, ?)
                             ON CONFLICT(provider, store_id) DO UPDATE SET 
                             last_seen_at=CURRENT_TIMESTAMP, 
                             name=excluded.name,
                             type = CASE WHEN excluded.type != 'UNKNOWN' THEN excluded.type ELSE type END,
                             vertical = CASE WHEN excluded.vertical != 'UNKNOWN' THEN excluded.vertical ELSE vertical END''',
                          ("uber_eats", s['uuid'], s['name'], s['name'], 
                           "RESTAURANT" if s.get('type') == 'restaurant' else ("GROCERY" if s.get('type') == 'grocery' else "UNKNOWN"), 
                           "RESTAURANTS" if s.get('type') == 'restaurant' else ("MARKET" if s.get('type') == 'grocery' else "UNKNOWN")))
                conn.commit()

                offset = 0
                items_found = 0
                store_failed = False
                while True:
                    try:
                        store_data = await transport.fetch_store_v1(s['uuid'], offset=offset)
                        reqs += 1
                    except Exception as e:
                        logger.error(f"Failed to fetch store {s['uuid']} offset {offset}: {e}")
                        store_failed = True
                        break

                    payload = store_data.get("data", store_data)
                    parsed = parser.parse_store(payload)
                    prods = parsed.get("products", [])

                    for p in prods:
                        norm_p = normalizer.normalize_product(p)
                        norm_o = normalizer.normalize_observation(p, run_id)

                        validate_provider('uber_eats')
                        c.execute('''INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                     ON CONFLICT(provider, store_id, product_id) DO UPDATE SET
                                     name=excluded.name, image=excluded.image, category=excluded.category''',
                                  ("uber_eats", norm_p['store_id'], norm_p['product_id'], norm_p['name'], norm_p.get('brand', ''), norm_p.get('image', ''), norm_p.get('category', ''), 'uber_eats_grid'))

                        c.execute('''INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, availability, stock)
                                     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (run_id, "uber_eats", norm_p['store_id'], norm_p['product_id'], norm_o.get('price'), norm_o.get('original_price'), norm_o.get('discount_price', 0), norm_o.get('discount_promotion', 0), norm_o.get('discount_effective', 0), norm_o.get('discount_source'), norm_o.get('promotion_type'), norm_o.get('promotion_label'), norm_o.get('availability', 'AVAILABLE'), norm_o.get('stock', 1)))
                        items_found += 1

                    paging = store_data.get("paging", {})
                    next_offset = paging.get("offset")
                    if next_offset and next_offset > offset:
                        offset = next_offset
                    else:
                        break


                if store_failed:
                    stores_failed += 1
                    conn.rollback()
                    logger.warning(f"Store {s['name']} failed. Rolled back partial batch.")
                else:
                    # Commit per-store batch only if fully completed
                    conn.commit()
                    stores_completed += 1
                    logger.info(f"Finished store {s['name']}. Extracted {items_found} items.")


            except Exception as e:
                logger.error(f"Error processing store {s['name']}: {e}")
                stores_failed += 1
                try:
                    conn.rollback()
                except Exception:
                    pass

    except Exception as e:
        logger.exception("Error during Uber sync")
        return "FAILED_FINAL", reqs
    finally:
        await transport.close()
        rt.stop()

    # Compute final state from actual results
    if stores_completed == 0:
        state = "FAILED_FINAL"
    elif stores_failed > 0:
        state = "PARTIAL"
    else:
        state = "COMPLETE"

    logger.info(f"Uber sync finished: {state} (completed={stores_completed}, failed={stores_failed}, reqs={reqs})")
    return state, reqs

def run_uber_sync(config, lat, lng, conn, run_id):
    return asyncio.run(_run_uber_sync_async(config, lat, lng, conn, run_id))
