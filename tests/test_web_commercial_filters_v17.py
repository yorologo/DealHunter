import sqlite3

import pytest

from dealhunter.web.app import create_app
from tests.helpers.db import insert_observation, insert_product, insert_store


@pytest.fixture
def commercial_app(current_schema_db_path):
    with sqlite3.connect(current_schema_db_path) as conn:
        conn.execute("INSERT INTO merchants (merchant_id,name,source) VALUES ('m1','Merchant One','reviewed')")
        conn.execute("INSERT INTO merchant_locations (location_id,merchant_id,name,source) VALUES ('l1','m1','North','reviewed'),('l2','m1','South','reviewed')")
        for provider, store_id, location_id, name, brand in [
            ('rappi', 'r1', 'l1', 'North Store', 'Logitech'),
            ('uber_eats', 'u1', 'l2', 'South Store', 'Razer'),
        ]:
            insert_store(conn, store_id, name=name, type='grocery', provider=provider)
            conn.execute(
                "UPDATE stores SET merchant_id='m1',location_id=?,commerce_type='SUPERMARKET',catalog_domain='RETAIL' WHERE provider=? AND store_id=?",
                (location_id, provider, store_id),
            )
            insert_product(conn, f'p-{store_id}', store_id, name=f'{brand} Keyboard', brand=brand, category=None, provider=provider)
            insert_observation(
                conn,
                run_id=f'run-{store_id}',
                store_id=store_id,
                product_id=f'p-{store_id}',
                price=100,
                original_price=120,
                discount_effective=20,
                availability='AVAILABLE',
                provider=provider,
            )
        conn.execute("INSERT INTO product_memberships (provider,store_id,product_id,raw_type,raw_name,path,source,semantic_type) VALUES ('rappi','r1','p-r1','corridor','Teclados','[\"Teclados\"]','provider','CATEGORY')")
        conn.execute("INSERT INTO browse_nodes (browse_node_id,parent_id,level,name) VALUES ('electronics',NULL,'DEPARTMENT','Electrónica'),('keyboards','electronics','CATEGORY','Teclados')")
        conn.execute("INSERT INTO browse_mappings (provider,raw_type,raw_name,raw_path,browse_node_id,source) VALUES ('rappi','corridor','Teclados','[\"Teclados\"]','keyboards','reviewed')")
        conn.commit()
    return create_app({'DATABASE': current_schema_db_path, 'TESTING': True, 'SECRET_KEY': 'test-secret'})


@pytest.fixture
def client(commercial_app):
    return commercial_app.test_client()


def test_commercial_filter_dimensions_reach_catalog(client):
    rv = client.get('/market?merchant=m1&location=l1&commerce_type=SUPERMARKET&catalog_domain=RETAIL&brand=Logitech&browse_node=electronics')
    assert rv.status_code == 200
    assert b'Logitech Keyboard' in rv.data
    assert b'Razer Keyboard' not in rv.data
    assert b'Merchant One' in rv.data
    assert b'North' in rv.data


def test_location_exclusion_is_and_semantic(client):
    rv = client.get('/market?merchant=m1&exclude_location=l2')
    assert rv.status_code == 200
    assert b'Logitech Keyboard' in rv.data
    assert b'Razer Keyboard' not in rv.data


@pytest.mark.parametrize(
    'url',
    [
        '/market?page=abc',
        '/market?page=0',
        '/market?page=-1',
        '/market?sort=DROP_TABLE',
        '/market?min_discount=NaN',
        '/market?min_discount=Infinity',
        '/market?min_discount=-1',
        '/market?min_discount=101',
        '/market?max_price=-1',
        '/market?channel=UNKNOWN',
        '/deals?page=abc',
        '/deals?tab=UNKNOWN',
        '/best?page=-1',
    ],
)
def test_invalid_web_params_return_400_not_500(client, url):
    assert client.get(url).status_code == 400


def test_provider_selector_sets_cookie_and_filters(client):
    with client.session_transaction() as session:
        session['csrf_token'] = 'token'
    rv = client.post(
        '/preferences/provider',
        data={'csrf_token': 'token', 'provider': 'rappi'},
        headers={'Referer': '/market'},
    )
    assert rv.status_code == 302
    assert 'dh_provider=rappi' in rv.headers.get('Set-Cookie', '')

    rv = client.get('/market')
    assert b'Logitech Keyboard' in rv.data
    assert b'Razer Keyboard' not in rv.data


def test_unknown_provider_cookie_fails_closed(client):
    client.set_cookie('dh_provider', 'made_up')
    rv = client.get('/market')
    assert rv.status_code == 200
    assert b'Logitech Keyboard' not in rv.data
    assert b'Razer Keyboard' not in rv.data


def test_unknown_provider_preference_rejected(client):
    with client.session_transaction() as session:
        session['csrf_token'] = 'token'
    rv = client.post('/preferences/provider', data={'csrf_token': 'token', 'provider': 'made_up'})
    assert rv.status_code == 400


def test_categories_separate_browse_from_raw_provider_evidence(client):
    rv = client.get('/categories')
    assert rv.status_code == 200
    assert b'Taxonom' in rv.data
    assert b'Compatibilidad: evidencia RAW del proveedor' in rv.data
    assert b'Teclados' in rv.data
    assert b'Sin clasificar' in rv.data


def test_browse_category_route_uses_reviewed_mapping(client):
    rv = client.get('/categories/browse/electronics')
    assert rv.status_code == 200
    assert b'Logitech Keyboard' in rv.data
    assert b'Razer Keyboard' not in rv.data

    rv = client.get('/categories/browse/UNCLASSIFIED')
    assert rv.status_code == 200
    assert b'Razer Keyboard' in rv.data
    assert b'Logitech Keyboard' not in rv.data

def test_provider_selector_rejects_external_referrer_redirect(client):
    with client.session_transaction() as session:
        session['csrf_token'] = 'token'
    rv = client.post(
        '/preferences/provider',
        data={'csrf_token': 'token', 'provider': 'rappi'},
        headers={'Referer': 'https://evil.example/phish'},
    )
    assert rv.status_code == 302
    assert rv.headers['Location'].endswith('/')
    assert 'evil.example' not in rv.headers['Location']
