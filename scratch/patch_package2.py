import re

with open('src/dealhunter/identity/normalization.py', 'r') as f:
    content = f.read()

# Replace [\d\.,]+ with \d+[\d\.,]* in all regexes
content = content.replace(r'([\d\.,]+)', r'(\d+[\d\.,]*)')

with open('src/dealhunter/identity/normalization.py', 'w') as f:
    f.write(content)
