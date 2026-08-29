import re

with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

# Add get_merged_config
content = content.replace("from dealhunter.query_layer import build_faceted_query", "from dealhunter.query_layer import build_faceted_query\n    from dealhunter.config import get_merged_config")
content = content.replace("q, count_q, params = build_faceted_query(facets)", "q, count_q, params = build_faceted_query(facets, get_merged_config(None))")

content = content.replace("from dealhunter.query_layer import get_facet_counts", "from dealhunter.query_layer import get_facet_counts\n    from dealhunter.config import get_merged_config")
content = content.replace("counts = get_facet_counts(conn, facets)", "counts = get_facet_counts(conn, facets, get_merged_config(None))")

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)
