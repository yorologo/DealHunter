with open("src/dealhunter/alerts.py", "r") as f:
    content = f.read()

content = content.replace("SELECT store_id, product_id, availability", "SELECT provider, store_id, product_id, availability")
content = content.replace("avail_history.get((store_id, product_id), [])", "avail_history.get((provider, store_id, product_id), [])")
content = content.replace("avail_history.setdefault((r[0], r[1]), []).append(r[2])", "avail_history.setdefault((r[0], r[1], r[2]), []).append(r[3])")

content = content.replace('store_id = m["store_id"]\n            product_id = m["product_id"]\n            product_name = m["product_name"]', 'provider = m["provider"]\n            store_id = m["store_id"]\n            product_id = m["product_id"]\n            product_name = m["product_name"]')

content = content.replace("def _try_add_alert(self, alerts_list, store_id, product_id, alert_type, price, previous_price, status, reason):", "def _try_add_alert(self, alerts_list, provider, store_id, product_id, alert_type, price, previous_price, status, reason):")

# Fix all self._try_add_alert calls
import re
content = re.sub(r'self\._try_add_alert\(\s*new_alerts,\s*store_id,\s*product_id,', r'self._try_add_alert(\n                        new_alerts, provider, store_id, product_id,', content)

# Fix DB operations
content = content.replace("WHERE product_id = ? AND store_id = ? AND alert_type = ?", "WHERE provider = ? AND product_id = ? AND store_id = ? AND alert_type = ?")
content = content.replace('(a["product_id"], a["store_id"], a["alert_type"])', '(a["provider"], a["product_id"], a["store_id"], a["alert_type"])')

content = content.replace("INSERT INTO alerts (product_id, store_id, alert_type, triggered_at, price, previous_price, deal_status, reason, seen)", "INSERT INTO alerts (provider, product_id, store_id, alert_type, triggered_at, price, previous_price, deal_status, reason, seen)")
content = content.replace('(a["product_id"], a["store_id"], a["alert_type"], now, a["price"], a["previous_price"], a["deal_status"], a["reason"])', '(a["provider"], a["product_id"], a["store_id"], a["alert_type"], now, a["price"], a["previous_price"], a["deal_status"], a["reason"])')

content = content.replace('"store_id": store_id,', '"provider": provider,\n            "store_id": store_id,')

# Fix get_alerts JOIN
content = content.replace("JOIN products p ON a.product_id = p.product_id AND a.store_id = p.store_id", "JOIN products p ON a.provider = p.provider AND a.product_id = p.product_id AND a.store_id = p.store_id")
content = content.replace("JOIN stores s ON a.store_id = s.store_id", "JOIN stores s ON a.provider = s.provider AND a.store_id = s.store_id")

content = content.replace("SELECT a.id, a.alert_type, a.product_id, a.store_id, p.name, s.name,", "SELECT a.id, a.alert_type, a.product_id, a.store_id, p.name, s.name, a.provider,")

content = content.replace('"store_id": r[3],', '"store_id": r[3],\n                "provider": r[12],') # Check index! id=0, alert_type=1, product_id=2, store_id=3, name=4, s.name=5, provider=6. Price=7, prev=8, deal=9, trig=10, reas=11, seen=12.
# Let's fix the indexing of get_alerts

with open("src/dealhunter/alerts.py", "w") as f:
    f.write(content)
