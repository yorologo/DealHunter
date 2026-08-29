import re
with open("src/dealhunter/core.py", "r") as f:
    content = f.read()

if "from dealhunter.providers.registry import validate_provider" not in content:
    content = "from dealhunter.providers.registry import validate_provider\n" + content

# Instead of patching _upsert_product, we should patch the execute calls inside `core.py` that do INSERTs.
# Let's check where they are!

with open("src/dealhunter/core.py", "w") as f:
    f.write(content)
