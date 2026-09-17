"""DealHunter Admin Blueprint — Phase E Administration."""

import os
import sqlite3
import secrets
import time
from urllib.parse import urlsplit
from flask import (
    Blueprint, render_template, request, current_app, redirect, url_for, abort,
    session, jsonify, flash, make_response,
)
from markupsafe import escape
from dealhunter.doctor import run_doctor
from dealhunter.account import get_account_status, get_account_token
from dealhunter.config import (
    load_config, get_config_path, get_default_config, get_merged_config, save_config,
    parse_strict_bool, validate_membership, validate_membership_status,
    validate_comparison_policy, DISCOVERY_MODES, SORT_OPTIONS, parse_location,
)
from dealhunter.providers.registry import validate_provider
from dealhunter.web.security import local_redirect_target
from dealhunter.db import db_status, db_integrity, backup_db, db_vacuum, CURRENT_SCHEMA_VERSION, read_connection
from dealhunter.web.admin_queries import (
    get_runs_paginated, get_run_detail, get_run_progress, get_events,
    get_run_status_summary, get_db_extended_stats
)

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

RAPPI_MOBILE_AUTH_SESSION_KEY = 'rappi_mobile_auth'
RAPPI_MOBILE_AUTH_TTL_SECONDS = 300
RAPPI_MOBILE_AUTH_MAX_PAYLOAD_BYTES = 64 * 1024


# Settings classification. Location is edited atomically through its own POST.
BASIC_EDITABLE = {'discovery_mode'}
ADVANCED_EDITABLE = {
    'min_discount', 'max_discount', 'sort',
    'vertical', 'store', 'exclude_store', 'query', 'exclude',
    'dry_run', 'max_requests', 'max_runtime',
}
TECHNICAL_READ_ONLY = {'radius', 'top', 'output_format', 'compact'}
SAFE_EDITABLE = BASIC_EDITABLE | ADVANCED_EDITABLE

SECRET_FORBIDDEN = {
    'RAPPI_BEARER_TOKEN', 'bearer_token', 'token', 'secret',
    'password', 'cookie', 'session', 'api_key', 'secret_key',
}


@admin_bp.route('/')
def admin_home():
    """Admin home — system overview dashboard."""
    db_path = current_app.config['DATABASE']

    data_errors = []
    try:
        summary = get_run_status_summary(db_path)
    except Exception as exc:
        summary = None
        data_errors.append(f"Runs: {exc}")

    try:
        from dealhunter.run_lifecycle import find_active_run
        with read_connection(db_path) as conn:
            active_row = find_active_run(conn)
        active_run = {'run_id': active_row[0], 'crawler_mode': active_row[1], 'started_at': active_row[2]} if active_row else None
    except Exception as exc:
        active_run = None
        data_errors.append(f"Active run: {exc}")

    try:
        stats = db_status(db_path)
        if stats.get('error'):
            data_errors.append(f"Database: {stats['error']}")
    except Exception as exc:
        stats = {'error': str(exc)}
        data_errors.append(f"Database: {exc}")

    health = "UNKNOWN"
    try:
        checks = run_doctor(db_path=db_path, check_network=False)
        has_error = any(status == "ERROR" for _, status, _ in checks)
        health = "ERROR" if has_error else "HEALTHY"
    except Exception as exc:
        health = "ERROR"
        data_errors.append(f"Doctor: {exc}")

    return render_template('admin/home.html',
                           current_path='/admin',
                           summary=summary,
                           stats=stats,
                           health=health,
                           data_errors=data_errors)



def _rappi_account_status(check_network=False):
    """Resolve Rappi independently so provider failures stay isolated."""
    try:
        from dealhunter.account import get_account_status as resolve_rappi_status
        return resolve_rappi_status(load_config(), check_network=check_network)
    except Exception:
        current_app.logger.exception("Rappi account status failed")
        return {
            "configured": False,
            "status": "ERROR",
            "source": "ERROR",
            "last_validated_at": None,
            "action_required": None,
            "market": "UNKNOWN",
            "region": "UNKNOWN",
            "has_prime": False,
            "prime_type": "NONE",
            "effective": False,
        }


def _uber_account_status(check_network=False):
    """Resolve Uber through its provider-owned status authority."""
    try:
        from dealhunter.providers.uber_eats.status import get_status as resolve_uber_status
        return resolve_uber_status(
            check_network=check_network,
            db_path=current_app.config.get("DATABASE"),
        )
    except Exception:
        current_app.logger.exception("Uber Eats account status failed")
        return {
            "provider": "Uber Eats",
            "profile": "UNKNOWN",
            "runtime": "RUNTIME_ERROR",
            "session": "UNVERIFIED",
            "last_sync": "Never",
            "last_sync_age_hours": None,
            "data_status": "UNKNOWN",
            "status": "RUNTIME_ERROR",
            "checked_network": bool(check_network),
        }


def _render_account(*, rappi_network=False, uber_network=False, mobile_auth=None):
    return render_template(
        'admin/account.html',
        current_path='/admin/account',
        rappi=_rappi_account_status(check_network=rappi_network),
        uber=_uber_account_status(check_network=uber_network),
        mobile_auth=mobile_auth,
    )


def _rappi_mobile_callback_url():
    """Build a loopback-only callback while preserving the Flask session host."""
    parsed = urlsplit(f'//{request.host}')
    host = parsed.hostname if parsed.hostname in ('127.0.0.1', 'localhost') else '127.0.0.1'
    try:
        port = parsed.port or int(request.environ.get('SERVER_PORT', 8765))
    except (TypeError, ValueError):
        port = 8765
    if not 1 <= port <= 65535:
        port = 8765
    return f'http://{host}:{port}/admin/account/rappi/mobile/import'


def _safe_mobile_import_error(code, http_status=400):
    """Return a fixed error contract that never reflects credential material."""
    return jsonify({'ok': False, 'status': 'ERROR', 'error': code}), http_status


@admin_bp.route('/account')
def account():
    """Local-only status for all account-backed providers."""
    return _render_account()


@admin_bp.route('/account/check', methods=['POST'])
def account_check():
    """Explicit Rappi network validation."""
    return _render_account(rappi_network=True)


@admin_bp.route('/account/uber/check', methods=['POST'])
def account_uber_check():
    """Explicit Uber Eats session validation through provider status authority."""
    return _render_account(uber_network=True)


@admin_bp.route('/account/rappi/mobile/start', methods=['POST'])
def account_rappi_mobile_start():
    """Start an ephemeral mobile Rappi import flow on the existing Flask server."""
    from dealhunter.auth import build_mobile_bookmarklet

    nonce = secrets.token_hex(16)
    expires_at = int(time.time()) + RAPPI_MOBILE_AUTH_TTL_SECONDS
    session[RAPPI_MOBILE_AUTH_SESSION_KEY] = {
        'nonce': nonce,
        'expires_at': expires_at,
    }
    callback_url = _rappi_mobile_callback_url()
    bookmarklet = build_mobile_bookmarklet(callback_url, nonce)
    return _render_account(mobile_auth={
        'bookmarklet': bookmarklet,
        'expires_seconds': RAPPI_MOBILE_AUTH_TTL_SECONDS,
    })


@admin_bp.route('/account/rappi/mobile/import')
def account_rappi_mobile_import():
    """Serve the fragment reader; credential material is never rendered by Jinja."""
    state = session.get(RAPPI_MOBILE_AUTH_SESSION_KEY) or {}
    flow_active = bool(
        state.get('nonce') and
        isinstance(state.get('expires_at'), (int, float)) and
        state['expires_at'] >= time.time()
    )
    response = make_response(render_template(
        'admin/rappi_mobile_import.html',
        flow_active=flow_active,
    ))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@admin_bp.route('/account/rappi/mobile/commit', methods=['POST'])
def account_rappi_mobile_commit():
    """Persist one mobile Rappi credential, then validate through account.py."""
    content_length = request.content_length
    if content_length is not None and content_length > RAPPI_MOBILE_AUTH_MAX_PAYLOAD_BYTES:
        return _safe_mobile_import_error('PAYLOAD_TOO_LARGE', 413)

    state = session.get(RAPPI_MOBILE_AUTH_SESSION_KEY) or {}
    nonce = state.get('nonce')
    expires_at = state.get('expires_at')
    if not nonce or not isinstance(expires_at, (int, float)):
        return _safe_mobile_import_error('FLOW_NOT_STARTED')
    if expires_at < time.time():
        session.pop(RAPPI_MOBILE_AUTH_SESSION_KEY, None)
        return _safe_mobile_import_error('NONCE_EXPIRED')

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _safe_mobile_import_error('MALFORMED_PAYLOAD')
    received_nonce = data.get('nonce')
    if not isinstance(received_nonce, str) or not secrets.compare_digest(nonce, received_nonce):
        return _safe_mobile_import_error('INVALID_NONCE')

    token = data.get('token')
    if not isinstance(token, str):
        return _safe_mobile_import_error('TOKEN_MISSING')
    token = token.strip()
    if token.startswith('Bearer '):
        token = token[7:].strip()
    if (
        not token
        or len(token.encode('utf-8')) > RAPPI_MOBILE_AUTH_MAX_PAYLOAD_BYTES
        or any(ch.isspace() for ch in token)
    ):
        return _safe_mobile_import_error('TOKEN_INVALID')

    try:
        from dealhunter.secret_store import SessionService
        stored = SessionService().store_persistent(token)
        if not stored:
            return _safe_mobile_import_error('SECRET_STORE_ERROR', 500)
    except Exception:
        current_app.logger.error('Rappi mobile session persistence failed')
        return _safe_mobile_import_error('SECRET_STORE_ERROR', 500)

    # Persistence succeeded: consume the nonce before any network validation.
    session.pop(RAPPI_MOBILE_AUTH_SESSION_KEY, None)
    token = None  # noqa: F841 - discard the request-local reference promptly

    try:
        status_result = get_account_status(load_config(), check_network=True)
        status = status_result.get('status', 'ERROR')
    except Exception:
        current_app.logger.error('Rappi mobile post-import validation failed')
        status = 'ERROR'

    if status == 'VALID':
        flash('Sesión Rappi guardada y verificada.', 'success')
    elif status == 'UNVERIFIED':
        flash('Sesión Rappi guardada; la validación remota fue inconclusa y la credencial se conserva.', 'warning')
    elif status == 'EXPIRED':
        flash('La credencial Rappi fue guardada pero el servidor la rechazó como expirada.', 'error')
    else:
        flash('La sesión Rappi fue guardada, pero no pudo validarse de forma segura.', 'error')
        status = 'ERROR'

    return jsonify({'ok': status in ('VALID', 'UNVERIFIED'), 'stored': True, 'status': status})


@admin_bp.route('/account/delete', methods=['POST'])
def account_delete():
    """Invalidate only the Rappi session; Uber profile lifecycle stays isolated."""
    from dealhunter.secret_store import SessionService
    SessionService().delete()
    return redirect('/admin/account')


@admin_bp.route('/runs')
def runs():
    """Paginated run history with filters."""
    page = int(request.args.get('page', 1))
    per_page = 20
    status_filter = request.args.get('status', None)
    db_path = current_app.config['DATABASE']
    runs_data, total_pages, total = get_runs_paginated(
        db_path, page, per_page, status_filter
    )

    summary = {}
    try:
        summary = get_run_status_summary(db_path)
    except Exception:
        pass

    from dealhunter.run_lifecycle import find_active_run
    conn = sqlite3.connect(db_path)
    active_row = find_active_run(conn)
    active_run = {
        'run_id': active_row[0],
        'crawler_mode': active_row[1],
        'started_at': active_row[2],
    } if active_row else None
    conn.close()

    cfg = get_merged_config(None)
    try:
        parse_location(cfg.get("lat"), cfg.get("lng"))
        location_ready = True
    except ValueError:
        location_ready = False

    if request.headers.get('HX-Request'):
        return render_template('admin/partials/runs_table.html',
                               runs=runs_data, page=page,
                               total_pages=total_pages, total=total,
                               status_filter=status_filter)
    return render_template('admin/runs.html', active_run=active_run,
                           runs=runs_data, page=page,
                           total_pages=total_pages, total=total,
                           summary=summary, status_filter=status_filter,
                           location_ready=location_ready,
                           crawler_provider='Rappi',
                           crawler_mode_label='Automático según sesión',
                           current_path='/admin/runs')


@admin_bp.route('/runs/start', methods=['POST'])
def runs_start():
    """Manually start the crawler (discover general)."""
    import subprocess
    import sys
    import uuid
    from dealhunter.config import load_config

    try:
        db_path = current_app.config['DATABASE']
        from pathlib import Path
        project_root = str(Path(__file__).resolve().parents[3])

        conn = sqlite3.connect(db_path, timeout=30)
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        cfg = get_merged_config(None)
        try:
            lat, lng = parse_location(cfg.get("lat"), cfg.get("lng"))
        except ValueError:
            conn.close()
            return "Ubicación (lat/lng) no configurada o inválida. Configúrala en Administración → Configuración.", 400

        from dealhunter.run_lifecycle import ActiveRunError, reserve_run
        try:
            reserve_run(
                conn, run_id, lat=lat, lng=lng, radius=cfg.get("radius", 5.0),
                vertical="general", source="WEB",
            )
        except ActiveRunError:
            conn.close()
            return "Ya hay un crawler activo recientemente.", 400
        conn.close()

        env = os.environ.copy()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = os.path.join(project_root, "src")

        try:
            subprocess.Popen(
                [sys.executable, "-m", "dealhunter", "discover", "--vertical", "general", "--run-id", run_id],
                cwd=project_root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        except Exception:
            from dealhunter.run_lifecycle import update_run_progress
            fail_conn = sqlite3.connect(db_path, timeout=30)
            try:
                update_run_progress(
                    fail_conn, run_id, phase="FAILED", completed=0, total=None
                )
                fail_conn.execute(
                    "UPDATE runs SET status='FAILED', finished_at=CURRENT_TIMESTAMP WHERE run_id=?",
                    (run_id,),
                )
                fail_conn.commit()
            finally:
                fail_conn.close()
            current_app.logger.error("Crawler process launch failed")
            return "No se pudo iniciar el crawler.", 500

        # Preserve compatibility for callers that still send HX-Request.
        if request.headers.get('HX-Request'):
            from flask import make_response
            response = make_response()
            response.headers['HX-Redirect'] = url_for('admin_bp.run_detail', run_id=run_id)
            return response
        else:
            return redirect(url_for('admin_bp.run_detail', run_id=run_id))

    except Exception as e:
        import sys
        print(f"Error starting crawler from web: {e}", file=sys.stderr)
        return "Error interno", 500



@admin_bp.route('/runs/<run_id>')
def run_detail(run_id):
    """Run detail view with persisted progress reconstructed from SQLite."""
    safe_id = str(escape(run_id))
    db_path = current_app.config['DATABASE']
    run = get_run_detail(db_path, safe_id)
    if not run:
        return render_template(
            'admin/run_detail.html',
            run=None,
            progress=None,
            current_path='/admin/runs',
        ), 404
    progress = get_run_progress(db_path, safe_id) if run.get('status') == 'RUNNING' else None
    return render_template(
        'admin/run_detail.html',
        run=run,
        progress=progress,
        current_path='/admin/runs',
    )


@admin_bp.route('/runs/<run_id>/progress')
def run_progress(run_id):
    """Read-only persisted crawler progress; never performs provider I/O."""
    safe_id = str(escape(run_id))
    progress = get_run_progress(current_app.config['DATABASE'], safe_id)
    if not progress:
        return "Run no encontrado.", 404
    if progress['terminal'] or progress['status'] != 'RUNNING':
        response = make_response("")
        response.headers['HX-Refresh'] = 'true'
        return response
    return render_template('admin/partials/run_progress_modal.html', progress=progress)


@admin_bp.route('/events')
def events():
    """Structured events / errors view."""
    page = int(request.args.get('page', 1))
    db_path = current_app.config['DATABASE']
    evts, total_pages, total = get_events(db_path, page)

    if request.headers.get('HX-Request'):
        return render_template('admin/partials/events_table.html',
                               events=evts, page=page,
                               total_pages=total_pages, total=total)
    return render_template('admin/events.html',
                           events=evts, page=page,
                           total_pages=total_pages, total=total,
                           current_path='/admin/events')


@admin_bp.route('/doctor')
def doctor():
    """Doctor — local-only checks on load."""
    db_path = current_app.config['DATABASE']
    # Local checks only — no network on page load
    checks = run_doctor(db_path=db_path, check_network=False)
    has_error = any(s == "ERROR" for _, s, _ in checks)
    overall = "ERROR" if has_error else "HEALTHY"
    return render_template('admin/doctor.html',
                           current_path='/admin/doctor',
                           checks=checks, overall=overall)


@admin_bp.route('/doctor/check', methods=['POST'])
def doctor_check():
    """Doctor with network — explicit opt-in."""
    db_path = current_app.config['DATABASE']
    checks = run_doctor(db_path=db_path, check_network=True)
    has_error = any(s == "ERROR" for _, s, _ in checks)
    overall = "ERROR" if has_error else "HEALTHY"
    return render_template('admin/partials/doctor_results.html',
                           checks=checks, overall=overall)


@admin_bp.route('/database')
def database():
    """Database administration — stats, schema, integrity."""
    db_path = current_app.config['DATABASE']
    stats = get_db_extended_stats(db_path)
    return render_template('admin/database.html',
                           stats=stats,
                           schema_version=CURRENT_SCHEMA_VERSION,
                           current_path='/admin/database')


@admin_bp.route('/database/backup', methods=['POST'])
def database_backup():
    """Create a database backup — POST only."""
    db_path = current_app.config['DATABASE']
    backup_path = backup_db(db_path)
    if backup_path:
        filename = os.path.basename(backup_path)
        return render_template('admin/partials/db_action_result.html',
                               success=True,
                               message=f"Backup creado: {filename}")
    return render_template('admin/partials/db_action_result.html',
                           success=False,
                           message="No se pudo crear el backup. La base de datos no existe.")


@admin_bp.route('/database/integrity', methods=['POST'])
def database_integrity():
    """Run integrity check — POST only."""
    db_path = current_app.config['DATABASE']
    try:
        result = db_integrity(db_path)
        ok = result == "ok"
        return render_template('admin/partials/db_action_result.html',
                               success=ok,
                               message=f"Integridad: {result}")
    except Exception as e:
        return render_template('admin/partials/db_action_result.html',
                               success=False,
                               message=f"Error: {e}")


@admin_bp.route('/settings')
def settings():
    """Task-oriented settings view backed by the canonical config layer."""
    global_cfg = load_config()
    config_path = get_config_path()
    config_exists = os.path.exists(config_path)

    profiles = list(global_cfg.get('profiles', {}).keys())
    requested_profile = request.args.get('profile')
    selected_profile = requested_profile if requested_profile in profiles else None
    defaults = get_default_config()
    effective_cfg = get_merged_config(None, profile_name=selected_profile)
    profile_cfg = global_cfg.get('profiles', {}).get(selected_profile, {}) if selected_profile else {}
    settings_editable = selected_profile is None

    return_to = local_redirect_target(
        request.args.get('return_to'),
        host=request.host,
        default='/admin/settings',
    )

    def setting_source(key):
        if key in profile_cfg:
            return f"profile:{selected_profile}"
        if key in global_cfg:
            return "config.toml"
        return "default"

    try:
        location_lat, location_lng = parse_location(
            effective_cfg.get("lat"), effective_cfg.get("lng")
        )
        location_ready = True
    except ValueError:
        location_lat = location_lng = None
        location_ready = False

    settings_list = []
    for key in sorted(ADVANCED_EDITABLE | TECHNICAL_READ_ONLY):
        default_val = defaults.get(key)
        effective = effective_cfg.get(key)
        editable = settings_editable and key in ADVANCED_EDITABLE
        settings_list.append({
            'key': key,
            'value': effective,
            'default': default_val,
            'source': setting_source(key),
            'classification': "SAFE_EDITABLE" if editable else "READ_ONLY",
            'type': type(default_val).__name__,
            'editable': editable,
            'choices': SORT_OPTIONS if key == 'sort' else None,
            'overridden': key in global_cfg,
        })

    # Extra config keys remain visible for diagnostics but never become editable.
    for key in sorted(global_cfg.keys()):
        if key in defaults or key == 'profiles':
            continue
        lower_key = key.lower()
        if any(s in lower_key for s in ('token', 'secret', 'password', 'cookie', 'key', 'bearer')):
            classification = "SECRET_FORBIDDEN"
        else:
            classification = "READ_ONLY"

        if classification == "SECRET_FORBIDDEN":
            settings_list.append({
                'key': key,
                'configured': bool(global_cfg[key]),
                'editable': False,
                'classification': classification,
                'source': 'config.toml',
                'default': None,
                'type': type(global_cfg[key]).__name__,
                'overridden': True,
            })
        else:
            settings_list.append({
                'key': key,
                'value': global_cfg[key],
                'default': None,
                'source': 'config.toml',
                'classification': classification,
                'type': type(global_cfg[key]).__name__,
                'editable': False,
                'overridden': True,
            })

    return render_template(
        'admin/settings.html',
        current_path='/admin/settings',
        settings=settings_list,
        profiles=profiles,
        config_path=config_path,
        config_exists=config_exists,
        raw_config=global_cfg,
        effective_config=effective_cfg,
        selected_profile=selected_profile,
        settings_editable=settings_editable,
        return_to=return_to,
        location_ready=location_ready,
        location_lat=location_lat,
        location_lng=location_lng,
        location_error=request.args.get('location_error') == '1',
        advanced_open=request.args.get('advanced') == '1',
        discovery_modes=DISCOVERY_MODES,
        discovery_source=setting_source('discovery_mode'),
    )


def _settings_post_scope_guard():
    """Fail closed if a read-only profile view attempts a global write."""
    if request.form.get('profile', '').strip():
        abort(400, "Los profiles son de solo lectura desde la Web.")


def _settings_safe_return(default='/admin/settings'):
    return local_redirect_target(
        request.form.get('return_to'),
        host=request.host,
        default=default,
    )


@admin_bp.route('/settings/location', methods=['POST'])
def settings_location():
    _settings_post_scope_guard()
    try:
        lat, lng = parse_location(
            request.form.get('lat'),
            request.form.get('lng'),
        )
    except ValueError:
        flash("Ubicación inválida. Introduce latitud y longitud válidas juntas.", "danger")
        return redirect('/admin/settings?location_error=1#location')

    try:
        cfg = load_config()
        cfg['lat'] = lat
        cfg['lng'] = lng
        save_config(cfg)
    except Exception:
        current_app.logger.error("Could not persist location configuration")
        flash("No se pudo guardar la ubicación.", "danger")
        return redirect('/admin/settings?location_error=1#location')

    flash("Ubicación guardada.", "success")
    return redirect(_settings_safe_return('/admin/settings#location'))


@admin_bp.route('/settings/provider', methods=['POST'])
def settings_provider():
    _settings_post_scope_guard()
    try:
        provider = validate_provider(request.form.get('provider'))
        enabled = parse_strict_bool(request.form.get('enabled'))
    except ValueError as exc:
        abort(400, str(exc))
    cfg = load_config()
    if 'providers' not in cfg:
        cfg['providers'] = {}
    if provider not in cfg['providers']:
        cfg['providers'][provider] = {}
    cfg['providers'][provider]['enabled'] = enabled
    save_config(cfg)
    flash("Proveedor actualizado.", "success")
    return redirect(_settings_safe_return('/admin/settings'))


@admin_bp.route('/settings/membership', methods=['POST'])
def settings_membership():
    _settings_post_scope_guard()
    try:
        membership = validate_membership(request.form.get('membership'))
        status = validate_membership_status(request.form.get('status'))
    except ValueError as exc:
        abort(400, str(exc))
    cfg = load_config()
    if 'memberships' not in cfg:
        cfg['memberships'] = {}
    if membership not in cfg['memberships']:
        cfg['memberships'][membership] = {}
    cfg['memberships'][membership]['status'] = status
    save_config(cfg)
    flash("Membresía actualizada.", "success")
    return redirect(_settings_safe_return('/admin/settings'))


@admin_bp.route('/settings/comparison', methods=['POST'])
def settings_comparison():
    _settings_post_scope_guard()
    try:
        policy = validate_comparison_policy(request.form.get('policy'))
    except ValueError as exc:
        abort(400, str(exc))
    cfg = load_config()
    if 'comparison' not in cfg:
        cfg['comparison'] = {}
    cfg['comparison']['inactive_membership_offers'] = policy
    save_config(cfg)
    flash("Política de comparación actualizada.", "success")
    return redirect(_settings_safe_return('/admin/settings?advanced=1#advanced-settings'))


def _settings_parse_value(key, value):
    default_val = get_default_config().get(key)
    if key == 'discovery_mode':
        if value not in DISCOVERY_MODES:
            raise ValueError("unsupported discovery mode")
        return value
    if key == 'sort':
        if value not in SORT_OPTIONS:
            raise ValueError("unsupported sort option")
        return value
    if isinstance(default_val, bool):
        return parse_strict_bool(value)
    if isinstance(default_val, int):
        return int(value)
    if isinstance(default_val, float):
        return float(value)
    if isinstance(default_val, list):
        return [v.strip() for v in value.split(',') if v.strip()]
    return value


@admin_bp.route('/settings/update', methods=['POST'])
def settings_update():
    """Update one allowlisted global setting."""
    _settings_post_scope_guard()
    key = request.form.get('key', '').strip()
    value = request.form.get('value', '').strip()

    if key not in SAFE_EDITABLE:
        message = f"'{key}' no es editable desde la web."
        if request.headers.get('HX-Request'):
            return render_template('admin/partials/settings_result.html', success=False, message=message)
        flash(message, "danger")
        return redirect('/admin/settings?advanced=1#advanced-settings')

    lower_key = key.lower()
    if any(s in lower_key for s in ('token', 'secret', 'password', 'cookie', 'bearer')):
        message = "No se permiten secretos en la configuración web."
        if request.headers.get('HX-Request'):
            return render_template('admin/partials/settings_result.html', success=False, message=message)
        flash(message, "danger")
        return redirect('/admin/settings?advanced=1#advanced-settings')

    try:
        parsed = _settings_parse_value(key, value)
        if key in ("min_discount", "max_discount") and not 0 <= parsed <= 100:
            raise ValueError("discount range")
        if key in ("max_requests", "max_runtime") and parsed <= 0:
            raise ValueError("positive value required")
    except (ValueError, TypeError):
        message = f"Valor inválido para '{key}'."
        if request.headers.get('HX-Request'):
            return render_template(
                'admin/partials/settings_result.html',
                success=False,
                message=message,
            ), 400
        flash(message, "danger")
        suffix = '#crawler' if key == 'discovery_mode' else '#advanced-settings'
        query = '' if key == 'discovery_mode' else '?advanced=1'
        return redirect(f"/admin/settings{query}{suffix}")

    try:
        cfg = load_config()
        cfg[key] = parsed
        save_config(cfg)
    except Exception:
        current_app.logger.error("Could not persist Web setting: %s", key)
        message = "No se pudo guardar la configuración."
        if request.headers.get('HX-Request'):
            return render_template('admin/partials/settings_result.html', success=False, message=message), 500
        flash(message, "danger")
        return redirect('/admin/settings?advanced=1#advanced-settings')

    if request.headers.get('HX-Request'):
        return render_template(
            'admin/partials/settings_result.html',
            success=True,
            message=f"'{key}' actualizado.",
        )
    flash("Configuración actualizada.", "success")
    return redirect(_settings_safe_return('/admin/settings'))


@admin_bp.route('/settings/restore', methods=['POST'])
def settings_restore():
    """Remove one advanced global override so normal precedence resolves again."""
    _settings_post_scope_guard()
    key = request.form.get('key', '').strip()
    if key not in ADVANCED_EDITABLE:
        abort(400, "El ajuste no se puede restaurar desde la Web.")
    cfg = load_config()
    if key in cfg:
        del cfg[key]
        save_config(cfg)
    flash("Valor recomendado restaurado.", "success")
    return redirect(_settings_safe_return('/admin/settings?advanced=1#advanced-settings'))


# ──────────────────────────────────
#  Catalog Sync — Session Management
# ──────────────────────────────────



@admin_bp.route('/catalog-sync/wizard')
def catalog_sync_wizard():
    """PC/browser wizard for Rappi; preserve a safe local return target."""
    from dealhunter.account import get_account_status
    cfg = load_config()
    acc = get_account_status(cfg, check_network=False)
    return_path = local_redirect_target(
        request.args.get('return_path', '/admin/catalog-sync'),
        host=request.host, default='/admin/catalog-sync',
    )

    return render_template('admin/wizard.html',
                           current_path=return_path,
                           return_path=return_path,
                           status=acc['status'],
                           mode=acc['mode'])


@admin_bp.route('/catalog-sync/wizard/store', methods=['POST'])
def catalog_sync_wizard_store():
    """Store session from wizard and redirect back."""
    from dealhunter.secret_store import SessionService
    from flask import redirect, request, flash

    token = request.form.get('token', '').strip()
    mode = request.form.get('session_mode', 'persistent')
    return_path = local_redirect_target(
        request.form.get('return_path', '/admin/account'),
        host=request.host, default=None,
    )
    if return_path is None:
        abort(400, "return_path must be an internal or same-origin URL")

    if not token:
        flash("No se proporcionó un token.", "error")
        return redirect('/admin/catalog-sync/wizard')

    svc = SessionService()
    if mode == 'persistent':
        success = svc.store_persistent(token)
        if not success:
            flash("Error al guardar la sesión cifrada.", "error")
            return redirect('/admin/catalog-sync/wizard')
    else:
        svc.store_temporary(token)

    # Guardar y comprobar
    from dealhunter.account import get_account_status
    cfg = load_config()
    status_res = get_account_status(cfg, check_network=True)
    status_str = status_res.get('status', 'UNVERIFIED')

    if status_str == 'VALID':
        flash("Sesión guardada y verificada exitosamente.", "success")
    elif status_str == 'UNVERIFIED':
        flash("Sesión guardada, pero no pudimos verificarla en este momento (WAF/Red).", "warning")
    elif status_str == 'EXPIRED':
        flash("La sesión guardada ya está expirada o es inválida.", "error")

    return redirect(return_path)

@admin_bp.route('/catalog-sync')
def catalog_sync():
    """Catalog Sync dashboard with session status."""
    from dealhunter.secret_store import SessionService
    from dealhunter.account import get_account_status

    svc = SessionService()
    store_meta = svc.store.metadata() if svc.get_mode() == 'SESSION_PERSISTENT' else {}

    cfg = load_config()
    acc = get_account_status(cfg, check_network=False)

    stored_at_str = None
    if store_meta.get('stored_at'):
        import datetime
        stored_at_str = datetime.datetime.fromtimestamp(
            store_meta['stored_at']
        ).strftime('%d %b %Y %H:%M')

    db_path = current_app.config.get('DATABASE')
    db_error = None
    try:
        with read_connection(db_path) as conn:
            stores_count = conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
            row = conn.execute("SELECT started_at, status, coverage_complete FROM runs WHERE crawler_mode='ZONE_INVENTORY' ORDER BY started_at DESC LIMIT 1").fetchone()
            last_zone_attempt = row[0] if row else None
            last_zone_status = row[1] if row else None
            last_zone_coverage = row[2] if row else 0
            row2 = conn.execute("SELECT started_at FROM runs WHERE crawler_mode='ZONE_INVENTORY' AND status='SUCCESS' AND coverage_complete=1 ORDER BY started_at DESC LIMIT 1").fetchone()
            last_zone_complete = row2[0] if row2 else None
    except Exception as exc:
        db_error = str(exc)
        stores_count = None
        last_zone_attempt = None
        last_zone_status = None
        last_zone_complete = None
        last_zone_coverage = None

    from dealhunter.scheduler import is_scheduler_enabled, get_next_run
    scheduler_enabled = is_scheduler_enabled()
    next_run = get_next_run()

    return render_template('admin/catalog_sync.html',
                           current_path='/admin/catalog-sync',
                           mode=acc['mode'],
                           session_ready=acc['configured'],
                           stored_at=stored_at_str,
                           encryption_method="Fernet",
                           valid=(acc['status'] == 'VALID'),
                           warnings=svc.store.check_permissions(),
                           status=acc['status'],
                           stores_count=stores_count,
                           db_error=db_error,
                           last_zone_attempt=last_zone_attempt,
                           last_zone_complete=last_zone_complete,
                           last_zone_status=last_zone_status,
                           last_zone_coverage=last_zone_coverage,
                           scheduler_enabled=scheduler_enabled,
                           next_run=next_run)



def _session_status_response(*, flash_message=None, flash_success=None, valid=None):
    """Render the compatibility session partial without exposing the token."""
    from datetime import datetime
    from dealhunter.secret_store import SessionService

    svc = SessionService()
    status = svc.get_status()
    stored_at_str = None
    if status.get('stored_at'):
        stored_at_str = datetime.fromtimestamp(status['stored_at']).strftime('%d %b %Y %H:%M')
    if valid is not None:
        status['valid'] = valid
    return render_template(
        'admin/partials/session_status.html',
        mode=status['mode'],
        stored_at=stored_at_str,
        encryption_method=status.get('encryption_method'),
        valid=status.get('valid'),
        warnings=status.get('warnings', []),
        flash_message=flash_message,
        flash_success=flash_success,
    )


@admin_bp.route('/catalog-sync/session/store', methods=['POST'])
def session_store():
    """Store or update the Rappi session token."""
    from dealhunter.secret_store import SessionService
    token = request.form.get('token', '').strip()
    mode = request.form.get('session_mode', 'persistent')

    if not token:
        return _session_status_response(
            flash_message="No se proporcionó un token.",
            flash_success=False
        )

    svc = SessionService()

    if mode == 'persistent':
        success = svc.store_persistent(token)
        if not success:
            return _session_status_response(
                flash_message="Error al guardar la sesión cifrada.",
                flash_success=False
            )
    else:
        svc.store_temporary(token)

    # Discard token from memory immediately
    token = None  # noqa: F841

    return _session_status_response(
        flash_message="Sesión configurada correctamente.",
        flash_success=True
    )


@admin_bp.route('/catalog-sync/session/delete', methods=['POST'])
def session_delete():
    """Delete the stored session."""
    from dealhunter.secret_store import SessionService
    svc = SessionService()
    svc.delete()

    # Also clean up legacy session.json if it exists
    import os
    legacy = os.path.expanduser('~/.config/dealhunter/session.json')
    if os.path.exists(legacy):
        try:
            os.remove(legacy)
        except Exception:
            pass

    return _session_status_response(
        flash_message="Sesión eliminada.",
        flash_success=True
    )


@admin_bp.route('/catalog-sync/session/check', methods=['POST'])
def session_check():
    """Validate the current Rappi session through the canonical account resolver."""
    acc = get_account_status(load_config(), check_network=True)
    status = acc.get('status', 'UNVERIFIED')
    if status == 'VALID':
        return _session_status_response(
            flash_message='Sesión válida ✓', flash_success=True, valid=True
        )
    if status == 'EXPIRED':
        return _session_status_response(
            flash_message='La sesión expiró o fue rechazada por autenticación.',
            flash_success=False,
            valid=False,
        )
    if status == 'NOT_CONFIGURED':
        return _session_status_response(
            flash_message='No hay sesión configurada para comprobar.',
            flash_success=False,
            valid=False,
        )
    return _session_status_response(
        flash_message='No fue posible verificar la sesión de forma concluyente; se conserva sin invalidarla.',
        flash_success=False,
        valid=None,
    )


@admin_bp.route('/catalog-sync/scheduler', methods=['POST'])
def catalog_sync_scheduler():
    from flask import request, redirect, flash
    from dealhunter.scheduler import enable_scheduler, disable_scheduler
    
    enabled = request.form.get('enabled') == '1'
    try:
        if enabled:
            enable_scheduler()
            flash("Scheduler activado: Rappi 07:00/10:00/13:00/19:00 y Uber Eats a :30.", "success")
        else:
            disable_scheduler()
            flash("Scheduler desactivado.", "info")
    except RuntimeError as exc:
        flash(str(exc), "warning")

    return redirect('/admin/catalog-sync')
