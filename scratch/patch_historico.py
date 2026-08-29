import re
with open("src/dealhunter/historico.py", "r") as f:
    content = f.read()

content = content.replace("def compare_with_anchor(db_path, store_id, product_id):", "def compare_with_anchor(db_path, provider, store_id, product_id):")
content = content.replace("JOIN stores s ON p.store_id = s.store_id", "JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id")
content = content.replace("WHERE p.product_id = ? AND p.store_id = ?", "WHERE p.provider = ? AND p.store_id = ? AND p.product_id = ?")
content = content.replace("(product_id, store_id)", "(provider, store_id, product_id)")
content = content.replace("AND p.store_id != ?", "AND p.provider = ? AND p.store_id != ?")

# Let's fix the SQL inside compare_with_anchor for fetching candidates
old_candidates_sql = """
    c.execute('''
        SELECT p.provider, p.product_id, p.store_id, p.name, s.name,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               p.fingerprint, p.pack_count
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        WHERE p.product_id != ? AND p.store_id != ?
          AND p.normalized_name = ?
          AND (p.brand = ? OR (p.brand IS NULL AND ? IS NULL))
          AND (p.normalized_quantity = ? OR (p.normalized_quantity IS NULL AND ? IS NULL))
          AND (p.normalized_unit = ? OR (p.normalized_unit IS NULL AND ? IS NULL))
          AND (p.pack_count = ? OR (p.pack_count IS NULL AND ? IS NULL))
    ''', (product_id, store_id, 
          anchor["normalized_name"], 
          anchor["brand"], anchor["brand"],
          anchor["normalized_quantity"], anchor["normalized_quantity"],
          anchor["normalized_unit"], anchor["normalized_unit"],
          anchor["pack_count"], anchor["pack_count"]))
"""
new_candidates_sql = """
    c.execute('''
        SELECT p.provider, p.product_id, p.store_id, p.name, s.name,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               p.fingerprint, p.pack_count
        FROM products p
        JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
        WHERE p.provider = ? AND p.product_id != ? AND p.store_id != ?
          AND p.normalized_name = ?
          AND (p.brand = ? OR (p.brand IS NULL AND ? IS NULL))
          AND (p.normalized_quantity = ? OR (p.normalized_quantity IS NULL AND ? IS NULL))
          AND (p.normalized_unit = ? OR (p.normalized_unit IS NULL AND ? IS NULL))
          AND (p.pack_count = ? OR (p.pack_count IS NULL AND ? IS NULL))
    ''', (provider, product_id, store_id, 
          anchor["normalized_name"], 
          anchor["brand"], anchor["brand"],
          anchor["normalized_quantity"], anchor["normalized_quantity"],
          anchor["normalized_unit"], anchor["normalized_unit"],
          anchor["pack_count"], anchor["pack_count"]))
"""

if old_candidates_sql.strip() in content:
    content = content.replace(old_candidates_sql.strip(), new_candidates_sql.strip())
else:
    # Use regex
    content = re.sub(r"SELECT p\.provider.*?\)\)\)", new_candidates_sql.strip(), content, flags=re.DOTALL)


with open("src/dealhunter/historico.py", "w") as f:
    f.write(content)
