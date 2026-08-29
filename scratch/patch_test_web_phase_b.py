with open("tests/test_web_phase_b.py", "r") as f:
    content = f.read()

content = content.replace("rv = client.get('/products/s1/p1')", "rv = client.get('/products/rappi/s1/p1')")
content = content.replace("rv = client.get('/products/s1/non_existent')", "rv = client.get('/products/rappi/s1/non_existent')")
content = content.replace("rv = client.get('/compare?store_id=s1&product_id=p1')", "rv = client.get('/compare?provider=rappi&store_id=s1&product_id=p1')")
content = content.replace("res = compare_with_anchor(db, 's1', 'p_anc')", "res = compare_with_anchor(db, 'rappi', 's1', 'p_anc')")

with open("tests/test_web_phase_b.py", "w") as f:
    f.write(content)
