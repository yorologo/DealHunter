"""DealHunter Admin Blueprint — Phase E Administration."""

import os
import sqlite3
from flask import Blueprint, render_template, request, current_app, redirect, url_for, abort
from markupsafe import escape
from dealhunter.doctor import run_doctor
from dealhunter.account import get_account_status, get_account_token
from dealhunter.config import (
    load_config, get_config_path, get_default_config, get_merged_config, save_config,
    parse_strict_bool, validate_membership, validate_membership_status,
    validate_comparison_policy,
)
from dealhunter.providers.registry import validate_provider
from dealhunter.web.security import local_redirect_target
from dealhunter.db import db_status, db_integrity, backup_db, db_vacuum, CURRENT_SCHEMA_VERSION
from dealhunter.web.admin_queries import (
    get_runs_paginated, get_run_detail, get_events,
    get_run_status_summary, get_db_extended_stats
)

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# Settings classification
SAFE_EDITABLE = {
    'min_discount', 'max_discount', 'radius', 'top', 'sort',
    'output_format', 'vertical', 'store', 'exclude_store',
    'query', 'exclude', 'compact', 'dry_run',
    'max_requests', 'max_runtime', 'lat', 'lng',
}

SECRET_FORBIDDEN = {
    'RAPPI_BEARER_TOKEN', 'bearer_token', 'token', 'secret',
    'password', 'cookie', 'session', 'api_key', 'secret_key',
}


@admin_bp.route('/')
def admin_home():
    """Admin home — system overview dashboard."""
    db_path = current_app.config['DATABASE']

    # Gather quick stats
    summary = {}
    try:
        summary = get_run_status_summary(db_path)
    except Exception:
        pass

    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT run_id, crawler_mode, started_at FROM runs WHERE status = 'RUNNING' ORDER BY started_at DESC LIMIT 1")
    active_row = c.fetchone()
    active_run = {'run_id': active_row[0], 'crawler_mode': active_row[1], 'started_at': active_row[2]} if active_row else None
    conn.close()

    stats = {}
    try:
        stats = db_status(db_path)
    except Exception:
        pass

    # Quick doctor (local only, no network)
    health = "UNKNOWN"
    try:
        checks = run_doctor(db_path=db_path, check_network=False)
        has_error = any(s == "ERROR" for _, s, _ in checks)
        health = "ERROR" if has_error else "HEALTHY"
    except Exception:
        pass

    return render_template('admin/home.html',
                           current_path='/admin',
                           summary=summary,
                           stats=stats,
                           health=health)



@admin_bp.route('/account')
def account():
    """Account management and diagnostics."""
    cfg = load_config()
    db_path = current_app.config.get('DATABASE')
    from dealhunter.account import get_account_status
    # Do NOT hit network on load
    status = get_account_status(cfg, check_network=False)

    return render_template('admin/account.html',
                           current_path='/admin/account',
                           **status)

@admin_bp.route('/account/check', methods=['POST'])
def account_check():
    """Explicit account check - hits network."""
    cfg = load_config()
    db_path = current_app.config.get('DATABASE')
    from dealhunter.account import get_account_status
    status = get_account_status(cfg, check_network=True)

    return render_template('admin/account.html',
                           current_path='/admin/account',
                           **status)

@admin_bp.route('/account/delete', methods=['POST'])
def account_delete():
    from dealhunter.secret_store import SessionService
    svc = SessionService()
    svc.invalidate()
    # Redirect to account page
    from flask import redirect
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

    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT run_id, crawler_mode, started_at FROM runs WHERE status = 'RUNNING' ORDER BY started_at DESC LIMIT 1")
    active_row = c.fetchone()
    active_run = {'run_id': active_row[0], 'crawler_mode': active_row[1], 'started_at': active_row[2]} if active_row else None
    conn.close()

    if request.headers.get('HX-Request'):
        return render_template('admin/partials/runs_table.html',
                               runs=runs_data, page=page,
                               total_pages=total_pages, total=total,
                               status_filter=status_filter)
    return render_template('admin/runs.html', active_run=active_run,
                           runs=runs_data, page=page,
                           total_pages=total_pages, total=total,
                           summary=summary, status_filter=status_filter,
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
        lat = cfg.get("lat")
        lng = cfg.get("lng")
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            conn.close()
            return "Ubicación (lat/lng) no configurada. Configúrala en Administración → Configuración.", 400
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            conn.close()
            return "Ubicación fuera de rango válido.", 400

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

        subprocess.Popen(
            [sys.executable, "-m", "dealhunter", "discover", "--vertical", "general", "--run-id", run_id],
            cwd=project_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # 11. HX-REDIRECT FALLBACK
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
    """Run detail view."""
    # Sanitize run_id
    safe_id = str(escape(run_id))
    db_path = current_app.config['DATABASE']
    run = get_run_detail(db_path, safe_id)
    if not run:
        return render_template('admin/run_detail.html',
                               run=None, current_path='/admin/runs'), 404
    return render_template('admin/run_detail.html',
                           run=run, current_path='/admin/runs')


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
    """Settings view with precedence and classification."""
    global_cfg = load_config()
    config_path = get_config_path()
    config_exists = os.path.exists(config_path)

    profiles = list(global_cfg.get('profiles', {}).keys())
    requested_profile = request.args.get('profile')
    selected_profile = requested_profile if requested_profile in profiles else None
    defaults = get_default_config()
    effective_cfg = get_merged_config(None, profile_name=selected_profile)
    profile_cfg = global_cfg.get('profiles', {}).get(selected_profile, {}) if selected_profile else {}

    # Build the editable runtime view from the same merge authority as CLI/runtime.
    settings_list = []
    for key in sorted(SAFE_EDITABLE):
        default_val = defaults.get(key)
        effective = effective_cfg.get(key)
        if key in profile_cfg:
            source = f"profile:{selected_profile}"
        elif key in global_cfg:
            source = "config.toml"
        else:
            source = "default"
        settings_list.append({
            'key': key,
            'value': effective,
            'default': default_val,
            'source': source,
            'classification': "SAFE_EDITABLE",
            'type': ("float" if key in ("lat", "lng") else type(default_val).__name__),
        })

    # Add any extra keys from config that aren't in defaults
    for key in sorted(global_cfg.keys()):
        if key in defaults:
            continue
        if key == 'profiles':
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
                'source': 'config.toml'
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
            })

    return render_template('admin/settings.html',
                           current_path='/admin/settings',
                           settings=settings_list,
                           profiles=profiles,
                           config_path=config_path,
                           config_exists=config_exists,
                           raw_config=global_cfg,
                           effective_config=effective_cfg,
                           selected_profile=selected_profile)



@admin_bp.route('/settings/provider', methods=['POST'])
def settings_provider():
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
    return redirect(url_for('admin_bp.settings'))

@admin_bp.route('/settings/membership', methods=['POST'])
def settings_membership():
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
    return redirect(url_for('admin_bp.settings'))

@admin_bp.route('/settings/comparison', methods=['POST'])
def settings_comparison():
    try:
        policy = validate_comparison_policy(request.form.get('policy'))
    except ValueError as exc:
        abort(400, str(exc))
    cfg = load_config()
    if 'comparison' not in cfg:
        cfg['comparison'] = {}
    cfg['comparison']['inactive_membership_offers'] = policy
    save_config(cfg)
    return redirect(url_for('admin_bp.settings'))


@admin_bp.route('/settings/update', methods=['POST'])
def settings_update():
    """Update a safe-editable setting — POST only."""
    key = request.form.get('key', '').strip()
    value = request.form.get('value', '').strip()

    # Validate key is safe-editable
    if key not in SAFE_EDITABLE:
        return render_template('admin/partials/settings_result.html',
                               success=False,
                               message=f"'{key}' no es editable desde la web.")

    # Reject anything that looks like a secret
    lower_key = key.lower()
    if any(s in lower_key for s in ('token', 'secret', 'password', 'cookie', 'bearer')):
        return render_template('admin/partials/settings_result.html',
                               success=False,
                               message="No se permiten secretos en la configuración web.")

    # Parse value to correct type
    default_val = get_default_config().get(key)
    try:
        if key in ("lat", "lng"):
            parsed = float(value)
        elif isinstance(default_val, bool):
            parsed = parse_strict_bool(value)
        elif isinstance(default_val, int):
            parsed = int(value)
        elif isinstance(default_val, float):
            parsed = float(value)
        elif isinstance(default_val, list):
            # Comma-separated list
            parsed = [v.strip() for v in value.split(',') if v.strip()]
        else:
            parsed = value
    except (ValueError, TypeError):
        return render_template('admin/partials/settings_result.html',
                               success=False,
                               message=f"Valor inválido para '{key}'."), 400

    if key == "lat" and not -90 <= parsed <= 90:
        return render_template('admin/partials/settings_result.html', success=False, message="lat debe estar entre -90 y 90.")
    if key == "lng" and not -180 <= parsed <= 180:
        return render_template('admin/partials/settings_result.html', success=False, message="lng debe estar entre -180 y 180.")
    if key in ("min_discount", "max_discount") and not 0 <= parsed <= 100:
        return render_template('admin/partials/settings_result.html', success=False, message=f"{key} debe estar entre 0 y 100.")
    if key in ("radius", "top", "max_requests", "max_runtime") and parsed <= 0:
        return render_template('admin/partials/settings_result.html', success=False, message=f"{key} debe ser mayor que 0.")

    # Use config layer to save
    try:
        cfg = load_config()
        cfg[key] = parsed
        save_config(cfg)
        return render_template('admin/partials/settings_result.html',
                               success=True,
                               message=f"'{key}' actualizado a: {parsed}")
    except Exception as e:
        return render_template('admin/partials/settings_result.html',
                               success=False,
                               message=f"Error al guardar: {e}")


# ──────────────────────────────────
#  Catalog Sync — Session Management
# ──────────────────────────────────



@admin_bp.route('/catalog-sync/wizard')
def catalog_sync_wizard():
    """Wizard to import a Rappi session."""
    from dealhunter.account import get_account_status
    cfg = load_config()
    acc = get_account_status(cfg, check_network=False)

    return render_template('admin/wizard.html',
                           current_path='/admin/catalog-sync',
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
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM stores")
        stores_count = cur.fetchone()[0]

        cur.execute("SELECT started_at, status, coverage_complete FROM runs WHERE crawler_mode='ZONE_INVENTORY' ORDER BY started_at DESC LIMIT 1")
        row = cur.fetchone()
        last_zone_attempt = row[0] if row else None
        last_zone_status = row[1] if row else None
        last_zone_coverage = row[2] if row else 0

        cur.execute("SELECT started_at FROM runs WHERE crawler_mode='ZONE_INVENTORY' AND status='SUCCESS' AND coverage_complete=1 ORDER BY started_at DESC LIMIT 1")
        row2 = cur.fetchone()
        last_zone_complete = row2[0] if row2 else None

        conn.close()
    except Exception:
        stores_count = 0
        last_zone_attempt = None
        last_zone_status = None
        last_zone_complete = None
        last_zone_coverage = 0

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
