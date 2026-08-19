function setTheme(t) {
    localStorage.setItem('dealhunter_theme', t);
    applyTheme(t);
}

function setDensity(d) {
    localStorage.setItem('dealhunter_density', d);
    document.documentElement.setAttribute('data-density', d);
}
