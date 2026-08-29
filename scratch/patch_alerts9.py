import re
with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

content = content.replace("grouped.setdefault((ev['store_id'], ev['product_id']), []).append(ev)", "grouped.setdefault((ev.get('provider', 'rappi'), ev['store_id'], ev['product_id']), []).append(ev)")

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
