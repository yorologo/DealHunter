import sqlite3
import os
from dealhunter.alerts_engine import DealWatcher
from dealhunter.config import get_merged_config

import tempfile
from dealhunter.db import setup_db
fd, path = tempfile.mkstemp()
os.close(fd)

conn = setup_db(path)
c = conn.cursor()

# Insert Rappi s1/p1
c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('rappi', 's1', 'Rappi Store 1', 'market')")
c.execute("INSERT INTO products (provider, store_id, product_id, name, category) VALUES ('rappi', 's1', 'p1', 'Rappi Product 1', 'Cat A')")

# Insert Uber s1/p1
c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('uber_eats', 's1', 'Uber Store 1', 'market')")
c.execute("INSERT INTO products (provider, store_id, product_id, name, category) VALUES ('uber_eats', 's1', 'p1', 'Uber Product 1', 'Cat B')")

# Insert runs
c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run1', '2026-08-01T09:00:00Z')")
c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run2', '2026-08-02T09:00:00Z')")

# Observations Rappi
c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability) VALUES ('run1', 'rappi', 's1', 'p1', 100.0, 100.0, 10, '2026-08-01T10:00:00Z', 'AVAILABLE')")
c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability, discount_effective) VALUES ('run2', 'rappi', 's1', 'p1', 50.0, 100.0, 10, '2026-08-02T10:00:00Z', 'AVAILABLE', 50.0)")

# Observations Uber
c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability) VALUES ('run1', 'uber_eats', 's1', 'p1', 200.0, 200.0, 10, '2026-08-01T11:00:00Z', 'AVAILABLE')")
c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price, original_price, stock, timestamp, availability, discount_effective) VALUES ('run2', 'uber_eats', 's1', 'p1', 150.0, 200.0, 10, '2026-08-02T11:00:00Z', 'AVAILABLE', 25.0)")

conn.commit()
conn.close()

watcher = DealWatcher(path, config=get_merged_config(None), price_drop_threshold=10.0)
events = watcher.process_run("run2")
print("EVENTS:", events)

