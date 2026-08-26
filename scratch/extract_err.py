from bs4 import BeautifulSoup
import json
with open("scratch/soriana.html") as f:
    soup = BeautifulSoup(f, "html.parser")
text = soup.find("script", id="__REACT_QUERY_STATE__").string.strip()
text = text.replace("\\u0022", '"').replace("\\u003C", "<").replace("\\u003E", ">").replace("\\u0027", "'").replace("\\u0026", "&")
try:
    json.loads(text)
except json.JSONDecodeError as e:
    print(repr(text[e.pos-30:e.pos+30]))
