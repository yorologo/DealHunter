import re
with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

content = content.replace("add_event('DISCOUNT_INCREASED', store_id, product_id,", "add_event('DISCOUNT_INCREASED', provider, store_id, product_id,")
content = content.replace("add_event('NEW_DEAL', store_id, product_id,", "add_event('NEW_DEAL', provider, store_id, product_id,")
content = content.replace("add_event('NXM_APPEARED', store_id, product_id,", "add_event('NXM_APPEARED', provider, store_id, product_id,")
content = content.replace("add_event('PROGRESSIVE_APPEARED', store_id, product_id,", "add_event('PROGRESSIVE_APPEARED', provider, store_id, product_id,")

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
