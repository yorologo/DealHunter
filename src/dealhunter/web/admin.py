"""DealHunter Admin Blueprint — Phase E Administration."""

import os
import sqlite3
from flask import Blueprint, render_template, request, current_app, redirect, url_for
from markupsafe import escape
from dealhunter.doctor import run_doctor
from dealhunter.account import get_account_status, get_account_token
from dealhunter.config import load_config, get_config_path, get_merged_config, save_config
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
    'max_requests', 'max_runtime',
}

SECRET_FORBIDDEN = {
    'RAPPI_BEARER_TOKEN', 'bearer_token', 'token', 'secret',
    'password', 'cookie', 'session', 'api_key', 'secret_key',
}

# Default config values for reference
DEFAULTS = {
    'min_discount': 0,
    'max_discount': 100,
    'radius': 5.0,
    'top': 50,
    'sort': 'discount',
    'output_format': 'table',
    'vertical': [],
    'store': [],
    'exclude_store': [],
    'query': [],
    'exclude': [],
    'max_requests': 1000,
    'max_runtime': 3600,
    'compact': False,
    'dry_run': False,
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
    db_path = current_app.config.get('DB_PATH')
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
    db_path = current_app.config.get('DB_PATH')
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

    if request.headers.get('HX-Request'):
        return render_template('admin/partials/runs_table.html',
                               runs=runs_data, page=page,
                               total_pages=total_pages, total=total,
                               status_filter=status_filter)
    return render_template('admin/runs.html',
                           runs=runs_data, page=page,
                           total_pages=total_pages, total=total,
                           summary=summary, status_filter=status_filter,
                           current_path='/admin/runs')


@admin_bp.route('/runs/start', methods=['POST'])
def runs_start():
    """Manually start the crawler (discover general)."""
    import subprocess
    import sys
    try:
        db_path = current_app.config['DATABASE']
        project_root = os.path.dirname(os.path.abspath(db_path))
        
        subprocess.run(
            [sys.executable, "-m", "dealhunter", "discover", "--vertical", "general"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as e:
        print(f"Error starting crawler from web: {e}", file=sys.stderr)
        
    page = 1
    per_page = 20
    status_filter = request.args.get('status', None)
    runs_data, total_pages, total = get_runs_paginated(
        db_path, page, per_page, status_filter
    )
    return render_template('admin/partials/runs_table.html',
                           runs=runs_data, page=page,
                           total_pages=total_pages, total=total,
                           status_filter=status_filter)



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

    # Build settings display with source and classification
    settings_list = []

    for key, default_val in sorted(DEFAULTS.items()):
        effective = global_cfg.get(key, default_val)
        source = "config.toml" if key in global_cfg else "default"
        classification = "SAFE_EDITABLE"
        settings_list.append({
            'key': key,
            'value': effective,
            'default': default_val,
            'source': source,
            'classification': classification,
            'type': type(default_val).__name__,
        })

    # Add any extra keys from config that aren't in defaults
    for key in sorted(global_cfg.keys()):
        if key in DEFAULTS:
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

    # Profiles info
    profiles = list(global_cfg.get('profiles', {}).keys())

    return render_template('admin/settings.html',
                           current_path='/admin/settings',
                           settings=settings_list,
                           profiles=profiles,
                           config_path=config_path,
                           config_exists=config_exists)


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
    default_val = DEFAULTS.get(key)
    try:
        if isinstance(default_val, bool):
            parsed = value.lower() in ('true', '1', 'yes', 'on')
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
                               message=f"Valor inválido para '{key}'.")

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
    return_path = request.form.get('return_path', '/admin/account')
    
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
        
    flash("Sesión importada correctamente.", "success")
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
        
    db_path = current_app.config.get('DB_PATH')
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM stores")
        stores_count = cur.fetchone()[0]
        cur.execute("SELECT started_at, status, coverage_complete FROM runs WHERE crawler_mode='ZONE_INVENTORY' ORDER BY started_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            last_zone = row[0]
            last_zone_status = row[1]
            last_zone_coverage = row[2]
        else:
            last_zone = None
            last_zone_status = None
            last_zone_coverage = 0
        conn.close()
    except Exception:
        stores_count = 0
        last_zone = None
        last_zone_status = None
        last_zone_coverage = 0

    return render_template('admin/catalog_sync.html',
                           current_path='/admin/catalog-sync',
                           mode=acc['mode'],
                           session_ready=acc['configured'],
                           stored_at=stored_at_str,
                           encryption_method="Fernet",
                           valid=acc['effective'],
                           warnings=svc.store.check_permissions(),
                           status=acc['status'],
                           stores_count=stores_count,
                           last_zone=last_zone,
                           last_zone_status=last_zone_status,
                           last_zone_coverage=last_zone_coverage)



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
    """Validate the current session against Rappi API."""
    from dealhunter.secret_store import SessionService
    svc = SessionService()
    token = svc.get_token()

    if not token:
        return _session_status_response(
            flash_message="No hay sesión configurada para comprobar.",
            flash_success=False
        )

    # Try a lightweight API call to validate
    try:
        from dealhunter.api import fetch_unified_search
        result = fetch_unified_search("test", 19.4326, -99.1332, auth_token=token)
        if result == "RATE_LIMIT":
            return _session_status_response(
                flash_message="Rate limit alcanzado. Intenta más tarde.",
                flash_success=False
            )
        return _session_status_response(
            flash_message="Sesión válida ✓",
            flash_success=True,
            valid=True
        )
    except Exception as e:
        err = str(e)
        if '401' in err or '403' in err:
            svc.mark_expired()
            return _session_status_response(
                flash_message="La sesión no es válida o ha expirado.",
                flash_success=False
            )
        if '429' in err:
            return _session_status_response(
                flash_message="Rate limit (HTTP 429). Intenta más tarde.",
                flash_success=False
            )
        return _session_status_response(
            flash_message=f"Error de conexión: {err}",
            flash_success=False
        )


@admin_bp.route('/catalog-sync/run', methods=['POST'])
def catalog_sync_run():
    """Trigger a catalog sync run."""
    from dealhunter.secret_store import SessionService
    from dealhunter.config import load_config
    svc = SessionService()
    token = svc.get_token()

    if not token:
        return '<div class="alert alert-danger">No hay sesión configurada.</div>'

    try:
        import asyncio
        from dealhunter.catalog_sync import run_sync
        import sqlite3
        import uuid
        db_path = current_app.config['DATABASE']
        conn = sqlite3.connect(db_path)
        cfg = load_config()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status, report = loop.run_until_complete(
                run_sync(cfg, 19.4326, -99.1332, conn, str(uuid.uuid4()))
            )
        finally:
            loop.close()
            conn.close()

        return f'''<div class="alert alert-success">
            <strong>Sincronización completada</strong><br>
            Estado: {status}<br>
            Comercios procesados: {report.merchants_completed}/{report.merchants_attempted}<br>
            Productos únicos extraídos: {report.items_unique}
        </div>'''

    except Exception as e:
        return f'<div class="alert alert-danger">Error: {escape(str(e))}</div>'


def _session_status_response(flash_message=None, flash_success=True, valid=None):
    """Helper to render session status partial with flash message."""
    from dealhunter.secret_store import SessionService
    import datetime

    svc = SessionService()
    status = svc.get_status()

    stored_at_str = None
    if status.get('stored_at'):
        stored_at_str = datetime.datetime.fromtimestamp(
            status['stored_at']
        ).strftime('%d %b %Y %H:%M')

    if valid is not None:
        status['valid'] = valid

    return render_template('admin/partials/session_status.html',
                           mode=status['mode'],
                           stored_at=stored_at_str,
                           encryption_method=status.get('encryption_method'),
                           valid=status.get('valid'),
                           warnings=status.get('warnings', []),
                           flash_message=flash_message,
                           flash_success=flash_success)
