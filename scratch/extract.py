import re, json
with open("scratch/soriana.html") as f:
    html = f.read()
for match in re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.DOTALL):
    attrs = match.group(1)
    content = match.group(2).strip()
    if len(content) > 300000 and "mutations" in content:
        print("Attributes:", attrs)
        # Content is a JS string representation or directly JSON?
        # Let's just decode the unicode escapes
        decoded = content.encode().decode('unicode_escape')
        with open("scratch/soriana_query.json", "w") as out:
            out.write(decoded)
