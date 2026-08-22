from flask import render_template
import os
import secrets
from flask import Flask, session, request, abort, g, current_app
from dealhunter.db import get_default_db_path
from dealhunter.web.routes import register_routes
from dealhunter.web.admin import admin_bp
from dealhunter.termux import acquire_wake_lock, is_termux

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
    @app.errorhandler(400)
    def handle_400(e):
        description = getattr(e, 'description', str(e))
        if "CSRF token missing or invalid" in description:
            return render_template("errors/400_csrf.html"), 400
        return str(e), 400

    app.register_blueprint(admin_bp)

    return app

def run_server(port=8765, debug=False):
    app = create_app()
    
    # Termux background persistence
    if is_termux():
        if acquire_wake_lock():
            print("[*] Termux Wake Lock activo para mantener DealHunter disponible en segundo plano.")
        else:
            print("[!] Could not acquire Termux Wake Lock. App may be paused in background.")
            
    try:
        app.run(host='127.0.0.1', port=port, debug=debug)
    finally:
        if is_termux():
            print("[*] El Termux Wake Lock permanece activo porque es compartido por la aplicación Termux.")
            print("    Usa `termux-wake-unlock` manualmente cuando ya no necesites ningún servicio Termux en segundo plano.")
