import os
import secrets
from flask import Flask, session, request, abort, g, current_app
from dealhunter.db import get_default_db_path
from dealhunter.web.routes import register_routes
from dealhunter.web.admin import admin_bp

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=get_default_db_path(),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    @app.before_request
    def check_csrf():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        g.csrf_token = session['csrf_token']

        # Only check POST for CSRF
        if request.method == 'POST':
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or token != session['csrf_token']:
                abort(400, "CSRF token missing or invalid")

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=session.get('csrf_token'))

    register_routes(app)
    app.register_blueprint(admin_bp)

    return app

def run_server(port=8765, debug=False):
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=debug)
