with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

bad_sql = """
            SELECT id, store_id, product_id, price, provider, original_price, discount_effective, 
                   has_pro_offer, pro_price, pro_discount_effective, promotion_type, availability, provider
"""
good_sql = """
            SELECT id, store_id, product_id, price, original_price, discount_effective, 
                   has_pro_offer, pro_price, pro_discount_effective, promotion_type, availability, provider
"""
content = content.replace(bad_sql, good_sql)

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
