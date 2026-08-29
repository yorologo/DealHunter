import re
with open("src/dealhunter/crawler_zone.py", "r") as f:
    content = f.read()

if "from dealhunter.providers.registry import validate_provider" not in content:
    content = "from dealhunter.providers.registry import validate_provider\n" + content

with open("src/dealhunter/crawler_zone.py", "w") as f:
    f.write(content)
