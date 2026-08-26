from bs4 import BeautifulSoup
import json
with open("scratch/soriana.html") as f:
    soup = BeautifulSoup(f, "html.parser")
text = soup.find("script", id="__REACT_QUERY_STATE__").string.strip()
text = text.replace("\\u0022", '"').replace("\\u003C", "<").replace("\\u003E", ">")
text = text.replace("\\u0027", "'").replace("\\u0026", "&")
try:
    data = json.loads(text)
    for q in data.get("queries", []):
        if q.get("state") and q["state"].get("data"):
            if isinstance(q["state"]["data"], dict):
                print(q.get("queryHash")[:30], list(q["state"]["data"].keys())[:5])
                if "catalogSectionsMap" in q["state"]["data"]:
                    with open("scratch/soriana_catalog.json", "w") as out:
                        json.dump(q["state"]["data"], out)
                    print("Saved catalog!")
except json.JSONDecodeError as e:
    print(f"Error at {e.pos}: {text[e.pos-40:e.pos+40]}")
