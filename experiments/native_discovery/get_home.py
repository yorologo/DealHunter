import urllib.request, re, json

url = "https://www.rappi.com.mx/restaurantes?csr=false"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode('utf-8')
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
if m:
    with open("experiments/native_discovery/restaurantes_next.json", "w") as f:
        f.write(m.group(1))
    print("Saved restaurantes_next.json")
else:
    print("Not found")
