with open("src/dealhunter/historico.py", "r") as f:
    content = f.read()

content = content.replace("key = (r[1], r[2]) # product_id, store_id", "key = (r[0], r[1], r[2])")
content = content.replace("key = (pid, sid)", "key = (provider, pid, sid)")

# Wait, the observation loop for `compare_stores`
obs_loop_old = """
    for r in c.fetchall():
        provider, pid, sid, price, ts_str, orig_price = r
        key = (pid, sid)
        if key in products_map:
"""
obs_loop_new = """
    for r in c.fetchall():
        provider, pid, sid, price, ts_str, orig_price = r
        key = (provider, pid, sid)
        if key in products_map:
"""
content = content.replace(obs_loop_old.strip(), obs_loop_new.strip())

# The other one in `compare_with_anchor`
content = content.replace("key = (r[1], r[2])\n        products_map[key] =", "key = (r[0], r[1], r[2])\n        products_map[key] =")

anchor_map_old = 'products_map[(anchor["product_id"], anchor["store_id"])] = anchor'
anchor_map_new = 'products_map[(anchor["provider"], anchor["product_id"], anchor["store_id"])] = anchor'
content = content.replace(anchor_map_old, anchor_map_new)

# Wait, `for p_key, p in products_map.items():` is fine.

with open("src/dealhunter/historico.py", "w") as f:
    f.write(content)
