with open("src/dealhunter/web/templates/admin/settings.html", "r") as f:
    content = f.read()

ui_snippet = """
    <!-- Providers & Memberships Phase 5E -->
    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card shadow-sm h-100">
                <div class="card-header bg-light">
                    <h5 class="mb-0">🔌 Proveedores (Providers)</h5>
                </div>
                <div class="card-body">
                    <p class="text-muted small">Activa o desactiva las integraciones de tiendas. Los datos históricos se conservan si desactivas uno.</p>
                    <ul class="list-group list-group-flush">
                        {% set p_rappi = raw_config.get("providers", {}).get("rappi", {}).get("enabled", True) %}
                        {% set p_uber = raw_config.get("providers", {}).get("uber_eats", {}).get("enabled", False) %}
                        
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <strong>Rappi</strong>
                                <div class="small text-muted">Provider principal</div>
                            </div>
                            <form method="POST" action="/admin/settings/provider">
                                <input type="hidden" name="provider" value="rappi">
                                <input type="hidden" name="enabled" value="{{ 'false' if p_rappi else 'true' }}">
                                <button type="submit" class="btn btn-sm {{ 'btn-success' if p_rappi else 'btn-outline-secondary' }}">
                                    {{ 'ON' if p_rappi else 'OFF' }}
                                </button>
                            </form>
                        </li>
                        
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <strong>Uber Eats</strong>
                                <div class="small text-muted">Integración secundaria</div>
                            </div>
                            <form method="POST" action="/admin/settings/provider">
                                <input type="hidden" name="provider" value="uber_eats">
                                <input type="hidden" name="enabled" value="{{ 'false' if p_uber else 'true' }}">
                                <button type="submit" class="btn btn-sm {{ 'btn-success' if p_uber else 'btn-outline-secondary' }}">
                                    {{ 'ON' if p_uber else 'OFF' }}
                                </button>
                            </form>
                        </li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <div class="card shadow-sm h-100">
                <div class="card-header bg-light">
                    <h5 class="mb-0">💳 Membresías y Políticas</h5>
                </div>
                <div class="card-body">
                    <p class="text-muted small">Configura el estado de tus membresías y qué hacer con ofertas exclusivas a las que no tienes acceso.</p>
                    
                    {% set m_rappi = raw_config.get("memberships", {}).get("rappi_pro", {}).get("status", "unknown") %}
                    {% set m_uber = raw_config.get("memberships", {}).get("uber_one", {}).get("status", "unknown") %}
                    {% set c_policy = raw_config.get("comparison", {}).get("inactive_membership_offers", "show_but_exclude") %}
                    
                    <form method="POST" action="/admin/settings/membership" class="mb-3 d-flex gap-2">
                        <select name="membership" class="form-select form-select-sm" style="width: auto;">
                            <option value="rappi_pro">Rappi Pro</option>
                            <option value="uber_one">Uber One</option>
                        </select>
                        <select name="status" class="form-select form-select-sm" style="width: auto;">
                            <option value="unknown" {% if m_rappi == 'unknown' %}selected{% endif %}>Desconocido (Unknown)</option>
                            <option value="active" {% if m_rappi == 'active' %}selected{% endif %}>Activa (Active)</option>
                            <option value="inactive" {% if m_rappi == 'inactive' %}selected{% endif %}>Inactiva (Inactive)</option>
                        </select>
                        <button type="submit" class="btn btn-sm btn-primary">Guardar</button>
                    </form>

                    <hr>
                    
                    <form method="POST" action="/admin/settings/comparison">
                        <label class="form-label small fw-bold">Política para ofertas de membresías inactivas/desconocidas</label>
                        <div class="d-flex gap-2">
                            <select name="policy" class="form-select form-select-sm">
                                <option value="exclude" {% if c_policy == 'exclude' %}selected{% endif %}>Ocultar completamente (Exclude)</option>
                                <option value="show_but_exclude" {% if c_policy == 'show_but_exclude' %}selected{% endif %}>Mostrar pero excluir del ranking (Show but exclude)</option>
                                <option value="include" {% if c_policy == 'include' %}selected{% endif %}>Incluir en ranking con advertencia (Include)</option>
                            </select>
                            <button type="submit" class="btn btn-sm btn-primary">Guardar</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
"""

content = content.replace("<!-- Settings Table -->", ui_snippet + "\n    <!-- Settings Table -->")
with open("src/dealhunter/web/templates/admin/settings.html", "w") as f:
    f.write(content)
