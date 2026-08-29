with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

content = content.replace("def get_store_detail(db_path, store_id):", "def get_store_detail(db_path, provider, store_id):")
content = content.replace("WHERE store_id = ?", "WHERE provider = ? AND store_id = ?")
# wait, there's "WHERE store_id = ?" in get_store_detail for stores and products!
# Let's use regex to replace specific ones in get_store_detail
import re
content = re.sub(r'c.execute\("SELECT name, type FROM stores WHERE store_id = \?", \(store_id,\)\)', r'c.execute("SELECT name, type FROM stores WHERE provider = ? AND store_id = ?", (provider, store_id))', content)
content = re.sub(r'c.execute\("SELECT COUNT\(product_id\) FROM products WHERE store_id = \?", \(store_id,\)\)', r'c.execute("SELECT COUNT(product_id) FROM products WHERE provider = ? AND store_id = ?", (provider, store_id))', content)
content = re.sub(r'c.execute\("SELECT MAX\(timestamp\) FROM observations WHERE provider = \? AND store_id = \?", \(store_id,\)\)', r'c.execute("SELECT MAX(timestamp) FROM observations WHERE provider = ? AND store_id = ?", (provider, store_id))', content)
content = content.replace("(store_id, store_id)", "(provider, store_id, provider, store_id)") # if I did that in previous script?
# In patch_queries3 I replaced: WHERE p.store_id = ? to WHERE p.provider = ? AND p.store_id = ? but didn't update args!
# The args for categories:
content = re.sub(r'c\.execute\(\'\'\'(.*?)WHERE p.provider = \? AND p.store_id = \?(.*?)\'\'\', \(store_id,\)\)', r"c.execute('''\1WHERE p.provider = ? AND p.store_id = ?\2''', (provider, store_id))", content, flags=re.DOTALL)

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)
