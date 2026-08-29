with open("src/dealhunter/db.py", "r") as f:
    content = f.read()

v12_old = """
        if version < 12:
            c.execute("ALTER TABLE observations ADD COLUMN has_pro_offer INTEGER DEFAULT NULL")
            c.execute("ALTER TABLE observations ADD COLUMN pro_price REAL")
            c.execute("ALTER TABLE observations ADD COLUMN pro_discount_effective REAL")
"""
v12_new = """
        if version < 12:
            try:
                c.execute("ALTER TABLE observations ADD COLUMN has_pro_offer INTEGER DEFAULT NULL")
                c.execute("ALTER TABLE observations ADD COLUMN pro_price REAL")
                c.execute("ALTER TABLE observations ADD COLUMN pro_discount_effective REAL")
            except sqlite3.OperationalError:
                pass
"""
content = content.replace(v12_old, v12_new)

v13_old = """
        if version < 13:
            c.execute("ALTER TABLE observations ADD COLUMN limit_info TEXT")
"""
v13_new = """
        if version < 13:
            try:
                c.execute("ALTER TABLE observations ADD COLUMN limit_info TEXT")
            except sqlite3.OperationalError:
                pass
"""
content = content.replace(v13_old, v13_new)

v14_old = """
        if version < 14:
            # We already have vertical in stores, but we should make sure query_layer supports it.
            # Schema changes: none strictly required, but we mark v14.
            pass
"""
# That's fine.

with open("src/dealhunter/db.py", "w") as f:
    f.write(content)
