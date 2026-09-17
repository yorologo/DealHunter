from flask import render_template
import os
import secrets
from flask import Flask, session, request, abort, g, current_app
from dealhunter.db import get_default_db_path, setup_db
from dealhunter.config import get_config_dir
from dealhunter.metadata import VERSION
from dealhunter.web.routes import register_routes
from dealhunter.web.admin import admin_bp
from dealhunter.termux import acquire_wake_lock, is_termux


def _production_secret_key():
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    config_dir = get_config_dir()
    os.makedirs(config_dir, mode=0o700, exist_ok=True)
    os.chmod(config_dir, 0o700)
    path = os.path.join(config_dir, "flask_secret.key")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(secrets.token_hex(32))
            f.flush()
            os.fsync(f.fileno())
    os.chmod(path, 0o600)
    with open(path, encoding="ascii") as f:
        key = f.read().strip()
    if not key:
        raise RuntimeError("Flask session secret is empty")
    return key


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    configured_test_secret = None
    if test_config is not None and "SECRET_KEY" in test_config:
        configured_test_secret = test_config["SECRET_KEY"]

    app.config.from_mapping(
        SECRET_KEY=configured_test_secret if configured_test_secret is not None else _production_secret_key(),
        DATABASE=get_default_db_path(),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    @app.before_request
    def check_csrf():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)
        g.csrf_token = session["csrf_token"]

        if request.method == "POST":
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or token != session["csrf_token"]:
                abort(400, "CSRF token missing or invalid")

    @app.context_processor
    def inject_template_metadata():
        return {
            "csrf_token": session.get("csrf_token"),
            "dealhunter_version": VERSION,
        }

    register_routes(app)

    @app.errorhandler(400)
    def handle_400(e):
        description = getattr(e, "description", str(e))
        if "CSRF token missing or invalid" in description:
            return render_template("errors/400_csrf.html"), 400
        return str(e), 400

    app.register_blueprint(admin_bp)
    return app


def run_server(port=8765, debug=False):
    # The documented Web command must be safe on a first run. Initialize or
    # migrate the default database before Flask routes start reading from it.
    conn = setup_db(get_default_db_path())
    conn.close()
    app = create_app()

    if is_termux():
        if acquire_wake_lock():
            print("[*] Termux Wake Lock activo para mantener DealHunter disponible en segundo plano.")
        else:
            print("[!] Could not acquire Termux Wake Lock. App may be paused in background.")

    try:
        app.run(host="127.0.0.1", port=port, debug=debug)
    finally:
        if is_termux():
            print("[*] El Termux Wake Lock permanece activo porque es compartido por la aplicación Termux.")
            print("    Usa `termux-wake-unlock` manualmente cuando ya no necesites ningún servicio Termux en segundo plano.")
