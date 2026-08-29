with open("src/dealhunter/web/routes.py", "r") as f:
    content = f.read()

content = content.replace('filters = {"store": store_id}', 'filters = {"provider": provider, "store": store_id}')

with open("src/dealhunter/web/routes.py", "w") as f:
    f.write(content)
