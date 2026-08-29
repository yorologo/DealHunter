with open("src/dealhunter/db.py", "r") as f:
    content = f.read()

v8_old = """
        if version < 8:
            try:
                c.execute("ALTER TABLE stores ADD COLUMN status TEXT DEFAULT 'UNKNOWN'")
                c.execute("ALTER TABLE stores ADD COLUMN last_seen_at DATETIME")
                c.execute("ALTER TABLE runs ADD COLUMN crawler_mode TEXT")
                c.execute("ALTER TABLE runs ADD COLUMN coverage_complete INTEGER DEFAULT 0")
            except Exception:
                pass
"""
v8_new = """
        if version < 8:
            try:
                c.execute("ALTER TABLE stores ADD COLUMN status TEXT DEFAULT 'UNKNOWN'")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE stores ADD COLUMN last_seen_at DATETIME")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN crawler_mode TEXT")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN coverage_complete INTEGER DEFAULT 0")
            except Exception:
                pass
"""
content = content.replace(v8_old.strip(), v8_new.strip())

v9_old = """
        if version < 9:
            try:
                c.execute("ALTER TABLE runs ADD COLUMN run_metadata TEXT")
                c.execute("ALTER TABLE runs ADD COLUMN source TEXT DEFAULT 'CLI'")
            except Exception:
                pass
"""
v9_new = """
        if version < 9:
            try:
                c.execute("ALTER TABLE runs ADD COLUMN run_metadata TEXT")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN source TEXT DEFAULT 'CLI'")
            except Exception:
                pass
"""
content = content.replace(v9_old.strip(), v9_new.strip())

with open("src/dealhunter/db.py", "w") as f:
    f.write(content)
