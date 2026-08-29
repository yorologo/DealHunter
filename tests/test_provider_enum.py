import pytest
import sqlite3
from dealhunter.db import setup_db

def test_provider_enum_validation():
    import tempfile, os
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "enum.db")
    
    conn = setup_db(db)
    c = conn.cursor()
    
    c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('rappi', 's1', 'Valid')")
    c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('uber_eats', 's2', 'Valid')")
    
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('Uber1', 's3', 'Invalid')")
        
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO products (provider, product_id, store_id, name) VALUES ('invalid', 'p1', 's1', 'Inv')")
        
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO observations (provider, store_id, product_id, price) VALUES ('foo', 's1', 'p1', 10)")
        
    conn.commit()
    conn.close()
