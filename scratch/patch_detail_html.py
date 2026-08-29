with open("src/dealhunter/web/templates/product_detail.html", "r") as f:
    content = f.read()

replacement = """
                <div class="d-flex justify-content-between align-items-start">
                    <h2 class="fw-bold mb-3">{{ p.product_name }}</h2>
"""

badge = """
                {% if p.requires_membership and p.requires_membership != "NONE" %}
                    <div class="mb-3">
                    {% if not p.ranking_eligible %}
                        <span class="badge bg-secondary text-light fs-6" title="Not eligible for ranking"><i class="bi bi-lock-fill"></i> Requiere {{ p.requires_membership }}</span>
                    {% else %}
                        <span class="badge bg-danger text-light fs-6" title="Requiere membresía para redimir"><i class="bi bi-star-fill"></i> Requiere {{ p.requires_membership }}</span>
                    {% endif %}
                    </div>
                {% endif %}
"""

content = content.replace(replacement, badge + replacement)

with open("src/dealhunter/web/templates/product_detail.html", "w") as f:
    f.write(content)
