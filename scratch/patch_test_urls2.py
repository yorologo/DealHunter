with open("tests/test_queries.py", "r") as f:
    content = f.read()

content = content.replace("get_product_detail(current_schema_db_path, 's1', 'p1')", "get_product_detail(current_schema_db_path, 'rappi', 's1', 'p1')")

with open("tests/test_queries.py", "w") as f:
    f.write(content)

with open("tests/test_web_stores.py", "r") as f:
    content = f.read()

content = content.replace("c.get('/stores/STORE1')", "c.get('/stores/rappi/STORE1')")
content = content.replace("c.get('/stores/STORE2')", "c.get('/stores/rappi/STORE2')")
content = content.replace("c.get('/stores/STORE1?sort=opportunity')", "c.get('/stores/rappi/STORE1?sort=opportunity')")
content = content.replace("c.get('/stores/STORE2?sort=price')", "c.get('/stores/rappi/STORE2?sort=price')")

with open("tests/test_web_stores.py", "w") as f:
    f.write(content)
