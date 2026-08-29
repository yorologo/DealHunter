with open("src/dealhunter/web/templates/components/product_card.html", "r") as f:
    content = f.read()

replacement = """
        {% if p.promotion_label %}
            <div class="mb-2"><span class="badge bg-danger">{{ p.promotion_label }}</span></div>
        {% endif %}

        {% if p.requires_membership and p.requires_membership != "NONE" %}
            <div class="mb-2">
                {% if p.ranking_eligible == False %}
                    <span class="badge bg-secondary text-light" title="Not eligible for ranking">Requiere {{ p.requires_membership }}</span>
                {% else %}
                    <span class="badge bg-danger text-light" title="Requiere membresía para redimir">Requiere {{ p.requires_membership }}</span>
                {% endif %}
            </div>
        {% endif %}
"""

content = content.replace("""        {% if p.promotion_label %}
            <div class="mb-2"><span class="badge bg-danger">{{ p.promotion_label }}</span></div>
        {% endif %}""", replacement.strip())

with open("src/dealhunter/web/templates/components/product_card.html", "w") as f:
    f.write(content)
