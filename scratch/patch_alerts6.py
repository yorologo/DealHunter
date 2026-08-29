import re

with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

content = content.replace("SELECT store_id, product_id, event_type", "SELECT provider, store_id, product_id, event_type")

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
