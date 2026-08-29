with open("src/dealhunter/alerts.py", "r") as f:
    content = f.read()

loop_old = """
        for r in rows:
            res.append({
                "id": r[0],
                "alert_type": r[1],
                "product_id": r[2],
                "store_id": r[3],
                "provider": r[12],
                "product_name": r[4],
                "store_name": r[5],
                "current_price": r[6],
                "previous_price": r[7],
                "deal_status": r[8],
                "triggered_at": r[9],
                "reason": r[10],
                "seen": bool(r[11])
            })
"""
loop_new = """
        for r in rows:
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

# Let's just use regex to replace everything inside res.append since I don't know exact spacing
import re
res = re.search(r'for r in rows:\n\s*res.append\(\{.*?\}\)', content, re.DOTALL)
if res:
    content = content.replace(res.group(0), loop_new.strip())

with open("src/dealhunter/alerts.py", "w") as f:
    f.write(content)
