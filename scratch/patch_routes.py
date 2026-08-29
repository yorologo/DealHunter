with open("src/dealhunter/web/routes.py", "r") as f:
    content = f.read()

content = content.replace("@app.route('/products/<store_id>/<product_id>')", "@app.route('/products/<provider>/<store_id>/<product_id>')")
content = content.replace("def product_detail(store_id, product_id):", "def product_detail(provider, store_id, product_id):")
content = content.replace("p = get_product_detail(db_path, store_id, product_id)", "p = get_product_detail(db_path, provider, store_id, product_id)")

content = content.replace("res = get_anchor_compare(db_path, store_id, product_id)", "provider = request.args.get('provider')\n            res = get_anchor_compare(db_path, provider, store_id, product_id)")

with open("src/dealhunter/web/routes.py", "w") as f:
    f.write(content)
