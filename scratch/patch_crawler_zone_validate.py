import re
with open("src/dealhunter/crawler_zone.py", "r") as f:
    content = f.read()

# Add import
if "from dealhunter.providers.registry import validate_provider" not in content:
    content = content.replace("from dealhunter.checkpoint import Checkpoint", "from dealhunter.checkpoint import Checkpoint\nfrom dealhunter.providers.registry import validate_provider")

# Find store insertion
content = content.replace("c.execute('''INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)", "validate_provider(provider)\n        c.execute('''INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)")

with open("src/dealhunter/crawler_zone.py", "w") as f:
    f.write(content)
