with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

# Fix state_history query
content = content.replace("SELECT store_id, product_id, state", "SELECT provider, store_id, product_id, state")
content = content.replace("state_history[(r[0], r[1])] = r[2]", "state_history[(r[0], r[1], r[2])] = r[3]")

# Fix loops
content = content.replace("for (store_id, product_id), curr in curr_obs.items():", "for (provider, store_id, product_id), curr in curr_obs.items():")
content = content.replace("prev = prev_obs.get((store_id, product_id))", "prev = prev_obs.get((provider, store_id, product_id))")
content = content.replace("last_event = state_history.get((store_id, product_id))", "last_event = state_history.get((provider, store_id, product_id))")
content = content.replace("for (store_id, product_id), prev in prev_obs.items():", "for (provider, store_id, product_id), prev in prev_obs.items():")
content = content.replace("if (store_id, product_id) not in curr_obs:", "if (provider, store_id, product_id) not in curr_obs:")

# Fix add_event calls where store_id, product_id are used
content = content.replace("add_event('NEW_LOW', store_id, product_id,", "add_event('NEW_LOW', provider, store_id, product_id,")
content = content.replace("add_event('PRICE_DROP', store_id, product_id,", "add_event('PRICE_DROP', provider, store_id, product_id,")
content = content.replace("add_event('REAL_DEAL', store_id, product_id,", "add_event('REAL_DEAL', provider, store_id, product_id,")
content = content.replace("add_event('GOOD_DEAL', store_id, product_id,", "add_event('GOOD_DEAL', provider, store_id, product_id,")
content = content.replace("add_event('TARGET_PRICE', store_id, product_id,", "add_event('TARGET_PRICE', provider, store_id, product_id,")
content = content.replace("add_event('PRO_DEAL_APPEARED', store_id, product_id,", "add_event('PRO_DEAL_APPEARED', provider, store_id, product_id,")
content = content.replace("add_event('BACK_IN_STOCK', store_id, product_id,", "add_event('BACK_IN_STOCK', provider, store_id, product_id,")
content = content.replace("add_event('OUT_OF_STOCK', store_id, product_id,", "add_event('OUT_OF_STOCK', provider, store_id, product_id,")
content = content.replace("add_event('SUSPICIOUS_REFERENCE_PRICE', store_id, product_id,", "add_event('SUSPICIOUS_REFERENCE_PRICE', provider, store_id, product_id,")

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
