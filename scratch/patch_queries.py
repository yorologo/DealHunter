import re
with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

content = content.replace("def get_product_detail(db_path, store_id, product_id):", "def get_product_detail(db_path, provider, store_id, product_id):")
content = content.replace("WHERE p.store_id = ? AND p.product_id = ?", "WHERE p.provider = ? AND p.store_id = ? AND p.product_id = ?")
content = content.replace("(store_id, product_id)", "(provider, store_id, product_id)")
# But wait, there might be other (store_id, product_id) tuples in queries.py! Let's be careful.
content = content.replace("''', (store_id, product_id))", "''', (provider, store_id, product_id))")

# Wait, the above replaced (store_id, product_id) everywhere in queries.py.
# There are 2 instances: get_product_detail has ONE execute, another execute is for history.
