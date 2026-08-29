with open("src/dealhunter/crawler_zone.py", "r") as f:
    content = f.read()

content = content.replace("validate_provider(provider)\n", "validate_provider(provider_id)\n")

with open("src/dealhunter/crawler_zone.py", "w") as f:
    f.write(content)
