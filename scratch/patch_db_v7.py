with open("src/dealhunter/db.py", "r") as f:
    content = f.read()

v7_old = """
        if version < 7:
            try:
                c.execute("ALTER TABLE products ADD COLUMN has_toppings INTEGER")
                c.execute("ALTER TABLE products ADD COLUMN category_source TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                pass
"""
v7_new = """
        if version < 7:
            try:
                c.execute("ALTER TABLE products ADD COLUMN has_toppings INTEGER")
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("ALTER TABLE products ADD COLUMN category_source TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                pass
"""
content = content.replace(v7_old.strip(), v7_new.strip())

with open("src/dealhunter/db.py", "w") as f:
    f.write(content)
