import re
with open("src/dealhunter/core.py", "r") as f:
    content = f.read()

# Add import
if "from dealhunter.providers.registry import validate_provider" not in content:
    content = content.replace("from dealhunter.normalization import normalize_product, fingerprint_product", "from dealhunter.normalization import normalize_product, fingerprint_product\nfrom dealhunter.providers.registry import validate_provider")

content = content.replace("def _upsert_product(c, provider, store_id, product_id, item):", "def _upsert_product(c, provider, store_id, product_id, item):\n    validate_provider(provider)")

content = content.replace("def _insert_observation(c, provider, store_id, product_id, item, run_id):", "def _insert_observation(c, provider, store_id, product_id, item, run_id):\n    validate_provider(provider)")

with open("src/dealhunter/core.py", "w") as f:
    f.write(content)
