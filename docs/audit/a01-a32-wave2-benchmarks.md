# A01–A32 Wave 2 benchmark evidence

Synthetic schema-v17 fixture used for A11/A12: 60 stores (40 restaurants + 20 markets), 40 products/store, 5 trusted observations/product = 2,400 products / 12,000 observations. Same DB was reused before and after the change on the Termux runtime.

| Measurement | Before | After |
|---|---:|---:|
| `get_restaurants_home` SELECT statements (40 restaurants) | 81 | 1 |
| `get_restaurants_home` elapsed | 0.0688 s | 0.0291 s |
| `analyze_history` median | 0.1898 s | 0.1932 s |
| `get_home_deals` median | 0.5385 s | 0.1884 s |
| `get_best_buys` median | 0.2045 s | 0.2055 s |

A11 removes the `1 + 2N` restaurant query pattern with one CTE/aggregate query while retaining `timestamp DESC, id DESC` latest-observation authority. A12 reuses a single `analyze_history` pass for the three Home deal buckets. No index, schema change, cache, materialized table, dependency, or service was added.
