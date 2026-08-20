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
