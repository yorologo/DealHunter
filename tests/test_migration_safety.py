import pytest
import sqlite3
import os
import tempfile
from dealhunter.db import setup_db, CURRENT_SCHEMA_VERSION

def test_migration_unexpected_error_not_swallowed():
    test_db = os.path.join(tempfile.gettempdir(), "test_migration_safety.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO schema_version (version) VALUES (0)")
    
    # Create observations table with an INCOMPATIBLE type that will crash ADD COLUMN
    # Actually, ADD COLUMN to a view crashes!
    c.execute("CREATE TABLE stores (store_id TEXT PRIMARY KEY)")
    c.execute("CREATE VIEW observations AS SELECT 1 AS id")
    conn.commit()
    conn.close()

    with pytest.raises(sqlite3.OperationalError):
        setup_db(test_db)

def test_schema_version_global_not_leaked():
    import dealhunter.db as db_module
    assert db_module.CURRENT_SCHEMA_VERSION == 15
