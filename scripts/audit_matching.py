#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from backfill_normalization import backfill
from dealhunter.normalization import compute_match


QUERIES = (
    "coca cola",
    "leche",
    "shampoo",
    "papel",
    "pan",
    "cerveza",
    "queso",
    "detergente",
    "dog chow",
    "paracetamol",
    "cacahuate",
    "cacahuete",
    "huevos",
    "agua",
    "atun",
    "sabritas",
    "bimbo",
    "lala",
    "alpura",
)


def _load_products(cursor, query):
    cursor.execute(
        """
        SELECT p.product_id, p.store_id, p.name, s.name AS store_name,
               p.brand, p.normalized_name, p.quantity, p.unit,
               p.normalized_quantity, p.normalized_unit, p.fingerprint,
               p.pack_count
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        LEFT JOIN observations o
          ON p.product_id = o.product_id AND p.store_id = o.store_id
        WHERE p.name LIKE ? OR p.brand LIKE ? OR o.query_term LIKE ?
        GROUP BY p.store_id, p.product_id
        ORDER BY p.store_id, p.product_id
        LIMIT 200
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    )
    return [dict(row) for row in cursor.fetchall()]


def _pair_record(p1, p2, match_type, confidence):
    return {
        "type": match_type,
        "confidence": confidence,
        "p1_name": p1["name"],
        "p1_store": p1["store_name"],
        "p1_brand": p1["brand"],
        "p1_quantity": p1["normalized_quantity"],
        "p1_unit": p1["normalized_unit"],
        "p1_pack_count": p1["pack_count"],
        "p2_name": p2["name"],
        "p2_store": p2["store_name"],
        "p2_brand": p2["brand"],
        "p2_quantity": p2["normalized_quantity"],
        "p2_unit": p2["normalized_unit"],
        "p2_pack_count": p2["pack_count"],
    }


def collect_sample(db_path, limit=40):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    buckets = {
        "EXACT_MATCH": [],
        "HIGH_CONFIDENCE_MATCH": [],
        "FUZZY_MATCH": [],
    }
    seen_pairs = set()

    for query in QUERIES:
        products = _load_products(cursor, query)
        for index, p1 in enumerate(products):
            for p2 in products[index + 1 :]:
                if p1["store_id"] == p2["store_id"]:
                    continue

                key1 = (p1["store_id"], p1["product_id"])
                key2 = (p2["store_id"], p2["product_id"])
                pair_key = tuple(sorted((key1, key2)))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                match_type, confidence = compute_match(p1, p2)
                if match_type not in buckets or len(buckets[match_type]) >= limit:
                    continue
                buckets[match_type].append(
                    _pair_record(p1, p2, match_type, confidence)
                )

        if all(len(bucket) >= limit for bucket in buckets.values()):
            break

    conn.close()
    return buckets


def run_audit(source_db, output_path, limit=40):
    if not os.path.isfile(source_db):
        raise FileNotFoundError(source_db)

    # Never migrate or backfill the user's source database during an audit.
    with tempfile.TemporaryDirectory(prefix="dealhunter-matching-audit-") as temp_dir:
        audit_db = os.path.join(temp_dir, "audit.db")
        shutil.copy2(source_db, audit_db)
        backfill(audit_db)
        buckets = collect_sample(audit_db, limit=limit)

    result = {
        "methodology": {
            "source": os.path.basename(source_db),
            "queries": list(QUERIES),
            "cross_store_only": True,
            "deduplicated_pairs": True,
            "requested_per_type": limit,
        },
        "counts": {match_type: len(pairs) for match_type, pairs in buckets.items()},
        "samples": buckets,
    }
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, ensure_ascii=False, indent=2)

    for match_type, count in result["counts"].items():
        print(f"{match_type}: {count}")
    print(f"Audit sample: {output_path}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Audit a conservative cross-store matching sample offline."
    )
    parser.add_argument("--db", default="rappi-deals.db")
    parser.add_argument("--output", default="audit_results.json")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()
    run_audit(args.db, args.output, args.limit)


if __name__ == "__main__":
    main()
