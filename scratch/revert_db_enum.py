import re
with open("src/dealhunter/db.py", "r") as f:
    content = f.read()

content = content.replace("provider TEXT DEFAULT 'rappi' CHECK (provider IN ('rappi', 'uber_eats')),", "provider TEXT DEFAULT 'rappi',")

with open("src/dealhunter/db.py", "w") as f:
    f.write(content)
