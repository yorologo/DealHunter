import json
import http.server
import socketserver
import os

with open('research/identity/5f2/review_queue.json') as f:
    queue = json.load(f)

html = """
<!DOCTYPE html>
<html>
<head>
    <title>DealHunter Identity Review</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .pair { border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; border-radius: 4px; }
        .flex { display: flex; gap: 20px; }
        .col { flex: 1; padding: 10px; background: #f9f9f9; }
        .buttons button { margin-right: 10px; padding: 10px; cursor: pointer; }
        .meta { margin-bottom: 10px; font-size: 0.9em; color: #555; }
    </style>
</head>
<body>
    <h1>Identity Review Queue</h1>
"""
for i, item in enumerate(queue):
    p1 = item["p1"]
    p2 = item["p2"]
    html += f"""
    <div class="pair">
        <h3>Pair {i+1}</h3>
        <div class="meta">
            Model Label: <strong>{item["model_label"]}</strong> | Shadow: <strong>{item["shadow_status"]}</strong>
        </div>
        <div class="flex">
            <div class="col">
                <strong>{p1.get("provider", "Unknown Provider")}</strong><br>
                Name: {p1.get("display_name", p1.get("name", ""))} <br>
                Brand: {p1.get("brand", "")} <br>
                Variant: {p1.get("variant", "")} <br>
                Size: {p1.get("quantity", "")} {p1.get("unit", "")}
            </div>
            <div class="col">
                <strong>{p2.get("provider", "Unknown Provider")}</strong><br>
                Name: {p2.get("display_name", p2.get("name", ""))} <br>
                Brand: {p2.get("brand", "")} <br>
                Variant: {p2.get("variant", "")} <br>
                Size: {p2.get("quantity", "")} {p2.get("unit", "")}
            </div>
        </div>
        <div class="buttons" style="margin-top: 15px;">
            <button>[SAME EXACT PRODUCT]</button>
            <button>[SAME FAMILY]</button>
            <button>[SIMILAR]</button>
            <button>[NO MATCH]</button>
            <button>[UNSURE]</button>
        </div>
    </div>
    """
html += "</body></html>"

with open("research/identity/5f2/review.html", "w") as f:
    f.write(html)
print("Saved review.html")
