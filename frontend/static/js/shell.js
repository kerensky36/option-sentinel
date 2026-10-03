/**
 * shell.js — page shell state before first paint (specs/023: moved out of inline
 * scripts so every page can run under `script-src 'self'`).
 * Classic script, loaded right after the top nav: shows the demo banner and marks
 * the active Demo | Live segment (specs/021).
 */
(function () {
  var demo = sessionStorage.getItem('demo_mode') === 'true';
  var banner = document.getElementById('demo-banner');
  if (banner && demo) banner.style.display = 'block';

  var active = document.getElementById(demo ? 'mode-switch-demo' : 'mode-switch-live');
  if (active) active.setAttribute('aria-pressed', 'true');
  if (!demo) return;
  var live = document.getElementById('mode-switch-live');
  if (live && !sessionStorage.getItem('schwab_access_token')) {
    live.title = 'Connect your Schwab account to see live data (demo state is kept)';
  }
})();
