// Autumn Theme Toggle & Persistence
(function() {
    function getServerTheme() {
        return document.documentElement.getAttribute('data-server-theme') || '';
    }

    function getStoredTheme() {
        return localStorage.getItem('prioritysuite-theme');
    }

    function setStoredTheme(theme) {
        localStorage.setItem('prioritysuite-theme', theme);
    }

    function getPreferredTheme() {
        const stored = getStoredTheme();
        if (stored && stored !== 'auto') {
            return stored;
        }
        const server = getServerTheme();
        if (server && server !== 'auto') {
            return server;
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        const effectiveTheme = (theme === 'auto' || !theme) ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;
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
        if (!getStoredTheme() || getStoredTheme() === 'auto') {
            applyTheme('auto');
        }
    });
})();
