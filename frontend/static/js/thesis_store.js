/**
 * thesis_store.js — localStorage-backed thesis group persistence.
 *
 * All data is stored client-side only. No server API calls are made.
 * The server has zero knowledge of this data.
 */

const THESIS_GROUPS_KEY = 'thesis_groups';
const THESIS_ASSIGNMENTS_KEY = 'thesis_assignments';

// ── Thesis Groups ────────────────────────────────────────────────────────────

/**
 * Get all thesis groups from localStorage.
 * @returns {Array<object>} Array of LocalThesisGroup objects.
 */
export function getThesisGroups() {
  try {
    const raw = localStorage.getItem(THESIS_GROUPS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error('thesis_store.getThesisGroups: parse error', e);
    return [];
  }
}

/**
 * Save (add or update) a thesis group in localStorage.
 * If a group with the same id exists, it is replaced.
 * @param {object} group - LocalThesisGroup object (must have id field).
 */
export function saveThesisGroup(group) {
  const groups = getThesisGroups();
  const idx = groups.findIndex((g) => g.id === group.id);
  if (idx >= 0) {
    groups[idx] = group;
  } else {
    groups.push(group);
  }
  localStorage.setItem(THESIS_GROUPS_KEY, JSON.stringify(groups));
}

/**
 * Delete a thesis group by id from localStorage.
 * Also removes all assignments that reference this group.
 * @param {string} id - UUID of the group to delete.
 */
export function deleteThesisGroup(id) {
  const groups = getThesisGroups().filter((g) => g.id !== id);
  localStorage.setItem(THESIS_GROUPS_KEY, JSON.stringify(groups));

  // Unassign any positions that referenced this group
  const assignments = getAssignments().map((a) =>
    a.thesis_group_id === id ? { ...a, thesis_group_id: null } : a
  );
  localStorage.setItem(THESIS_ASSIGNMENTS_KEY, JSON.stringify(assignments));
}

// ── Assignments ──────────────────────────────────────────────────────────────

/**
 * Get all position-to-thesis assignments from localStorage.
 * @returns {Array<{symbol: string, thesis_group_id: string|null}>}
 */
export function getAssignments() {
  try {
    const raw = localStorage.getItem(THESIS_ASSIGNMENTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error('thesis_store.getAssignments: parse error', e);
    return [];
  }
}

/**
 * Assign a position symbol to a thesis group (or null to unassign).
 * @param {string} symbol - OCC option symbol.
 * @param {string|null} thesisGroupId - UUID of the thesis group, or null.
 */
export function setAssignment(symbol, thesisGroupId) {
  const assignments = getAssignments();
  const idx = assignments.findIndex((a) => a.symbol === symbol);
  const entry = { symbol, thesis_group_id: thesisGroupId };
  if (idx >= 0) {
    assignments[idx] = entry;
  } else {
    assignments.push(entry);
  }
  localStorage.setItem(THESIS_ASSIGNMENTS_KEY, JSON.stringify(assignments));
}
