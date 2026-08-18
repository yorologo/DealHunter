import json, sqlite3, sys
conn = sqlite3.connect('/data/data/com.termux/files/home/rappi-deal-hunter/rappi-deals.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM products')
print(c.fetchone()[0])
