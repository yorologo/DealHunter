#!/usr/bin/env python3
"""Read-only benchmark for the shadow identity candidate generator."""

import argparse
import gc
import json
import math
import resource
import sqlite3
import time
from collections import defaultdict

from dealhunter.identity.evaluator import generate_candidates
from dealhunter.identity.normalization import extract_signature, is_hard_reject


def _p95(values):
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _load_products_read_only(db_path):
    uri = f"file:{db_path}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            """
            SELECT provider, store_id, product_id, name, brand, quantity, unit,
                   category
            FROM products
            """
        ).fetchall()

    products = defaultdict(list)
    for row in rows:
        products[row[0]].append(
            {
                "provider": row[0],
                "store_id": row[1],
                "product_id": row[2],
                "name": row[3],
                "brand": row[4],
                "category": row[7],
                "signature": extract_signature(row[4], row[3], row[5], row[6]),
            }
        )
    return products


def _instrument(db_path):
    started = time.perf_counter()
    products = _load_products_read_only(db_path)
    providers = list(products)
    if providers != ["rappi", "uber_eats"]:
        raise RuntimeError(f"Expected providers rappi/uber_eats, got {providers}")

    left = products[providers[0]]
    right = products[providers[1]]
    index = defaultdict(list)
    for idx, product in enumerate(right):
        brand = product["signature"]["brand"]
        if brand:
            index[f"brand:{brand}"].append(idx)
        for token in product["signature"]["base_name"].split()[:3]:
            if len(token) > 2:
                index[f"token:{token}"].append(idx)

    generated_counts = []
    screened_counts = []
    processing_ms = []
    generated = 0
    screened = 0
    clusters_over_cap = 0
    dropped_by_cap = 0

    for product in left:
        product_started = time.perf_counter()
        brand = product["signature"]["brand"]
        brand_matches = index.get(f"brand:{brand}", []) if brand else []
        token_matches = set()
        for token in product["signature"]["base_name"].split()[:3]:
            if len(token) > 2:
                token_matches.update(index.get(f"token:{token}", []))

        block = list(brand_matches)
        for idx in token_matches:
            if idx not in block:
                block.append(idx)

        if len(block) > 100:
            clusters_over_cap += 1
            dropped_by_cap += len(block) - 100
            block = block[:100]

        accepted = 0
        for idx in block:
            candidate = right[idx]
            rejected, _ = is_hard_reject(
                product["signature"], candidate["signature"]
            )
            if rejected:
                continue
            left_tokens = set(product["signature"]["base_name"].split())
            right_tokens = set(candidate["signature"]["base_name"].split())
            if not left_tokens or not right_tokens:
                continue
            overlap = len(left_tokens.intersection(right_tokens))
            minimum = min(len(left_tokens), len(right_tokens))
            if minimum and overlap / minimum >= 0.5:
                accepted += 1

        generated += accepted
        screened += len(block)
        generated_counts.append(accepted)
        screened_counts.append(len(block))
        processing_ms.append((time.perf_counter() - product_started) * 1000)

    theoretical = len(left) * len(right)
    elapsed = time.perf_counter() - started
    return {
        "eligible_left": len(left),
        "eligible_right": len(right),
        "theoretical_cross_product": theoretical,
        "screened_after_cap": screened,
        "generated_candidate_pairs": generated,
        "candidate_reduction_percent": (1 - generated / theoretical) * 100,
        "screened_reduction_percent": (1 - screened / theoretical) * 100,
        "generated_per_left_product": {
            "avg": generated / len(left),
            "p95": _p95(generated_counts),
            "max": max(generated_counts, default=0),
        },
        "screened_per_left_product": {
            "avg": screened / len(left),
            "p95": _p95(screened_counts),
            "max": max(screened_counts, default=0),
        },
        "processing_ms_per_left_product": {
            "avg": sum(processing_ms) / len(processing_ms),
            "p95": _p95(processing_ms),
            "max": max(processing_ms, default=0),
        },
        "clusters_over_cap": clusters_over_cap,
        "dropped_by_cap": dropped_by_cap,
        "instrumented_total_time_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", help="Existing schema v16 catalog database")
    args = parser.parse_args()

    actual_started = time.perf_counter()
    actual = generate_candidates(args.db_path)
    actual_elapsed = time.perf_counter() - actual_started
    actual_count = len(actual)
    actual_peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    del actual
    gc.collect()

    result = _instrument(args.db_path)
    if actual_count != result["generated_candidate_pairs"]:
        raise RuntimeError(
            "Instrumented count diverged from production generator: "
            f"{result['generated_candidate_pairs']} != {actual_count}"
        )
    result.update(
        {
            "source": "dealhunter.identity.evaluator.generate_candidates",
            "python_hash_seed": 0,
            "actual_generate_candidates_time_seconds": actual_elapsed,
            "actual_peak_rss_mib": actual_peak_rss_mib,
        }
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
