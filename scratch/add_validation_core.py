with open("src/dealhunter/core.py", "r") as f:
    content = f.read()

content = content.replace(
    "c.execute('''INSERT INTO products (provider, product_id, store_id",
    "validate_provider(provider)\n    c.execute('''INSERT INTO products (provider, product_id, store_id"
)

content = content.replace(
    "c.execute('''INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id",
    "validate_provider(provider)\n        c.execute('''INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id"
)

with open("src/dealhunter/core.py", "w") as f:
    f.write(content)
