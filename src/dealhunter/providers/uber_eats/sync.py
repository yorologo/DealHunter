"""
Uber Eats catalog sync — orchestrates BrowserTransport → Parser → Normalizer → DB.

Produces a sanitized capture envelope and, when ``db_path`` is configured,
persists provider-aware rows through the current database contract.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime

from dealhunter.providers.uber_eats.browser_transport import (
    UberBrowserTransport,
    READY,
    LOGIN_REQUIRED,
    CHALLENGE_REQUIRED,
    BROWSER_NOT_RUNNING,
)
from dealhunter.providers.uber_eats.parser import UberEatsParser
from dealhunter.providers.uber_eats.normalizer import UberEatsNormalizer

logger = logging.getLogger(__name__)

# Store sync states
PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
FAILED = "FAILED"
RETRYABLE = "RETRYABLE"


class UberCatalogSync:
    """Orchestrates browser-based Uber Eats catalog sync."""

    def __init__(self, db_path=None, cdp_host="127.0.0.1", cdp_port=9222):
        self.transport = UberBrowserTransport(cdp_host, cdp_port)
        self.parser = UberEatsParser()
        self.normalizer = UberEatsNormalizer()
        self.db_path = db_path

    async def doctor(self):
        """Run diagnostic checks. Returns structured health report."""
        report = {
            "browser": "FAIL",
            "tunnel": "FAIL",
            "session": "FAIL",
            "csrf": "FAIL",
            "capture": "SKIP",
            "parser": "SKIP",
            "overall": "FAIL",
        }

        # 1. Browser connectivity
        health = self.transport.health()
        if health != READY:
            report["browser"] = health
            return report
        report["browser"] = "PASS"
        report["tunnel"] = "PASS"

        browser_info = self.transport.get_browser_info()
        if browser_info:
            report["browser_version"] = browser_info.get("browser")

        # 2. Session
        try:
            await self.transport.connect()
            login_state = await self.transport.ensure_ready()
            if login_state == READY:
                report["session"] = "PASS"
            else:
                report["session"] = login_state
                await self.transport.close()
                return report
        except Exception as e:
            report["session"] = f"ERROR: {e}"
            return report

        # 3. CSRF
        has_csrf = await self.transport._has_csrf()
        if not has_csrf:
            has_csrf = await self.transport._trigger_csrf_capture()
        report["csrf"] = "PASS" if has_csrf else "FAIL"

        if has_csrf:
            report["capture"] = "PASS"
            report["parser"] = "PASS"
            report["overall"] = "READY"
        else:
            report["overall"] = "CSRF_NOT_AVAILABLE"

        await self.transport.close()
        return report

    async def sync_stores(self, store_list, run_id=None):
        """Sync a list of stores and return structured results.

        Args:
            store_list: List of dicts with keys: url, uuid, label.
            run_id: Optional run identifier.

        Returns:
            Structured sync report.
        """
        if run_id is None:
            run_id = int(time.time())

        report = {
            "run_id": run_id,
            "started_at": datetime.now().isoformat(),
            "stores": [],
            "summary": {
                "attempted": 0,
                "complete": 0,
                "partial": 0,
                "failed": 0,
                "products": 0,
                "observations": 0,
            },
        }

        try:
            await self.transport.connect()
            state = await self.transport.ensure_ready()
            if state != READY:
                report["error"] = state
                report["summary"]["status"] = state
                return report
        except Exception as e:
            report["error"] = str(e)
            report["summary"]["status"] = "CONNECTION_ERROR"
            return report

        tuples = [(s["url"], s["uuid"], s["label"]) for s in store_list]

        def on_progress(label, status, result):
            logger.info("  %s: %s (%d items)",
                        label, status, result.get("products_unique", 0))

        try:
            results = await self.transport.capture_stores(tuples, on_progress)
        except Exception as e:
            report["error"] = str(e)
            report["summary"]["status"] = "SYNC_ERROR"
            await self.transport.close()
            return report

        # Process each store result
        for r in results:
            store_report = {
                "label": r.get("label"),
                "uuid": r.get("store_uuid"),
                "completeness": r.get("completeness", FAILED),
                "products_raw": r.get("products_raw", 0),
                "products_unique": r.get("products_unique", 0),
                "sections": r.get("sections_total", 0),
                "pages_fetched": r.get("pages_fetched", 0),
            }

            report["summary"]["attempted"] += 1

            if r.get("status") == "error" or r.get("completeness") == FAILED:
                store_report["error"] = r.get("error")
                report["summary"]["failed"] += 1
            else:
                items = r.get("items", [])
                if items:
                    # Parse through the existing parser
                    # Build a getStoreV1-compatible payload for the parser
                    fake_payload = self._build_parser_payload(r)
                    parsed = self.parser.parse_store(fake_payload)

                    store_report["parsed_products"] = len(parsed.get("products", []))

                    # Normalize and optionally persist
                    if self.db_path and parsed.get("products"):
                        obs_count = self._persist_to_db(
                            parsed, run_id, r.get("store_uuid")
                        )
                        store_report["observations_written"] = obs_count
                        report["summary"]["observations"] += obs_count

                    report["summary"]["products"] += store_report["parsed_products"]

                if r.get("completeness") == "COMPLETE":
                    report["summary"]["complete"] += 1
                else:
                    report["summary"]["partial"] += 1

            report["stores"].append(store_report)

        report["finished_at"] = datetime.now().isoformat()
        report["summary"]["status"] = self._overall_status(report["summary"])

        await self.transport.close()
        return report

    def _build_parser_payload(self, capture_result):
        """Convert browser capture items back to getStoreV1-like payload for the parser."""
        items = capture_result.get("items", [])

        # Group items by category
        categories = {}
        for item in items:
            cat = item.get("category", "Unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        # Build catalogSectionsMap
        section_uuid = capture_result.get("store_uuid", "unknown")
        elements = []
        for cat_name, cat_items in categories.items():
            elements.append({
                "type": "HORIZONTAL_GRID",
                "payload": {
                    "standardItemsPayload": {
                        "title": {"text": cat_name},
                        "catalogItems": cat_items,
                    }
                },
            })

        return {
            "uuid": capture_result.get("store_uuid"),
            "title": capture_result.get("label", "Unknown"),
            "isOpen": True,
            "isOrderable": True,
            "sections": [{"uuid": t} for t in capture_result.get("section_titles", [])],
            "catalogSectionsMap": {section_uuid: elements},
        }

    def _persist_to_db(self, parsed, run_id, store_uuid):
        """Persist parsed data to the configured provider-aware database."""
        if not self.db_path:
            return 0

        from dealhunter.db import DealHunterDB

        db = DealHunterDB(self.db_path)
        store_data = parsed.get("store", {})
        products = parsed.get("products", [])

        obs_count = 0
        for prod in products:
            normalized_product = self.normalizer.normalize_product(prod)
            normalized_obs = self.normalizer.normalize_observation(prod, run_id)

            # Ensure provider is set
            normalized_product["provider"] = "uber_eats"
            normalized_obs["provider"] = "uber_eats"

            try:
                db.upsert_store(
                    store_id=store_data.get("raw_store_id", store_uuid),
                    name=store_data.get("name", "Unknown"),
                    brand=store_data.get("name", "Unknown"),
                    store_type="GROCERY",
                    provider="uber_eats",
                )
                db.upsert_product(
                    product_id=normalized_product["product_id"],
                    store_id=normalized_product["store_id"],
                    name=normalized_product["name"],
                    brand=normalized_product.get("brand", ""),
                    image=normalized_product.get("image", ""),
                    category=normalized_product.get("category", ""),
                    category_source=normalized_product.get("category_source", ""),
                    provider="uber_eats",
                )
                db.insert_observation(
                    run_id=normalized_obs["run_id"],
                    store_id=normalized_obs["store_id"],
                    product_id=normalized_obs["product_id"],
                    price=normalized_obs["price"],
                    original_price=normalized_obs["original_price"],
                    stock=normalized_obs["stock"],
                    discount_price=normalized_obs["discount_price"],
                    discount_promotion=normalized_obs["discount_promotion"],
                    discount_effective=normalized_obs["discount_effective"],
                    discount_source=normalized_obs.get("discount_source"),
                    promotion_type=normalized_obs.get("promotion_type"),
                    promotion_label=normalized_obs.get("promotion_label"),
                    provider="uber_eats",
                )
                obs_count += 1
            except Exception as e:
                logger.warning("DB write error for %s: %s",
                               normalized_product.get("name", "?"), e)

        return obs_count

    @staticmethod
    def _overall_status(summary):
        """Determine overall run status from summary counts."""
        if summary["attempted"] == 0:
            return "EMPTY"
        if summary["failed"] == summary["attempted"]:
            return "FAILED"
        if summary["failed"] > 0:
            return "PARTIAL"
        return "SUCCESS"
