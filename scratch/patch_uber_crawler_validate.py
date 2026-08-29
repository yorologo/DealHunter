import re
with open("src/dealhunter/providers/uber_eats/crawler.py", "r") as f:
    content = f.read()

# Add import
if "from dealhunter.providers.registry import validate_provider" not in content:
    content = content.replace("from dealhunter.normalization import normalize_product, fingerprint_product", "from dealhunter.normalization import normalize_product, fingerprint_product\nfrom dealhunter.providers.registry import validate_provider")

# Find store insertion
content = content.replace("c.execute('''INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)", "validate_provider(provider)\n                c.execute('''INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)")

content = content.replace("c.execute('''INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)", "validate_provider(provider)\n                        c.execute('''INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)")


with open("src/dealhunter/providers/uber_eats/crawler.py", "w") as f:
    f.write(content)
