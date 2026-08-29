import re

with open("src/dealhunter/web/admin.py", "r") as f:
    content = f.read()

new_endpoints = """
@admin_bp.route('/settings/provider', methods=['POST'])
def settings_provider():
    provider = request.form.get('provider')
    enabled = request.form.get('enabled') == 'true'
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
    membership = request.form.get('membership')
    status = request.form.get('status')
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
    policy = request.form.get('policy')
    cfg = load_config()
    if 'comparison' not in cfg:
        cfg['comparison'] = {}
    cfg['comparison']['inactive_membership_offers'] = policy
    save_config(cfg)
    return redirect(url_for('admin_bp.settings'))
"""

content = content.replace("@admin_bp.route('/settings/update', methods=['POST'])", new_endpoints + "\n\n@admin_bp.route('/settings/update', methods=['POST'])")

with open("src/dealhunter/web/admin.py", "w") as f:
    f.write(content)
