with open("src/dealhunter/providers/uber_eats/crawler.py", "r") as f:
    content = f.read()

content = content.replace("validate_provider(provider)", "validate_provider('uber_eats')")

with open("src/dealhunter/providers/uber_eats/crawler.py", "w") as f:
    f.write(content)
