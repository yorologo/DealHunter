import os
import sqlite3
from dealhunter.db import setup_db
from dealhunter.web.app import create_app

def test_deals_and_best_full_pages(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["RAPPI_DB_PATH"] = str(db_path)
    conn = setup_db(str(db_path))
    conn.close()

    app = create_app()
    with app.test_client() as client:
        res_best = client.get('/best')
        assert res_best.status_code == 200
        html_best = res_best.get_data(as_text=True)
        assert 'Mejores' in html_best
        
        res_deals = client.get('/deals')
        assert res_deals.status_code == 200
        html_deals = res_deals.get_data(as_text=True)
        assert 'href="/deals?tab=' in html_deals
        assert 'href="/best' in html_deals
        
        # Test they are not the same
        assert 'Mejores compras ahora' not in html_deals
        assert 'Mejores compras ahora' in html_best

def test_deals_htmx_partial(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["RAPPI_DB_PATH"] = str(db_path)
    conn = setup_db(str(db_path))
    conn.close()

    app = create_app()
    with app.test_client() as client:
        res_deals_htmx = client.get('/deals?tab=Todo&sort=discount', headers={'HX-Request': 'true'})
        assert res_deals_htmx.status_code == 200
        html = res_deals_htmx.get_data(as_text=True)
        assert '<html' not in html.lower()
        assert '<body' not in html.lower()
        assert 'class="row row-cols' in html or 'Aún no hay productos' in html

