import os
import glob

replacements = {
    "compare_with_anchor(db, 's1', 'p_milk_anc')": "compare_with_anchor(db, 'rappi', 's1', 'p_milk_anc')",
    "compare_with_anchor(db, 's1', 'p_sham_anc')": "compare_with_anchor(db, 'rappi', 's1', 'p_sham_anc')",
    "client.get('/stores/s1')": "client.get('/stores/rappi/s1')",
    "client.get('/stores/non_existent')": "client.get('/stores/rappi/non_existent')",
    "client.get('/restaurants/r1')": "client.get('/restaurants/rappi/r1')",
    "client.get('/restaurants/non_existent')": "client.get('/restaurants/rappi/non_existent')"
}

for filepath in glob.glob("tests/test_*.py"):
    with open(filepath, "r") as f:
        content = f.read()
    
    modified = False
    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            modified = True
            
    if modified:
        with open(filepath, "w") as f:
            f.write(content)
