import pytest
from dealhunter.db import setup_db
from dealhunter.web.app import create_app
from flask import session

def test_admin_settings_csrf_protection(tmp_path, monkeypatch):
    config_home = tmp_path / "xdg-config"
    db_path = tmp_path / "csrf.db"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("RAPPI_DB_PATH", str(db_path))
    setup_db(str(db_path)).close()

    app = create_app({
        'DATABASE': str(db_path),
        'TESTING': True,
        'SECRET_KEY': 'test',
    })
    app.config['WTF_CSRF_ENABLED'] = False  # we manage CSRF manually
    
    with app.test_client() as client:
        # 1. GET /admin/settings -> 200
        res = client.get('/admin/settings')
        assert res.status_code == 200
        
        # Extracción del token del contexto/sesión de la cookie no es trivial, 
        # Forzamos setearlo en la session para probar POSTs.
        with client.session_transaction() as sess:
            sess['csrf_token'] = 'fake-token'
        
        # 3. POST provider con CSRF válido funciona
        res_valid = client.post('/admin/settings/provider', data={
            'csrf_token': 'fake-token',
            'provider': 'rappi',
            'enabled': 'true'
        })
        # Should redirect back to /admin/settings
        assert res_valid.status_code in [302, 303, 200]
        
        # 4. POST provider sin CSRF sigue rechazado
        res_invalid = client.post('/admin/settings/provider', data={
            'provider': 'rappi',
            'enabled': 'true'
        })
        assert res_invalid.status_code == 400
        
        # 5. POST membership con CSRF válido funciona
        res_mem_valid = client.post('/admin/settings/membership', data={
            'csrf_token': 'fake-token',
            'membership': 'rappi_pro',
            'status': 'active'
        })
        assert res_mem_valid.status_code in [302, 303, 200]
        
        # POST membership sin CSRF fallará
        res_mem_invalid = client.post('/admin/settings/membership', data={
            'membership': 'rappi_pro',
            'status': 'active'
        })
        assert res_mem_invalid.status_code == 400
        
        # 6. POST comparison idem
        res_comp_valid = client.post('/admin/settings/comparison', data={
            'csrf_token': 'fake-token',
            'policy': 'exclude'
        })
        assert res_comp_valid.status_code in [302, 303, 200]
        
        res_comp_invalid = client.post('/admin/settings/comparison', data={
            'policy': 'exclude'
        })
        assert res_comp_invalid.status_code == 400

    assert (config_home / "dealhunter" / "config.toml").is_file()
