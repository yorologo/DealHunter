import re
import sqlite3

import pytest

from dealhunter.web.app import create_app
from tests.helpers.db import insert_alert, insert_observation, insert_product, insert_store


@pytest.fixture
def ux_app(current_schema_db_path):
    with sqlite3.connect(current_schema_db_path) as conn:
        conn.execute("INSERT INTO merchants (merchant_id,name,source) VALUES ('m1','Merchant One','reviewed')")
        conn.execute("INSERT INTO merchant_locations (location_id,merchant_id,name,source) VALUES ('l1','m1','North','reviewed'),('l2','m1','South','reviewed')")
        conn.execute("INSERT INTO browse_nodes (browse_node_id,parent_id,level,name) VALUES ('electronics',NULL,'DEPARTMENT','Electrónica'),('keyboards','electronics','CATEGORY','Teclados')")
        conn.execute("INSERT INTO browse_mappings (provider,raw_type,raw_name,raw_path,browse_node_id,source) VALUES ('rappi','corridor','Teclados','[\"Teclados\"]','keyboards','reviewed')")
        for provider, store_id, location_id, name in [
            ('rappi', 'r1', 'l1', 'North Store'),
            ('uber_eats', 'u1', 'l2', 'South Store'),
        ]:
            insert_store(conn, store_id, name=name, type='market', provider=provider)
            conn.execute(
                "UPDATE stores SET merchant_id='m1',location_id=?,commerce_type='SUPERMARKET',catalog_domain='RETAIL' WHERE provider=? AND store_id=?",
                (location_id, provider, store_id),
            )
        for i in range(30):
            product_id = f'item-{i:03d}'
            insert_product(conn, product_id, 'r1', name=f'Keyboard {i:03d}', brand='Logitech', category='Teclados', provider='rappi')
            insert_observation(
                conn, run_id=f'run-r-{i:03d}', store_id='r1', product_id=product_id,
                provider='rappi', price=100-i, original_price=120,
                discount_effective=20, availability='AVAILABLE',
                timestamp=f'2026-09-16T10:{i:02d}:00Z',
            )
        insert_product(conn, 'south-item', 'u1', name='South Keyboard', brand='Razer', category='Teclados', provider='uber_eats')
        insert_observation(
            conn, run_id='run-u1', store_id='u1', product_id='south-item', provider='uber_eats',
            price=90, original_price=120, discount_effective=25,
            availability='AVAILABLE', timestamp='2026-09-16T11:00:00Z',
        )
        conn.execute("INSERT INTO product_memberships (provider,store_id,product_id,raw_type,raw_name,path,source,semantic_type) VALUES ('rappi','r1','item-000','corridor','Teclados','[\"Teclados\"]','provider','CATEGORY')")
        insert_alert(conn, 'item-000', 'r1', 'NEW_LOW', provider='rappi')
        conn.execute("UPDATE alerts SET price=99, previous_price=110, deal_status='NEW_LOW', reason='Nuevo mínimo confirmado', seen=0")
        conn.commit()
    return create_app({'DATABASE': current_schema_db_path, 'TESTING': True, 'SECRET_KEY': 'test-secret'})


@pytest.fixture
def ux_client(ux_app):
    return ux_app.test_client()


def test_visible_information_architecture_uses_product_language(ux_client):
    html = ux_client.get('/').get_data(as_text=True)
    for label in ('Descubrir', 'Explorar', 'Buscar', 'Seguir', 'Sistema'):
        assert label in html
    assert 'Comercios y sucursales' in html


def test_branch_scope_is_single_coherent_control_and_preserves_legacy(ux_client):
    all_html = ux_client.get('/market?branch_scope=ALL&location=l1').get_data(as_text=True)
    assert re.search(r'Keyboard \d{3}', all_html) and 'South Keyboard' in all_html

    include_html = ux_client.get('/market?branch_scope=INCLUDE&location=l1').get_data(as_text=True)
    assert re.search(r'Keyboard \d{3}', include_html) and 'South Keyboard' not in include_html

    exclude_html = ux_client.get('/market?branch_scope=EXCLUDE&location=l1').get_data(as_text=True)
    assert not re.search(r'Keyboard \d{3}', exclude_html) and 'South Keyboard' in exclude_html

    legacy_html = ux_client.get('/market?exclude_location=l2').get_data(as_text=True)
    assert re.search(r'Keyboard \d{3}', legacy_html) and 'South Keyboard' not in legacy_html

    html = ux_client.get('/market?branch_scope=INCLUDE&location=l1').get_data(as_text=True)
    assert 'id="filtersPanel"' in html
    assert 'Filtros (' in html
    assert html.count('<select name="branch_scope"') == 1
    assert 'name="exclude_location"' not in html
    assert ux_client.get('/market?branch_scope=BOGUS').status_code == 400


def test_keyset_load_more_appends_and_page_links_remain_compatible(ux_client):
    first = ux_client.get('/market?branch_scope=INCLUDE&location=l1')
    html1 = first.get_data(as_text=True)
    ids1 = set(re.findall(r'/products/rappi/r1/(item-\d{3})', html1))
    assert len(ids1) == 25
    assert 'Cargar más' in html1
    cursor = re.search(r'name="cursor" value="([^"]+)"', html1).group(1)

    append = ux_client.get(
        f'/market?branch_scope=INCLUDE&location=l1&page=2&cursor={cursor}',
        headers={'HX-Request': 'true'},
    )
    html2 = append.get_data(as_text=True)
    ids2 = set(re.findall(r'/products/rappi/r1/(item-\d{3})', html2))
    assert len(ids2) == 5
    assert not ids1 & ids2
    assert 'id="catalog-items"' not in html2
    assert 'hx-swap-oob="outerHTML"' in html2

    legacy = ux_client.get('/market?branch_scope=INCLUDE&location=l1&page=2', headers={'HX-Request': 'true'})
    assert legacy.status_code == 200
    assert 'id="catalog-items"' in legacy.get_data(as_text=True)


def test_home_is_purchase_focused_not_system_dashboard(ux_client):
    html = ux_client.get('/').get_data(as_text=True)
    assert '¿Qué vale la pena comprar hoy?' in html
    assert 'Observaciones:' not in html
    assert 'Último run:' not in html
    assert 'Explorar' in html


def test_local_search_covers_reviewed_commerce_hierarchy(ux_client):
    for query, expected in [
        ('Merchant', 'COMERCIOS'),
        ('North', 'SUCURSALES'),
        ('Teclados', 'CATEGORÍAS DEALHUNTER'),
        ('Keyboard', 'PRODUCTOS Y PLATILLOS'),
    ]:
        rv = ux_client.get('/search', query_string={'q': query})
        assert rv.status_code == 200
        assert expected in rv.get_data(as_text=True)


def test_alerts_is_real_read_only_view_with_translated_status(ux_client, ux_app):
    with sqlite3.connect(ux_app.config['DATABASE']) as conn:
        before = conn.execute("SELECT id, seen, alert_type, reason FROM alerts ORDER BY id").fetchall()
    rv = ux_client.get('/alerts?type=NEW_LOW')
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert 'Nuevo mínimo' in html
    assert 'Nuevo mínimo confirmado' in html
    assert 'Próximamente' not in html
    with sqlite3.connect(ux_app.config['DATABASE']) as conn:
        after = conn.execute("SELECT id, seen, alert_type, reason FROM alerts ORDER BY id").fetchall()
    assert after == before
    assert ux_client.get('/alerts?type=NOT_REAL').status_code == 400


def test_modern_views_prefer_reviewed_authorities_but_keep_raw_compatibility(ux_client):
    stores = ux_client.get('/stores').get_data(as_text=True)
    assert 'Comercios identificados' in stores
    assert 'Merchant One' in stores
    assert 'Provider listings sin mapping confirmado' in stores

    categories = ux_client.get('/categories').get_data(as_text=True)
    assert 'Taxonomía DealHunter' in categories
    assert 'Compatibilidad: evidencia RAW del proveedor' in categories


def test_presentation_translates_status_without_changing_internal_query_enum(ux_client):
    html = ux_client.get('/deals?tab=NEW_LOW').get_data(as_text=True)
    assert 'Nuevo mínimo' in html
    assert 'href="/deals?tab=NEW_LOW' in html
    assert 'tab=Nuevo+mínimo' not in html and 'tab=Nuevo%20m%C3%ADnimo' not in html
