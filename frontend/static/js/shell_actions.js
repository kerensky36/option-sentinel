/**
 * shell_actions.js — Erase All Data and Demo | Live switch handlers (specs/021),
 * moved out of an inline module script for the strict CSP (specs/023).
 */
import { eraseAll, isDemoMode, switchMode } from './auth.js';

for (const b of document.querySelectorAll('#mode-switch button')) {
  b.addEventListener('click', () => {
    const target = b.dataset.mode;
    if ((target === 'demo') !== isDemoMode()) switchMode(target);
  });
}

const btn = document.getElementById('erase-all-btn');
if (btn) {
  btn.addEventListener('click', async () => {
    const confirmed = window.confirm(
      'Erase All Data?\n\nThis will clear:\n' +
      '• Your Schwab token (sessionStorage)\n' +
      '• Position, screener and advice caches — live and demo (sessionStorage)\n\n' +
      'You will need to reconnect your Schwab account.'
    );
    if (confirmed) {
      await eraseAll();
    }
  });
}
