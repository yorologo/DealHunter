import codecs
from bs4 import BeautifulSoup
import json
with open("scratch/soriana.html") as f:
    soup = BeautifulSoup(f, "html.parser")
script = soup.find("script", id="__REACT_QUERY_STATE__")
content = script.string.strip()
decoded = codecs.decode(content, "unicode_escape")
try:
    data = json.loads(decoded)
    for q in data.get("queries", []):
        if q.get("state") and q["state"].get("data"):
            if isinstance(q["state"]["data"], dict):
                print(q.get("queryHash")[:20], list(q["state"]["data"].keys())[:5])
                if "catalogSectionsMap" in q["state"]["data"]:
                    with open("scratch/soriana_catalog.json", "w") as out:
                        json.dump(q["state"]["data"], out)
                    print("Saved catalog!")
except Exception as e:
    print(e)
