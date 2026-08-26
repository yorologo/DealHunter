import re

class UberEatsParser:
    def __init__(self):
        self.discount_regex = re.compile(r"(?:discounted from|el precio anterior era) \$([\d\,\.]+)")
        self.price_regex = re.compile(r"\$([\d\,\.]+)")

    def parse_accessibility_price(self, text):
        if not text:
            return None
        match = self.discount_regex.search(text)
        if match:
            val_str = match.group(1).replace(',', '')
            try:
                return float(val_str)
            except ValueError:
                pass
        return None


    def parse_store(self, payload):
        store_info = {
            "provider": "uber_eats",
            "raw_store_id": payload.get("uuid"),
            "name": payload.get("title"),
            "slug": payload.get("slug"),
            "is_open": payload.get("isOpen"),
            "is_available": payload.get("isOrderable")
        }
        
        products_dict = {}
        sections = payload.get("sections", [])
        catalog_map = payload.get("catalogSectionsMap", {})
        
        for elements in catalog_map.values():
            for el in elements:
                el_type = el.get("type")
                if el_type in ("VERTICAL_GRID", "HORIZONTAL_GRID"):
                    standard_payload = el.get("payload", {}).get("standardItemsPayload", {})
                    category_name = standard_payload.get("title", {}).get("text", "Sin Categoría")
                    
                    items = standard_payload.get("catalogItems", [])
                    for item in items:
                        prod_id = item.get("uuid")
                        if not prod_id:
                            continue
                            
                        if prod_id not in products_dict:
                            price_int = item.get("price")
                            if price_int is not None and type(price_int) is int:
                                price = price_int / 100.0
                            else:
                                price = None
                                
                            tagline_acc = item.get("priceTagline", {}).get("accessibilityText", "")
                            reference_price = self.parse_accessibility_price(tagline_acc)
                            if reference_price is None:
                                reference_price = price
                                reference_price_source = "structured" if price is not None else "unknown"
                            else:
                                reference_price_source = "accessibility"
                                
                            if reference_price and price and reference_price < price:
                                reference_price = price
                                reference_price_source = "fallback_override"

                            is_sold_out = item.get("isSoldOut")
                            availability = "UNKNOWN"
                            if is_sold_out is True:
                                availability = "UNAVAILABLE"
                            elif is_sold_out is False:
                                availability = "AVAILABLE"

                            products_dict[prod_id] = {
                                "provider": "uber_eats",
                                "raw_store_id": payload.get("uuid"),
                                "raw_product_id": prod_id,
                                "name": item.get("title"),
                                "description": item.get("itemDescription", ""),
                                "image_url": item.get("imageUrl", ""),
                                "price": price,
                                "reference_price": reference_price,
                                "reference_price_source": reference_price_source,
                                "promotion_uuid": item.get("promoInfo", {}).get("promotionUUID"),
                                "availability": availability,
                                "category": category_name,
                                "memberships": [{"raw_type": "GRID", "raw_name": category_name}]
                            }
                        else:
                            # Add membership
                            products_dict[prod_id]["memberships"].append({"raw_type": "GRID", "raw_name": category_name})

        return {
            "store": store_info,
            "products": list(products_dict.values())
        }
