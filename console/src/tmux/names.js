// Known roles a session can be spawned as. Extend when a new C-level chat
// REPL is wired up (see command.js). The session list only surfaces tmux
// sessions whose name matches `<role>-<slug>` for a role in this list, so
// unrelated tmux sessions on the host don't leak into the console UI.
export const ROLES = ['cto', 'cmo', 'cfo', 'cxo'];

export function slugify(input) {
  const slug = String(input ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
  return slug || `session-${Date.now().toString(36)}`;
}

export function buildSessionName(role, slug) {
  return `${role}-${slug}`;
}

// tmux session names are `<role>-<slug>`; slugs themselves may contain
// dashes (e.g. "contabo-migration"), so split on the first dash only.
export function parseSessionName(name) {
  const idx = name.indexOf('-');
  if (idx === -1) return null;
  const role = name.slice(0, idx);
  const slug = name.slice(idx + 1);
  if (!role || !slug) return null;
  return { role, slug, name };
}
