with open("src/dealhunter/web/routes.py", "r") as f:
    content = f.read()

content = content.replace("@app.route('/stores/<store_id>')", "@app.route('/stores/<provider>/<store_id>')")
content = content.replace("def store_detail(store_id):", "def store_detail(provider, store_id):")
content = content.replace("detail = get_store_detail(db_path, store_id)", "detail = get_store_detail(db_path, provider, store_id)")
content = content.replace("products, total = get_store_products(db_path, store_id, page=page, search=search)", "products, total = get_store_products(db_path, provider, store_id, page=page, search=search)")

with open("src/dealhunter/web/routes.py", "w") as f:
    f.write(content)
