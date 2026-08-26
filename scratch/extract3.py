from bs4 import BeautifulSoup
import json
with open("scratch/soriana.html") as f:
    soup = BeautifulSoup(f, "html.parser")
script = soup.find("script", id="__REACT_QUERY_STATE__")
content = script.string.strip()
content = content.replace("\\u0022", '"').replace("\\u003C", "<").replace("\\u003E", ">")
content = content.replace("\\u0027", "'").replace("\\u0026", "&")
try:
    data = json.loads(content)
    for q in data.get("queries", []):
        if q.get("state") and q["state"].get("data"):
            if isinstance(q["state"]["data"], dict):
                print(q.get("queryHash"), list(q["state"]["data"].keys())[:5])
            else:
                print(q.get("queryHash"), type(q["state"]["data"]))
except Exception as e:
    print(e)
