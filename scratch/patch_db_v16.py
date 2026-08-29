import re

with open('src/dealhunter/db.py', 'r') as f:
    content = f.read()

v16_migration = """
    # v16 migration (Shadow / Disabled by default)
    # Controlled by ENABLE_CANONICALIZATION flag in future
    if version < 16:
        import os
        if os.environ.get("ENABLE_CANONICALIZATION") == "1":
            print("Applying schema v16 (Canonicalization)")
            c.execute('''
            CREATE TABLE IF NOT EXISTS product_families (
                family_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT,
                category TEXT
            )''')
            c.execute('''
            CREATE TABLE IF NOT EXISTS canonical_products (
                canonical_id TEXT PRIMARY KEY,
                family_id TEXT REFERENCES product_families(family_id),
                name TEXT NOT NULL,
                brand TEXT,
                quantity REAL,
                unit TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('''
            CREATE TABLE IF NOT EXISTS product_external_identifiers (
                canonical_id TEXT REFERENCES canonical_products(canonical_id),
                identifier_type TEXT,
                identifier_value TEXT,
                PRIMARY KEY (canonical_id, identifier_type, identifier_value)
            )''')
            c.execute('''
            CREATE TABLE IF NOT EXISTS canonical_product_members (
                canonical_id TEXT REFERENCES canonical_products(canonical_id),
                provider TEXT NOT NULL,
                store_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                match_type TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by TEXT,
                PRIMARY KEY (canonical_id, provider, store_id, product_id)
            )''')
            c.execute('''
            CREATE TABLE IF NOT EXISTS product_identity_decisions (
                decision_id TEXT PRIMARY KEY,
                provider1 TEXT, store_id1 TEXT, product_id1 TEXT,
                provider2 TEXT, store_id2 TEXT, product_id2 TEXT,
                decision TEXT,
                confidence REAL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT
            )''')
            # Do NOT update the CURRENT_SCHEMA_VERSION constant yet, 
            # just update the DB if flag is passed.
            c.execute('UPDATE schema_version SET version = 16')
            version = 16
"""

# Find where version < CURRENT_SCHEMA_VERSION is handled
content = content.replace("if version < CURRENT_SCHEMA_VERSION:", v16_migration + "\n    if version < CURRENT_SCHEMA_VERSION:")

with open('src/dealhunter/db.py', 'w') as f:
    f.write(content)
