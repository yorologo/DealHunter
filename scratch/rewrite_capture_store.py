import re

with open("src/dealhunter/providers/uber_eats/browser_transport.py", "r") as f:
    content = f.read()

new_capture = """
    async def capture_store(self, store_uuid, max_pages=15):
        \"\"\"Capture a complete store catalog using browser-context fetch.\"\"\"
        merged_data = {
            "uuid": store_uuid,
            "sections": [],
            "catalogSectionsMap": {}
        }
        
        pages_fetched = 0
        offset = 0
        total_raw_items = 0

        for page in range(max_pages):
            try:
                page_result = await self._fetch_store_page(store_uuid, offset)
            except Exception as e:
                logger.warning("Store page error at offset %d: %s", offset, e)
                break
            
            if page_result is None or page_result.get("error"):
                break

            pages_fetched += 1
            
            # Merge top-level fields on the first page
            if page == 0:
                merged_data["title"] = page_result.get("storeTitle")
                merged_data["slug"] = page_result.get("slug")
                merged_data["isOpen"] = page_result.get("isOpen")
                merged_data["isOrderable"] = page_result.get("isOrderable")
            
            # Accumulate sections
            sections = page_result.get("sections", [])
            merged_data["sections"].extend(sections)
            
            # Accumulate catalogSectionsMap
            csm = page_result.get("catalogSectionsMap", {})
            items_in_page = 0
            for k, v in csm.items():
                if k not in merged_data["catalogSectionsMap"]:
                    merged_data["catalogSectionsMap"][k] = []
                merged_data["catalogSectionsMap"][k].extend(v)
                
                # Estimate items for completeness metrics
                for el in v:
                    if el.get("type") in ("VERTICAL_GRID", "HORIZONTAL_GRID"):
                        items_in_page += len(el.get("payload", {}).get("standardItemsPayload", {}).get("catalogItems", []))
            
            total_raw_items += items_in_page
            
            paging = page_result.get("pagingInfo") or {}
            new_offset = paging.get("offset")
            
            # If no items were found, or the offset didn't advance, stop.
            if not new_offset or new_offset <= offset or items_in_page == 0:
                break
            offset = new_offset
            await asyncio.sleep(INTER_PAGE_DELAY)

        completeness = "COMPLETE" if pages_fetched > 0 and total_raw_items > 0 else "FAILED"
        if pages_fetched > 0 and offset > 0 and pages_fetched >= max_pages:
            completeness = "PARTIAL"

        return {
            "status": "success" if total_raw_items > 0 else "empty",
            "store_uuid": store_uuid,
            "completeness": completeness,
            "pages_fetched": pages_fetched,
            "products_raw": total_raw_items,
            "raw_payload": merged_data,
        }
"""

content = re.sub(r'    async def capture_store.*?(?=    async def _fetch_store_page)', new_capture, content, flags=re.DOTALL)

with open("src/dealhunter/providers/uber_eats/browser_transport.py", "w") as f:
    f.write(content)
