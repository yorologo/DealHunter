import os
import glob

replacements = {
    'href="/products/{{ detail.store_id }}/{{ d.product_id }}?context=restaurant"': 'href="/products/{{ detail.provider }}/{{ detail.store_id }}/{{ d.product_id }}?context=restaurant"',
    'href="/products/{{ p.store_id }}/{{ p.product_id }}"': 'href="/products/{{ p.provider }}/{{ p.store_id }}/{{ p.product_id }}"',
    'href="/products/{{ item.store_id }}/{{ item.product_id }}"': 'href="/products/{{ item.provider }}/{{ item.store_id }}/{{ item.product_id }}"',
    'href="/products/{{ deal.store_id }}/{{ deal.product_id }}"': 'href="/products/{{ deal.provider }}/{{ deal.store_id }}/{{ deal.product_id }}"',
    'href="/products/{{ p.store_id }}/{{ p.product_id }}?context=restaurant"': 'href="/products/{{ p.provider }}/{{ p.store_id }}/{{ p.product_id }}?context=restaurant"',
}

for filepath in glob.glob("src/dealhunter/web/templates/**/*.html", recursive=True):
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
