import re
import os

test_files = []
for root, _, files in os.walk("tests"):
    for f in files:
        if f.endswith(".py"):
            test_files.append(os.path.join(root, f))

for filepath in test_files:
    with open(filepath, "r") as f:
        content = f.read()
        
    original = content
    content = re.sub(r'build_faceted_query\(([^,]+)\)', r'build_faceted_query(\1, {})', content)
    content = re.sub(r'get_facet_counts\(([^,]+), ([^\)]+)\)', r'get_facet_counts(\1, \2, {})', content)
    
    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Patched {filepath}")
