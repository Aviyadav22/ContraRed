// Apply saved theme preference synchronously to prevent flash-of-wrong-theme.
// Loaded in <head> before any other script so it runs before React mounts.
(function () {
    try {
        var saved = localStorage.getItem('contrared-theme');
        if (saved === 'dark' || saved === 'light') {
            document.documentElement.setAttribute('data-theme', saved);
        }
    } catch (e) { /* localStorage unavailable — keep HTML default */ }
})();
