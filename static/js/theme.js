// Autumn Theme Toggle & Persistence
(function() {
    function getStoredTheme() {
        return localStorage.getItem('prioritysuite-theme') || 'auto';
    }

    function setStoredTheme(theme) {
        localStorage.setItem('prioritysuite-theme', theme);
    }

    function getPreferredTheme() {
        const stored = getStoredTheme();
        if (stored && stored !== 'auto') {
            return stored;
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        const effectiveTheme = (theme === 'auto') ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;
        document.documentElement.setAttribute('data-bs-theme', effectiveTheme);
        const icon = document.getElementById('theme-toggle-icon');
        const text = document.getElementById('theme-toggle-text');
        if (icon) {
            icon.textContent = effectiveTheme === 'dark' ? '🌙' : '🍂';
        }
        if (text) {
            text.textContent = effectiveTheme === 'dark' ? 'Dark (Autumn)' : 'Light (Parchment)';
        }
    }

    applyTheme(getPreferredTheme());

    window.toggleTheme = function() {
        const current = document.documentElement.getAttribute('data-bs-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        setStoredTheme(next);
        applyTheme(next);
    };

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (getStoredTheme() === 'auto') {
            applyTheme('auto');
        }
    });
})();
