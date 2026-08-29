import re

with open('src/dealhunter/identity/normalization.py', 'r') as f:
    content = f.read()

with open('scratch/patch_package.py', 'r') as f:
    patch = f.read()

# Replace the parse_package function
start = content.find("def parse_package(text, qty_val, unit_val):")
end = content.find("def extract_signature(", start)
content = content[:start] + patch.split("import re\n\n")[1] + content[end:]

with open('src/dealhunter/identity/normalization.py', 'w') as f:
    f.write(content)
