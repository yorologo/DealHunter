import re
with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

# Fix get_store_detail
content = content.replace("c.execute(\"SELECT name, type FROM stores WHERE provider = ? AND store_id = ?\", (store_id,))", "c.execute(\"SELECT name, type FROM stores WHERE provider = ? AND store_id = ?\", (provider, store_id))")
content = content.replace("c.execute(\"SELECT COUNT(product_id) FROM products WHERE provider = ? AND store_id = ?\", (store_id,))", "c.execute(\"SELECT COUNT(product_id) FROM products WHERE provider = ? AND store_id = ?\", (provider, store_id))")
content = content.replace("c.execute(\"SELECT MAX(timestamp) FROM observations WHERE provider = ? AND store_id = ?\", (store_id,))", "c.execute(\"SELECT MAX(timestamp) FROM observations WHERE provider = ? AND store_id = ?\", (provider, store_id))")

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)

with open("src/dealhunter/web/routes.py", "r") as f:
    content = f.read()

content = content.replace("res = get_restaurant_detail(db_path, store_id)", "res = get_restaurant_detail(db_path, provider, store_id)")
# Wait, I also need to check `detail = get_restaurant_detail` ?
content = content.replace("detail = get_restaurant_detail(db_path, store_id)", "detail = get_restaurant_detail(db_path, provider, store_id)")

with open("src/dealhunter/web/routes.py", "w") as f:
    f.write(content)
