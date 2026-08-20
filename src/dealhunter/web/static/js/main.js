function setTheme(t) {
    localStorage.setItem('dealhunter_theme', t);
    applyTheme(t);
}

function setDensity(d) {
    localStorage.setItem('dealhunter_density', d);
    document.documentElement.setAttribute('data-density', d);
}

function filterMultiselect(input, itemSelector) {
    const filter = input.value.toLowerCase();
    const items = document.querySelectorAll(itemSelector);
    items.forEach(item => {
        const text = item.textContent || item.innerText;
        if (text.toLowerCase().indexOf(filter) > -1) {
            item.style.display = "";
        } else {
            item.style.display = "none";
        }
    });
}

function clearMultiselect(name) {
    const checks = document.querySelectorAll(`.${name}-check`);
    let changed = false;
    checks.forEach(check => {
        if (check.checked) {
            check.checked = false;
            changed = true;
        }
    });
    // Trigger HTMX if attached, or just submit the form
    if (changed) {
        if (checks.length > 0 && checks[0].hasAttribute("hx-get")) {
            htmx.trigger(checks[0], "change");
        }
        // Also apply the clear
        document.getElementById('filter-form').dispatchEvent(new Event('submit'));
    }
}

// --- Rappi App Launcher (directed Android Intent, no browser) ---
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.rappi-launcher').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var btn = form.querySelector('button[type="submit"]');
            var feedback = form.querySelector('.rappi-feedback');
            var data = new FormData(form);

            btn.disabled = true;
            btn.textContent = '⏳ Abriendo…';
            if (feedback) feedback.textContent = '';

            fetch('/api/open-rappi', {
                method: 'POST',
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                body: data
            })
            .then(function(r) { return r.json(); })
            .then(function(j) {
                btn.disabled = false;
                btn.textContent = '🛵 Abrir en Rappi';
                if (feedback) {
                    feedback.textContent = j.ok ? j.message : (j.error || 'Error desconocido');
                    feedback.className = 'rappi-feedback ms-2 small ' + (j.ok ? 'text-success' : 'text-danger');
                }
            })
            .catch(function() {
                btn.disabled = false;
                btn.textContent = '🛵 Abrir en Rappi';
                if (feedback) {
                    feedback.textContent = 'Error de conexión con el servidor.';
                    feedback.className = 'rappi-feedback ms-2 small text-danger';
                }
            });
        });
    });
});
