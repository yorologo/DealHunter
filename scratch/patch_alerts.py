import re

with open("src/dealhunter/alerts_engine.py", "r") as f:
    content = f.read()

# Fix curr_obs dictionary key
content = content.replace("curr_obs[(r[1], r[2])] =", "curr_obs[(r[11], r[1], r[2])] =")

# Let's find where previous observations are fetched
content = content.replace("SELECT id, store_id, product_id, price", "SELECT id, store_id, product_id, price, provider") # Oh wait, what does the prev query look like?

with open("src/dealhunter/alerts_engine.py", "w") as f:
    f.write(content)
