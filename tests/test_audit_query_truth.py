import sqlite3

from dealhunter.historico import analyze_history
from dealhunter.query_layer import build_faceted_cursor_query, build_faceted_query
from dealhunter.web.app import create_app
from dealhunter.web.queries import get_deals, get_restaurant_detail
from tests.helpers.db import insert_observation, insert_product, insert_store


def _catalog_fixture(conn):
    insert_store(conn, 's1', name='Store', type='market', provider='rappi')
    rows = [
        ('z-low', 90, 100, '2026-09-10T00:00:00Z'),
        ('a-high', 50, 100, '2026-09-12T00:00:00Z'),
        ('m-mid', 75, 100, '2026-09-11T00:00:00Z'),
    ]
    for pid, price, original, ts in rows:
        insert_product(conn, pid, 's1', name=pid, provider='rappi')
        insert_observation(
            conn, f'run-{pid}', 's1', pid, price,
            original_price=original, discount_effective=(1-price/original)*100,
            availability='AVAILABLE', timestamp=ts, provider='rappi',
        )
    conn.commit()


def test_catalog_savings_sort_is_real_and_keyset_matches_offset(current_schema_db):
    conn = current_schema_db
    _catalog_fixture(conn)
    filters = {'sort': 'savings', 'desc': True, 'limit': 10, 'offset': 0}
    offset_sql, _, params = build_faceted_query(filters)
    cursor_sql, _, cursor_params, _ = build_faceted_cursor_query(filters)
    offset_ids = [r[0] for r in conn.execute(offset_sql, params).fetchall()]
    cursor_ids = [r[0] for r in conn.execute(cursor_sql, cursor_params).fetchall()]
    assert offset_ids == ['a-high', 'm-mid', 'z-low']
    assert cursor_ids == offset_ids


def test_catalog_recent_sort_uses_observation_timestamp_and_matches_offset(current_schema_db):
    conn = current_schema_db
    _catalog_fixture(conn)
    filters = {'sort': 'recent', 'desc': True, 'limit': 10, 'offset': 0}
    offset_sql, _, params = build_faceted_query(filters)
    cursor_sql, _, cursor_params, _ = build_faceted_cursor_query(filters)
    offset_ids = [r[0] for r in conn.execute(offset_sql, params).fetchall()]
    cursor_ids = [r[0] for r in conn.execute(cursor_sql, cursor_params).fetchall()]
    assert offset_ids == ['a-high', 'm-mid', 'z-low']
    assert cursor_ids == offset_ids


def test_catalog_does_not_advertise_unimplemented_opportunity(current_schema_db_path):
    app = create_app({'DATABASE': current_schema_db_path, 'TESTING': True, 'SECRET_KEY': 'test'})
    client = app.test_client()
    assert client.get('/market?sort=opportunity').status_code == 400
    html = client.get('/market').get_data(as_text=True)
    assert 'value="opportunity"' not in html


def _insert_pi_history(conn, pid, latest_ts, latest_price):
    insert_product(conn, pid, 's1', name=pid, provider='rappi')
    stamps = ['2026-09-01T00:00:00Z', '2026-09-05T00:00:00Z', latest_ts]
    prices = [100, 100, latest_price]
    for idx, (ts, price) in enumerate(zip(stamps, prices)):
        insert_observation(
            conn, f'{pid}-run-{idx}', 's1', pid, price,
            original_price=100, discount_effective=100-price,
            availability='AVAILABLE', timestamp=ts, provider='rappi',
        )


def test_deal_recency_uses_latest_observation_not_wall_clock(current_schema_db_path):
    with sqlite3.connect(current_schema_db_path) as conn:
        insert_store(conn, 's1', name='Store', type='market', provider='rappi')
        _insert_pi_history(conn, 'z-old', '2026-09-10T00:00:00Z', 70)
        _insert_pi_history(conn, 'a-new', '2026-09-15T00:00:00Z', 60)
        conn.commit()

    history = analyze_history(current_schema_db_path, {'status': ['NEW_LOW', 'REAL_DEAL', 'GOOD_PRICE']})
    by_id = {r['product_id']: r for r in history}
    assert by_id['z-old']['latest_observed_at'].isoformat().startswith('2026-09-10')
    assert by_id['a-new']['latest_observed_at'].isoformat().startswith('2026-09-15')

    data = get_deals(current_schema_db_path, {'tab': 'Todo'}, 'recent', 1)
    pi_ids = [item['data']['product_id'] for item in data['items'] if item['type'] == 'pi']
    assert pi_ids[:2] == ['a-new', 'z-old']


def test_restaurant_latest_observation_tie_breaks_by_id(current_schema_db_path):
    with sqlite3.connect(current_schema_db_path) as conn:
        insert_store(conn, 'r1', name='Restaurant', type='restaurant', provider='rappi')
        insert_product(conn, 'dish', 'r1', name='Dish', category='Main', provider='rappi')
        insert_observation(conn, 'r-old', 'r1', 'dish', 10, timestamp='2026-09-15T12:00:00Z', availability='AVAILABLE')
        insert_observation(conn, 'r-new', 'r1', 'dish', 20, timestamp='2026-09-15T12:00:00Z', availability='AVAILABLE')
        conn.commit()

    detail = get_restaurant_detail(current_schema_db_path, 'rappi', 'r1')
    dish = detail['categories']['Main'][0]
    assert dish['price'] == 20
    assert detail['last_obs'] == '2026-09-15T12:00:00Z'
