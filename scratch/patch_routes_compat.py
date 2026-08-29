import re
with open("src/dealhunter/web/routes.py", "r") as f:
    content = f.read()

compat_routes = """
    # URL Backward Compatibility
    @app.route('/products/<store_id>/<product_id>')
    def product_detail_compat(store_id, product_id):
        return redirect(url_for('product_detail', provider='rappi', store_id=store_id, product_id=product_id))

    @app.route('/stores/<store_id>')
    def store_detail_compat(store_id):
        return redirect(url_for('store_detail', provider='rappi', store_id=store_id))

    @app.route('/restaurants/<store_id>')
    def restaurant_detail_compat(store_id):
        return redirect(url_for('restaurant_detail', provider='rappi', store_id=store_id))

"""

# Insert compat routes after definition of `def product_detail`
content = content.replace("def product_detail(provider, store_id, product_id):", "def product_detail(provider, store_id, product_id):")

# Better: just append it before `return app`
content = content.replace("    return app", compat_routes + "    return app")
# Wait, `redirect` and `url_for` need to be imported. They should be imported from flask at the top.
# They are usually imported in `routes.py`. Let's assume they are.

with open("src/dealhunter/web/routes.py", "w") as f:
    f.write(content)
