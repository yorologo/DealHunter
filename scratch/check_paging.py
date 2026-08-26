import json

d = json.load(open('/data/data/com.termux/files/home/.local/share/DealHunter/research/uber-eats/cdp/getstore_v1_resp.json'))
print("Paging Info:", d.get('data', {}).get('catalogSectionPagingInfo'))
