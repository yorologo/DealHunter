import re
with open("src/dealhunter/alerts.py", "r") as f:
    content = f.read()

content = content.replace("key = (r[0], r[1])", "key = (r[0], r[1], r[2])")
content = content.replace("avail_history[key].append(r[2])", "avail_history[key].append(r[3])")

# Also fix the fetch loop for get_alerts
get_alerts_loop_old = """
        res = []
        for r in c.fetchall():
            res.append({
                "id": r[0],
                "alert_type": r[1],
                "product_id": r[2],
                "store_id": r[3],
                "provider": r[12],
                "product_name": r[4],
                "store_name": r[5],
                "price": r[6],
                "previous_price": r[7],
                "deal_status": r[8],
                "triggered_at": r[9],
                "reason": r[10],
                "seen": bool(r[11])
            })
"""
get_alerts_loop_new = """
        res = []
        for r in c.fetchall():
            res.append({
                "id": r[0],
                "alert_type": r[1],
                "product_id": r[2],
                "store_id": r[3],
                "product_name": r[4],
                "store_name": r[5],
                "provider": r[6],
                "price": r[7],
                "previous_price": r[8],
                "deal_status": r[9],
                "triggered_at": r[10],
                "reason": r[11],
                "seen": bool(r[12])
            })
"""
# Note: My previous replace put provider in the wrong place or something. Let's just regex replace the whole loop.
import re
res = re.search(r'res = \[\]\n\s*for r in c.fetchall\(\):\n\s*res.append\(\{(.*?)\}\)', content, re.DOTALL)
if res:
    content = content.replace(res.group(0), get_alerts_loop_new.strip())

with open("src/dealhunter/alerts.py", "w") as f:
    f.write(content)
