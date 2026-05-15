/**
 * thesis_ui.js — Thesis group create/assign UI.
 *
 * Wires up the thesis creation form and renders the thesis group list.
 * All state goes to localStorage via thesis_store.js — no server calls.
 */

import {
  getThesisGroups,
  saveThesisGroup,
  deleteThesisGroup,
  getAssignments,
  setAssignment,
} from './thesis_store.js';

/**
 * Generate a simple UUID v4.
 * @returns {string}
 */
function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/**
 * Render the thesis group list into #thesis-list.
 */
export function renderThesisList() {
  const container = document.getElementById('thesis-list');
  if (!container) return;

  const groups = getThesisGroups();
  if (groups.length === 0) {
    container.innerHTML = `<p class="text-gray-500" style="font-size:11px">No thesis groups yet. Add one above.</p>`;
    return;
  }

  const items = groups.map((g) => `
    <div class="flex items-center justify-between bg-gray-800 border border-gray-700 px-3 py-1.5 mb-1" style="border-radius:1px">
      <div>
        <span class="text-gray-200" style="font-size:12px">${escapeHtml(g.name)}</span>
        <span class="text-gray-500 ml-2" style="font-size:10px; letter-spacing:0.08em;">${escapeHtml(g.template_type)}</span>
        ${g.description ? `<span class="text-gray-400 ml-2" style="font-size:11px">${escapeHtml(g.description)}</span>` : ''}
      </div>
      <button
        data-delete-thesis="${g.id}"
        class="text-red-400 hover:text-red-300 px-2 py-0.5 uppercase tracking-wider transition-colors"
        style="font-size:10px">
        ✕
      </button>
    </div>`).join('');

  container.innerHTML = items;

  // Attach delete handlers
  container.querySelectorAll('[data-delete-thesis]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-delete-thesis');
      if (window.confirm('Delete this thesis group and remove all its position assignments?')) {
        deleteThesisGroup(id);
        renderThesisList();
      }
    });
  });
}

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Apply thesis labels to position rows in the table.
 * Called after positions table is rendered.
 */
export function applyThesisLabels() {
  // Handled inline in positions_ui.js via getAssignments()
}

/**
 * Initialise: wire up the Add Thesis button and render existing groups.
 */
function init() {
  renderThesisList();

  const addBtn = document.getElementById('thesis-add-btn');
  if (!addBtn) return;

  addBtn.addEventListener('click', () => {
    const nameInput = document.getElementById('thesis-name');
    const typeSelect = document.getElementById('thesis-type');
    const descInput = document.getElementById('thesis-desc');

    const name = nameInput?.value.trim();
    if (!name) {
      nameInput?.focus();
      return;
    }

    const group = {
      id: uuid(),
      name,
      template_type: typeSelect?.value || 'custom',
      description: descInput?.value.trim() || null,
      alignment_rating: 'moderate',
      status: 'active',
    };

    saveThesisGroup(group);
    renderThesisList();

    // Clear inputs
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
  });
}

init();
