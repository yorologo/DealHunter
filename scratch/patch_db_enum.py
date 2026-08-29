import re
with open("src/dealhunter/db.py", "r") as f:
    content = f.read()

# Add CHECK constraints to the initial CREATE TABLE statements (for new DBs)
content = content.replace("provider TEXT DEFAULT 'rappi',", "provider TEXT DEFAULT 'rappi' CHECK (provider IN ('rappi', 'uber_eats')),")

# Also add to the v15 migration CREATE TABLE statements
# We already matched provider TEXT DEFAULT 'rappi', so it should have patched both!
# Wait, let's verify if v15 migration uses provider TEXT DEFAULT 'rappi',

with open("src/dealhunter/db.py", "w") as f:
    f.write(content)
