from datetime import datetime

class UberEatsNormalizer:
    def normalize_store(self, parsed_store):
        return {
            "store_id": parsed_store.get("raw_store_id"),
            "name": parsed_store.get("name"),
            "brand": parsed_store.get("name"),
            "type": "RESTAURANT" # Uber Eats is predominantly restaurants in this context, or we can leave it generic
        }
        
    def normalize_product(self, parsed_product):
        # We leave store_id and product_id as the raw UUIDs.
        return {
            "product_id": parsed_product.get("raw_product_id"),
            "store_id": parsed_product.get("raw_store_id"),
            "name": parsed_product.get("name"),
            "brand": "",
            "image": parsed_product.get("image_url"),
            "category": parsed_product.get("category"),
            "category_source": "uber_eats_grid",
            "quantity": None,
            "unit": None,
            "pack_count": 1,
            "has_toppings": 0,
            "memberships": parsed_product.get("memberships", [])
        }
        
    def normalize_observation(self, parsed_product, run_id):
        price = parsed_product.get("price")
        original_price = parsed_product.get("reference_price")
        
        discount_price = 0.0
        if price is not None and original_price is not None and original_price > 0 and original_price > price:
            discount_price = (1 - (price / original_price)) * 100
            
        return {
            "run_id": run_id,
            "store_id": parsed_product.get("raw_store_id"),
            "product_id": parsed_product.get("raw_product_id"),
            "price": price,
            "original_price": original_price,
            "stock": 1 if parsed_product.get("availability") == "AVAILABLE" else 0,
            "timestamp": datetime.now().isoformat(),
            "discount_price": discount_price,
            "discount_promotion": 0.0,
            "discount_effective": discount_price,
            "discount_source": "uber_price_tagline" if discount_price > 0 else None,
            "promotion_type": "uber_promo" if parsed_product.get("promotion_uuid") else None,
            "promotion_label": parsed_product.get("promotion_uuid"),
            "availability": parsed_product.get("availability")
        }
