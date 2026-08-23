from dealhunter.semantic import classify_membership, CATEGORY, COLLECTION, UNKNOWN

corpus = [
    # (raw_name, p_cat, p_src, EXPECTED)
    ("Bebidas", "Bebidas", "provider", CATEGORY),
    ("Lácteos", "Lácteos", "provider", CATEGORY),
    ("Antidiabéticos Orales", "Antidiabéticos Orales", "provider", CATEGORY),
    ("Ofertas", "Bebidas", "provider", COLLECTION),
    ("Promos", "Snacks", "inferred", COLLECTION),
    ("Descuentos", "Lácteos", "provider", COLLECTION),
    ("Populares", "", "unknown", COLLECTION),
    ("Destacados", "Cuidado Personal", "provider", COLLECTION),
    ("Last Chance", "Vinos", "provider", COLLECTION),
    ("Last Chance Deals", "Vinos", "provider", COLLECTION),
    ("Ofertas Pro", "Farmacia", "provider", COLLECTION),
    # Unknowns
    ("Morita Roll", "Sushi", "provider", UNKNOWN), 
    ("Tory Roll", "Sushi", "inferred", UNKNOWN),
    ("Combos", "Bebidas", "inferred", UNKNOWN),
    ("Solo por hoy", "Vinos", "provider", UNKNOWN), 
    ("Desayunos", "Desayunos", "inferred", UNKNOWN), 
]

stats = {
    "total": len(corpus),
    "expected_CATEGORY": 0,
    "correct_CATEGORY": 0,
    "false_CATEGORY": 0,
    "expected_COLLECTION": 0,
    "correct_COLLECTION": 0,
    "false_COLLECTION": 0,
    "expected_UNKNOWN": 0,
    "correct_UNKNOWN": 0,
    "false_UNKNOWN": 0,
    "conflicts": 0
}

for raw_name, p_cat, p_src, expected in corpus:
    if expected == CATEGORY: stats["expected_CATEGORY"] += 1
    elif expected == COLLECTION: stats["expected_COLLECTION"] += 1
    elif expected == UNKNOWN: stats["expected_UNKNOWN"] += 1

    res, reason = classify_membership(raw_name, p_cat, p_src)
    if reason == "conflicting_evidence": stats["conflicts"] += 1

    if res == CATEGORY:
        if expected == CATEGORY: stats["correct_CATEGORY"] += 1
        else: stats["false_CATEGORY"] += 1
    elif res == COLLECTION:
        if expected == COLLECTION: stats["correct_COLLECTION"] += 1
        else: stats["false_COLLECTION"] += 1
    elif res == UNKNOWN:
        if expected == UNKNOWN: stats["correct_UNKNOWN"] += 1
        else: stats["false_UNKNOWN"] += 1

stats["classified_rate"] = (stats["correct_CATEGORY"] + stats["correct_COLLECTION"]) / stats["total"]
stats["unknown_rate"] = stats["correct_UNKNOWN"] / stats["total"]

for k, v in stats.items():
    print(f"{k}: {v}")
