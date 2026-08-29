with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

content = content.replace("def get_restaurant_detail(db_path, store_id):", "def get_restaurant_detail(db_path, provider, store_id):")
content = content.replace("WHERE provider = ? AND store_id = ? AND type = 'restaurants'\", (store_id,)", "WHERE provider = ? AND store_id = ? AND type = 'restaurants'\", (provider, store_id,)")

# Also we need to check WHERE store_id = ? in get_restaurant_detail
content = content.replace("SELECT category, COUNT(*) FROM products WHERE store_id = ?", "SELECT category, COUNT(*) FROM products WHERE provider = ? AND store_id = ?")
content = content.replace("GROUP BY category\", (store_id,)", "GROUP BY category\", (provider, store_id,)")

content = content.replace("SELECT product_id, name, image, category, has_toppings FROM products WHERE store_id = ?", "SELECT product_id, name, image, category, has_toppings FROM products WHERE provider = ? AND store_id = ?")
content = content.replace("ORDER BY category, name\", (store_id,)", "ORDER BY category, name\", (provider, store_id,)")

content = content.replace("SELECT product_id, price FROM observations WHERE store_id = ?", "SELECT product_id, price FROM observations WHERE provider = ? AND store_id = ?")
content = content.replace("AND timestamp = (SELECT MAX(timestamp) FROM observations WHERE store_id = ?)\", (store_id, store_id)", "AND timestamp = (SELECT MAX(timestamp) FROM observations WHERE provider = ? AND store_id = ?)\", (provider, store_id, provider, store_id)")

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)
