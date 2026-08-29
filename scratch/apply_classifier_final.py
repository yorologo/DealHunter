import re
with open('src/dealhunter/identity/evaluator.py', 'r') as f:
    content = f.read()

# Replace the EXACT EVIDENCE GATE in match_products
content = content.replace('if ratio_max == 1.0:', 'if ratio_min >= 0.75 and ratio_max >= 0.75:')

with open('src/dealhunter/identity/evaluator.py', 'w') as f:
    f.write(content)
