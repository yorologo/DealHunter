import json
from bs4 import BeautifulSoup

with open("scratch/soriana.html") as f:
    soup = BeautifulSoup(f, "html.parser")
    
script = soup.find("script", id="__REACT_QUERY_STATE__")
if script:
    try:
        # The content might contain unicode escapes
        content = script.string
        content = content.encode('raw_unicode_escape').decode('unicode_escape')
        data = json.loads(content)
        for q in data.get("queries", []):
            keys = list(q.get("state", {}).get("data", {}).keys())
            print(q.get("queryHash"), "keys:", keys[:5])
    except Exception as e:
        print(e)
else:
    print("Script not found")
