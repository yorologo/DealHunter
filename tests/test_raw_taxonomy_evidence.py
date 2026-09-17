from dealhunter.core import persist_raw_memberships
from tests.helpers.db import insert_product, insert_store


def test_raw_memberships_preserve_provider_source_and_missing_evidence(current_schema_db):
    insert_store(current_schema_db, "s1", provider="rappi")
    insert_product(current_schema_db, "p1", "s1", name="Product", provider="rappi")
    current_schema_db.commit()

    persist_raw_memberships(
        current_schema_db,
        "rappi",
        "s1",
        "p1",
        [{
            "raw_type": "aisle",
            "raw_name": "Bebidas",
            "raw_id": "a1",
            "path": ["Super", "Bebidas"],
            "source": "provider_payload",
        }],
        category="Bebidas",
        category_source="provider_payload",
    )
    current_schema_db.commit()

    row = current_schema_db.execute(
        "SELECT raw_type, raw_name, raw_id, path, source FROM product_memberships "
        "WHERE provider='rappi' AND store_id='s1' AND product_id='p1'"
    ).fetchone()
    assert row == ("aisle", "Bebidas", "a1", '["Super", "Bebidas"]', "provider_payload")

    # Missing taxonomy in a later source is not evidence that the previous
    # provider membership disappeared.
    persist_raw_memberships(current_schema_db, "rappi", "s1", "p1", None)
    assert current_schema_db.execute(
        "SELECT COUNT(*) FROM product_memberships WHERE provider='rappi' AND store_id='s1' AND product_id='p1'"
    ).fetchone()[0] == 1

    # An explicit complete empty list may reconcile the old membership away.
    persist_raw_memberships(current_schema_db, "rappi", "s1", "p1", [])
    current_schema_db.commit()
    assert current_schema_db.execute(
        "SELECT COUNT(*) FROM product_memberships WHERE provider='rappi' AND store_id='s1' AND product_id='p1'"
    ).fetchone()[0] == 0
