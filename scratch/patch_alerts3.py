with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

content = content.replace("def generate_event_key(self, event_type, store_id, product_id, run_id):", "def generate_event_key(self, event_type, provider, store_id, product_id, run_id):")
content = content.replace('return f"{event_type}_{store_id}_{product_id}_{run_id}"', 'return f"{event_type}_{provider}_{store_id}_{product_id}_{run_id}"')

content = content.replace("def add_event(event_type, store_id, product_id, prev_id, curr_id, channel, before, after, meta):", "def add_event(event_type, provider, store_id, product_id, prev_id, curr_id, channel, before, after, meta):")
content = content.replace("key = self.generate_event_key(event_type, store_id, product_id, run_id)", "key = self.generate_event_key(event_type, provider, store_id, product_id, run_id)")
content = content.replace("'product_id': product_id,", "'product_id': product_id,\n                'provider': provider,")

content = content.replace("add_event('NEW_LOW', s_id, p_id,", "add_event('NEW_LOW', provider, s_id, p_id,")
content = content.replace("add_event('PRICE_DROP', s_id, p_id,", "add_event('PRICE_DROP', provider, s_id, p_id,")
content = content.replace("add_event('REAL_DEAL', s_id, p_id,", "add_event('REAL_DEAL', provider, s_id, p_id,")
content = content.replace("add_event('GOOD_DEAL', s_id, p_id,", "add_event('GOOD_DEAL', provider, s_id, p_id,")
content = content.replace("add_event('TARGET_PRICE', s_id, p_id,", "add_event('TARGET_PRICE', provider, s_id, p_id,")
content = content.replace("add_event('PRO_DEAL_APPEARED', s_id, p_id,", "add_event('PRO_DEAL_APPEARED', provider, s_id, p_id,")
content = content.replace("add_event('BACK_IN_STOCK', s_id, p_id,", "add_event('BACK_IN_STOCK', provider, s_id, p_id,")
content = content.replace("add_event('SUSPICIOUS_REFERENCE_PRICE', s_id, p_id,", "add_event('SUSPICIOUS_REFERENCE_PRICE', provider, s_id, p_id,")

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
