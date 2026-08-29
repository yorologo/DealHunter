import re
with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

content = content.replace("WHERE store_id = ? AND product_id = ?", "WHERE provider = ? AND store_id = ? AND product_id = ?")

# also fix enrich_products_with_metrics where it groups observations
# wait, enrich_products_with_metrics has "SELECT store_id, product_id, price, timestamp, original_price FROM observations"
# Does it need provider? Yes! If multiple providers have the same store/product id, we need to match them properly!
content = content.replace("SELECT store_id, product_id, price, timestamp, original_price", "SELECT provider, store_id, product_id, price, timestamp, original_price")
content = content.replace("key = (r[0], r[1])", "key = (r[0], r[1], r[2])")

# wait, how are `conds` generated in enrich_products_with_metrics?
content = content.replace("conds.append(\"(store_id = ? AND product_id = ?)\")", "conds.append(\"(provider = ? AND store_id = ? AND product_id = ?)\")")
content = content.replace("params.extend([p['store_id'], p['product_id']])", "params.extend([p['provider'], p['store_id'], p['product_id']])")

# what about `p = products[0]` to get `p['provider']` etc?
content = content.replace("obs = obs_map.get((p['store_id'], p['product_id']), [])", "obs = obs_map.get((p['provider'], p['store_id'], p['product_id']), [])")

# Also fix the store details: SELECT MAX(timestamp) FROM observations WHERE store_id = ?
# and WHERE product_id = o.product_id AND store_id = ?
# wait, those are in `get_store_detail` ?
content = content.replace("WHERE p.store_id = ?", "WHERE p.provider = ? AND p.store_id = ?")
content = content.replace("WHERE o.store_id = ? AND o.availability = 'AVAILABLE'", "WHERE o.provider = ? AND o.store_id = ? AND o.availability = 'AVAILABLE'")
content = content.replace("WHERE o.store_id = ? AND o.discount_effective > 0", "WHERE o.provider = ? AND o.store_id = ? AND o.discount_effective > 0")
content = content.replace("WHERE product_id = o.product_id AND store_id = ?", "WHERE provider = o.provider AND product_id = o.product_id AND store_id = ?")
content = content.replace("MAX(timestamp) FROM observations WHERE store_id = ?", "MAX(timestamp) FROM observations WHERE provider = ? AND store_id = ?")
# Note that get_store_detail doesn't have provider argument yet! Let's check get_store_detail.

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)
