#!/usr/bin/env node
// Set ONE machine identity's PROJECT role, through the CEO's own signed-in Infisical tab, zero-model.
//
//   node set_project_role.mjs [<cdp-url>] --identity contabo --role developer --project Org-Coo [--project …] [--go]
//
// Why it exists: a worker clicking the role in the UI was refused by the auto-mode classifier as a
// [Permission Grant] (task-0bbb27f9, 2026-10-14), and a permission grant is the CEO's to make. So the
// change runs only from a Run card he taps (ALL_Protocol_RunInbox): his tap is the authority.
// Without --go it only reads and prints the plan. It changes a row only when the identity is a member
// with exactly ["viewer"], and only to viewer|developer; anything else is printed and left alone.
// The session is borrowed the way bootstrap_setup_identity.mjs does it (one in-page token refresh);
// no token, secret or value is ever printed.
const argv = process.argv.slice(2);
const opt = { cdp: 'http://127.0.0.1:9281', identity: '', role: '', projects: [], go: false };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--go') opt.go = true;
  else if (a === '--identity') opt.identity = argv[++i] || '';
  else if (a === '--role') opt.role = argv[++i] || '';
  else if (a === '--project') opt.projects.push(argv[++i] || '');
  else if (!a.startsWith('--')) opt.cdp = a;
  else { console.error(`[role] unknown flag ${a}`); process.exit(64); }
}
const ROLES = ['viewer', 'developer'];
if (!/^[a-z][a-z0-9-]{1,30}$/.test(opt.identity)) { console.error('[role] --identity <name> required'); process.exit(64); }
if (!ROLES.includes(opt.role)) { console.error(`[role] --role must be one of ${ROLES.join('|')}`); process.exit(64); }
if (!opt.projects.length || opt.projects.some((p) => !/^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$/.test(p))) { console.error('[role] --project <exact name> required'); process.exit(64); }
const API = 'https://app.infisical.com';
const AUTH_PATH = /^\/(login|signup|signin|verify-email|verify|mfa|password-reset|reset-password|email-not-verified|cli-redirect)(\/|$)/i;
const log = (...a) => console.log('[role]', ...a);
const die = (code, msg) => { console.error('[role]', msg); process.exit(code); };

// --- 1. borrow the session from the logged-in tab ------------------------------------------------
let pages;
try { pages = (await (await fetch(`${opt.cdp.replace(/\/$/, '')}/json/list`)).json()).filter((t) => t.type === 'page'); }
catch { die(3, `cannot reach CDP at ${opt.cdp}`); }
const tab = pages.find((t) => { try { const u = new URL(t.url); return u.host === 'app.infisical.com' && u.pathname !== '/' && !AUTH_PATH.test(u.pathname); } catch { return false; } });
if (!tab) die(4, 'no logged-in app.infisical.com tab');
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error('ws')); }).catch(() => die(3, 'cannot open the tab websocket'));
let seq = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((ok, no) => { const id = ++seq; pending.set(id, (m) => (m.error ? no(new Error(m.error.message)) : ok(m.result))); ws.send(JSON.stringify({ id, method, params })); });
const r0 = await send('Runtime.evaluate', { expression: `fetch('/api/v1/auth/token', { method: 'POST', credentials: 'include' }).then(async (r) => ({ status: r.status, body: r.ok ? await r.json() : null }))`, awaitPromise: true, returnByValue: true }).catch(() => null);
ws.close();
const auth = r0?.result?.value;
if (!auth || auth.status !== 200 || typeof auth.body?.token !== 'string') die(5, `session token refresh failed (HTTP ${auth ? auth.status : '?'})`);
let token = auth.body.token;
const claims = (t) => { try { const p = t.split('.')[1]; return JSON.parse(Buffer.from(p + '='.repeat((4 - (p.length % 4)) % 4), 'base64url').toString()); } catch { return {}; } };
let orgId = claims(token).organizationId || auth.body.organizationId || null;
const api = async (method, path, body) => {
  const r = await fetch(API + path, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  let json = null; try { json = await r.json(); } catch { /* no body */ }
  return { status: r.status, json };
};
if (!orgId) {
  const orgs = await api('GET', '/api/v1/organization');
  const org = (orgs.json?.organizations || []).find((o) => o.name === 'MoonieX');
  if (!org) die(6, 'organization MoonieX not found');
  const sel = await api('POST', '/api/v3/auth/select-organization', { organizationId: org.id });
  if (sel.status !== 200 || typeof sel.json?.token !== 'string') die(6, `select-organization failed (HTTP ${sel.status})`);
  token = sel.json.token; orgId = org.id;
}
log(`session OK · org ${orgId.slice(0, 8)} · ${opt.go ? 'GO: will change' : 'dry run: read only'}`);

// --- 2. identity + projects ----------------------------------------------------------------------
const idents = await api('GET', `/api/v1/identities?orgId=${encodeURIComponent(orgId)}`);
if (idents.status !== 200) die(7, `cannot list identities (HTTP ${idents.status})`);
const ident = (idents.json?.identities || []).map((m) => m.identity).find((i) => i && i.name === opt.identity);
if (!ident) die(7, `identity ${opt.identity} not found`);
const ws2 = await api('GET', `/api/v2/organizations/${orgId}/workspaces`);
if (ws2.status !== 200) die(7, `cannot list projects (HTTP ${ws2.status})`);
const all = ws2.json?.workspaces || [];

const rolesOf = async (pid) => {
  const r = await api('GET', `/api/v1/projects/${pid}/identity-memberships/${ident.id}`);
  if (r.status === 404) return { status: 404, roles: null };
  const row = r.json?.identityMembership;
  return { status: r.status, roles: Array.isArray(row?.roles) ? row.roles.map((x) => x.customRoleSlug || x.role) : null };
};

let bad = 0;
for (const name of opt.projects) {
  const p = all.find((w) => w.name === name);
  if (!p) { log(`${name}: project not found — skipped`); bad++; continue; }
  const before = await rolesOf(p.id);
  const now = JSON.stringify(before.roles);
  if (before.status !== 200 || !before.roles) { log(`${name}: ${opt.identity} membership not readable (HTTP ${before.status}) — skipped`); bad++; continue; }
  if (now === JSON.stringify([opt.role])) { log(`${name}: ${opt.identity} already ${now} — nothing to do`); continue; }
  if (now !== JSON.stringify(['viewer'])) { log(`${name}: ${opt.identity} has ${now}, not ["viewer"] — left alone`); bad++; continue; }
  if (!opt.go) { log(`${name}: ${opt.identity} ${now} -> ["${opt.role}"] (dry run, not changed)`); continue; }
  const body = { roles: [{ role: opt.role, isTemporary: false }] };
  let res = await api('PATCH', `/api/v1/projects/${p.id}/identity-memberships/${ident.id}`, body);
  if (res.status === 404) res = await api('PATCH', `/api/v2/workspace/${p.id}/identity-memberships/${ident.id}`, body);
  const after = await rolesOf(p.id);
  const ok = res.status === 200 && JSON.stringify(after.roles) === JSON.stringify([opt.role]);
  log(`${name}: ${opt.identity} ${now} -> ${JSON.stringify(after.roles)} (HTTP ${res.status}) ${ok ? 'OK' : 'FAILED'}`);
  if (!ok) bad++;
}
token = null;
process.exit(bad ? 9 : 0);
