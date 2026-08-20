import sqlite3
from dealhunter.db import get_default_db_path

db_path = get_default_db_path()
print("DB:", db_path)
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT type, COUNT(*) FROM stores GROUP BY type")
for r in c.fetchall():
    print(r)
