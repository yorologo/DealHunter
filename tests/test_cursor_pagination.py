import re
import sqlite3

from dealhunter.query_layer import build_faceted_cursor_query
from dealhunter.web.app import create_app
from dealhunter.web.params import QueryParamError, encode_cursor, parse_cursor
from tests.helpers.db import insert_observation, insert_product, insert_store


def _cursor_from_row(row):
    return [row[24], row[25], row[26], row[27], row[23], row[1], row[0]]


def test_cursor_roundtrip_and_rejects_malformed():
    values = [1, 1, 42.5, 99.0, "rappi", "store-1", "product-1"]
    token = encode_cursor(values)
    assert parse_cursor(token) == values

    for bad in ("%%%", encode_cursor(values[:-1])):
        try:
            parse_cursor(bad)
        except QueryParamError:
            pass
        else:
            raise AssertionError("malformed cursor must be rejected")


def test_keyset_pages_do_not_overlap_with_sort_ties(current_schema_db):
    conn = current_schema_db
    insert_store(conn, "s1", name="Store", type="market", provider="rappi")
    values = [
        ("p1", 50, 50),
        ("p2", 50, 40),
        ("p3", 40, 60),
        ("p4", 30, 70),
        ("p5", 20, 80),
    ]
    for product_id, discount, price in values:
        insert_product(conn, product_id, "s1", name=product_id, provider="rappi")
        insert_observation(
            conn,
            run_id=f"run-{product_id}",
            store_id="s1",
            product_id=product_id,
            provider="rappi",
            price=price,
            original_price=100,
            discount_effective=discount,
            availability="AVAILABLE",
            timestamp="2026-01-01T00:00:00Z",
        )
    conn.commit()

    filters = {"limit": 3, "sort": "discount", "desc": True}
    query, count_query, query_params, count_params = build_faceted_cursor_query(filters)
    page1 = conn.execute(query, query_params).fetchall()
    assert [row[0] for row in page1] == ["p2", "p1", "p3"]
    assert conn.execute(count_query, count_params).fetchone()[0] == 5

    query2, _, query_params2, _ = build_faceted_cursor_query(
        filters, cursor_values=_cursor_from_row(page1[-1])
    )
    page2 = conn.execute(query2, query_params2).fetchall()
    assert [row[0] for row in page2] == ["p4", "p5"]
    assert not {row[0] for row in page1} & {row[0] for row in page2}


def test_market_web_uses_cursor_after_first_page(current_schema_db_path):
    with sqlite3.connect(current_schema_db_path) as conn:
        insert_store(conn, "market-1", name="Market One", type="market", provider="rappi")
        for i in range(35):
            product_id = f"item-{i:03d}"
            insert_product(conn, product_id, "market-1", name=product_id, provider="rappi")
            insert_observation(
                conn,
                run_id=f"run-{i:03d}",
                store_id="market-1",
                product_id=product_id,
                provider="rappi",
                price=100,
                original_price=100,
                discount_effective=0,
                availability="AVAILABLE",
                timestamp="2026-01-01T00:00:00Z",
            )
        conn.commit()

    app = create_app({"DATABASE": current_schema_db_path, "TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()

    first = client.get("/market")
    assert first.status_code == 200
    html1 = first.get_data(as_text=True)
    links1 = set(re.findall(r'/products/rappi/market-1/(item-\d{3})', html1))
    assert len(links1) == 25
    match = re.search(r'name="cursor" value="([^"]+)"', html1)
    assert match, "first page must expose a next keyset cursor"

    second = client.get(f"/market?page=2&cursor={match.group(1)}")
    assert second.status_code == 200
    html2 = second.get_data(as_text=True)
    links2 = set(re.findall(r'/products/rappi/market-1/(item-\d{3})', html2))
    assert len(links2) == 10
    assert not links1 & links2
    assert links1 | links2 == {f"item-{i:03d}" for i in range(35)}

    assert client.get("/market?cursor=not-a-valid-cursor").status_code == 400
