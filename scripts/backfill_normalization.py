import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from dealhunter.db import setup_db
from dealhunter.normalization import generate_fingerprint, parse_product_name


def backfill(db_path):
    conn = setup_db(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT product_id, store_id, name, brand
           FROM products
           WHERE normalized_name IS NULL OR pack_count IS NULL"""
    )
    rows = c.fetchall()

    count = 0
    for r in rows:
        pid, sid, name, brand = r
        norm = parse_product_name(name, brand)
        fp = generate_fingerprint(
            norm["brand"], norm["normalized_name"], norm["normalized_quantity"],
            norm["normalized_unit"], norm["pack_count"]
        )

        c.execute(
            '''
            UPDATE products SET
                brand = ?,
                normalized_name = ?,
                quantity = ?,
                unit = ?,
                normalized_quantity = ?,
                normalized_unit = ?,
                fingerprint = ?,
                pack_count = ?
            WHERE product_id = ? AND store_id = ?
            ''',
            (
                norm["brand"], norm["normalized_name"], norm["quantity"], norm["unit"],
                norm["normalized_quantity"], norm["normalized_unit"], fp,
                norm["pack_count"], pid, sid,
            ),
        )
        count += 1
        if count % 1000 == 0:
            print(f"Backfilled {count}/{len(rows)}")

    conn.commit()
    conn.close()
    print(f"Done backfilling {count} products.")


if __name__ == "__main__":
    backfill(sys.argv[1] if len(sys.argv) > 1 else "rappi-deals.db")
