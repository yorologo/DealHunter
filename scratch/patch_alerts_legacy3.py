import re
with open("src/dealhunter/alerts.py", "r") as f:
    content = f.read()

content = content.replace("VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)", "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)")

with open("src/dealhunter/alerts.py", "w") as f:
    f.write(content)
