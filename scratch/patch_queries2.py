with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

content = content.replace("def get_product_detail(db_path, store_id, product_id):", "def get_product_detail(db_path, provider, store_id, product_id):")
content = content.replace("WHERE p.store_id = ? AND p.product_id = ?", "WHERE p.provider = ? AND p.store_id = ? AND p.product_id = ?")
content = content.replace("''', (store_id, product_id))", "''', (provider, store_id, product_id))")

content = content.replace("def get_anchor_compare(db_path, store_id, product_id):", "def get_anchor_compare(db_path, provider, store_id, product_id):")
content = content.replace("return compare_with_anchor(db_path, store_id, product_id)", "return compare_with_anchor(db_path, provider, store_id, product_id)")

content = content.replace("JOIN stores s ON p.store_id = s.store_id", "JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id")


with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)
