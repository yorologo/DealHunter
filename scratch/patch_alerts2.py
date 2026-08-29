with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

# Fix prev observations query and dict
old_prev_sql = """
            SELECT o.id, o.store_id, o.product_id, o.price, o.original_price, o.discount_effective, 
                   o.has_pro_offer, o.pro_price, o.pro_discount_effective, o.promotion_type, o.availability, o.provider
            FROM observations o
            INNER JOIN (
                SELECT store_id, product_id, MAX(timestamp) as max_ts
                FROM observations
                WHERE store_id IN ({store_list_str}) AND run_id != ? AND timestamp < (SELECT started_at FROM runs WHERE run_id = ?)
                GROUP BY store_id, product_id
            ) prev ON o.store_id = prev.store_id AND o.product_id = prev.product_id AND o.timestamp = prev.max_ts
"""
new_prev_sql = """
            SELECT o.id, o.store_id, o.product_id, o.price, o.original_price, o.discount_effective, 
                   o.has_pro_offer, o.pro_price, o.pro_discount_effective, o.promotion_type, o.availability, o.provider
            FROM observations o
            INNER JOIN (
                SELECT provider, store_id, product_id, MAX(timestamp) as max_ts
                FROM observations
                WHERE store_id IN ({store_list_str}) AND run_id != ? AND timestamp < (SELECT started_at FROM runs WHERE run_id = ?)
                GROUP BY provider, store_id, product_id
            ) prev ON o.provider = prev.provider AND o.store_id = prev.store_id AND o.product_id = prev.product_id AND o.timestamp = prev.max_ts
"""
content = content.replace(old_prev_sql, new_prev_sql)

content = content.replace("prev_obs[(r[1], r[2])] =", "prev_obs[(r[11], r[1], r[2])] =")

# Later in the code we probably iterate over curr_obs. Let's fix that.
old_loop = "for (s_id, p_id), curr in curr_obs.items():"
new_loop = "for (provider, s_id, p_id), curr in curr_obs.items():"
content = content.replace(old_loop, new_loop)

old_prev_get = "prev = prev_obs.get((s_id, p_id))"
new_prev_get = "prev = prev_obs.get((provider, s_id, p_id))"
content = content.replace(old_prev_get, new_prev_get)

# Also fix the last_state fetch
old_state_sql = """
            SELECT o.store_id, o.product_id, o.availability, o.timestamp
            FROM observations o
            INNER JOIN (
                SELECT store_id, product_id, MAX(timestamp) as max_ts
                FROM observations
                WHERE store_id IN ({store_list_str}) AND run_id != ?
                GROUP BY store_id, product_id
            ) prev ON o.store_id = prev.store_id AND o.product_id = prev.product_id AND o.timestamp = prev.max_ts
"""
new_state_sql = """
            SELECT o.store_id, o.product_id, o.availability, o.timestamp, o.provider
            FROM observations o
            INNER JOIN (
                SELECT provider, store_id, product_id, MAX(timestamp) as max_ts
                FROM observations
                WHERE store_id IN ({store_list_str}) AND run_id != ?
                GROUP BY provider, store_id, product_id
            ) prev ON o.provider = prev.provider AND o.store_id = prev.store_id AND o.product_id = prev.product_id AND o.timestamp = prev.max_ts
"""
content = content.replace(old_state_sql, new_state_sql)

content = content.replace("last_states[(r[0], r[1])] =", "last_states[(r[4], r[0], r[1])] =")
content = content.replace("last_state = last_states.get((s_id, p_id))", "last_state = last_states.get((provider, s_id, p_id))")


with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
