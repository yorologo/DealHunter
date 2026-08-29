with open("src/dealhunter/web/routes.py", "r") as f:
    content = f.read()

content = content.replace("@app.route('/restaurants/<store_id>')", "@app.route('/restaurants/<provider>/<store_id>')")
content = content.replace("def restaurant_detail(store_id):", "def restaurant_detail(provider, store_id):")
content = content.replace("res = get_restaurant_detail(db_path, store_id)", "res = get_restaurant_detail(db_path, provider, store_id)")

with open("src/dealhunter/web/routes.py", "w") as f:
    f.write(content)
