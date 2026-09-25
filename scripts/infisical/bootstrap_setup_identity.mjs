#!/usr/bin/env node
// Infisical phase 1, zero-model: once the CEO has logged in to app.infisical.com in the Browser Home,
// make sure the org identity `setup` exists (org Admin, Universal Auth) and hand a fresh client
// secret to `tools/infisical_setup.py save setup --stdin` — through the API, never through the UI.
//
//   node bootstrap_setup_identity.mjs <cdp-url> [--dry]
//
// How the session is borrowed: the SPA keeps its refresh token in an httpOnly cookie, so ONE fetch
// runs inside the page (POST /api/v1/auth/token, credentials: include) and returns an access token
// for the org the CEO is in. Everything after that is plain HTTPS from this process with that
// bearer token. Nothing is typed, clicked or screenshotted; no value is ever printed (not the
// token, not the secret, not their lengths). --dry stops before creating anything.
// Plan: docs/design/secrets-infisical/PLAN.md §6 phase 1 (CEO-approved 2026-09-25).
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const [cdpUrl = 'http://127.0.0.1:9281', flag = ''] = process.argv.slice(2);
const DRY = flag === '--dry';
const API = 'https://app.infisical.com';
const IDENTITY = 'setup';
const SECRET_TTL = 14 * 86_400; // the admin identity lives only for the migration (PLAN §3)
const TOOL = process.env.INFISICAL_SETUP_PY || resolve(dirname(fileURLToPath(import.meta.url)), '../../tools/infisical_setup.py');
const AUTH_PATH = /^\/(login|signup|signin|verify-email|verify|mfa|password-reset|reset-password|email-not-verified|cli-redirect)(\/|$)/i;
const log = (...a) => console.log('[bootstrap]', ...a);
const die = (code, msg) => { console.error('[bootstrap]', msg); process.exit(code); };

// --- 1. the logged-in tab ---------------------------------------------------------------------
let pages;
try { pages = (await (await fetch(`${cdpUrl.replace(/\/$/, '')}/json/list`)).json()).filter((t) => t.type === 'page'); }
catch { die(3, `cannot reach CDP at ${cdpUrl}`); }
const tab = pages.find((t) => { try { const u = new URL(t.url); return u.host === 'app.infisical.com' && u.pathname !== '/' && !AUTH_PATH.test(u.pathname); } catch { return false; } });
if (!tab) die(4, `no logged-in app.infisical.com tab (tabs: ${pages.map((t) => { try { const u = new URL(t.url); return u.host + u.pathname; } catch { return '?'; } }).join(' | ') || 'none'})`);
log(`tab ${tab.id.slice(0, 8)} at ${new URL(tab.url).pathname}`);

const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error('ws')); }).catch(() => die(3, 'cannot open the tab websocket'));
let seq = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((ok, no) => { const id = ++seq; pending.set(id, (m) => (m.error ? no(new Error(m.error.message)) : ok(m.result))); ws.send(JSON.stringify({ id, method, params })); });
const inPage = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error('page threw'); return r.result?.value; };

// --- 2. borrow the session: one fetch inside the page --------------------------------------------
const auth = await inPage(`fetch('/api/v1/auth/token', { method: 'POST', credentials: 'include' }).then(async (r) => ({ status: r.status, body: r.ok ? await r.json() : null }))`).catch(() => null);
ws.close();
if (!auth || auth.status !== 200 || !auth.body || typeof auth.body.token !== 'string') die(5, `session token refresh failed (HTTP ${auth ? auth.status : '?'})`);
let token = auth.body.token;
const claims = (t) => { try { const p = t.split('.')[1]; return JSON.parse(Buffer.from(p + '='.repeat((4 - (p.length % 4)) % 4), 'base64url').toString()); } catch { return {}; } };
let orgId = claims(token).organizationId || auth.body.organizationId || null;
log(`session token OK · org ${orgId ? orgId.slice(0, 8) : 'not yet selected'}`);

const api = async (method, path, body) => {
  const r = await fetch(API + path, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  let json = null; try { json = await r.json(); } catch { /* no body */ }
  return { status: r.status, json };
};

if (!orgId) {
  const orgs = await api('GET', '/api/v1/organization');
  const list = orgs.json?.organizations || [];
  const org = list.find((o) => o.name === 'MoonieX') || (list.length === 1 ? list[0] : null);
  if (!org) die(6, `cannot pick the organization (${list.length} listed)`);
  const sel = await api('POST', '/api/v3/auth/select-organization', { organizationId: org.id });
  if (sel.status !== 200 || typeof sel.json?.token !== 'string') die(6, `select-organization failed (HTTP ${sel.status})`);
  token = sel.json.token; orgId = org.id;
  log(`organization selected: ${org.name}`);
}

// --- 3. the identity ---------------------------------------------------------------------------
const listed = await api('GET', `/api/v1/identities?orgId=${encodeURIComponent(orgId)}`);
if (listed.status !== 200) die(7, `cannot list identities (HTTP ${listed.status}) — is the CEO org admin?`);
let ident = (listed.json?.identities || []).map((m) => m.identity).find((i) => i && i.name === IDENTITY);
log(ident ? `identity ${IDENTITY} exists (${ident.id.slice(0, 8)})` : `identity ${IDENTITY} missing`);
if (DRY) { log('dry run: stopping before any change'); process.exit(0); }
if (!ident) {
  const made = await api('POST', '/api/v1/identities', { name: IDENTITY, organizationId: orgId, role: 'admin' });
  if (made.status !== 200 || !made.json?.identity?.id) die(7, `create identity failed (HTTP ${made.status})`);
  ident = made.json.identity; log(`identity ${IDENTITY} created (org role admin)`);
}

let ua = await api('GET', `/api/v1/auth/universal-auth/identities/${ident.id}`);
if (ua.status !== 200) {
  ua = await api('POST', `/api/v1/auth/universal-auth/identities/${ident.id}`, {});
  if (ua.status !== 200) die(8, `attach Universal Auth failed (HTTP ${ua.status})`);
  log('Universal Auth attached');
}
const clientId = ua.json?.identityUniversalAuth?.clientId;
if (typeof clientId !== 'string' || !clientId) die(8, 'Universal Auth has no client id');

const desc = `${IDENTITY}-${new Date().toISOString().slice(0, 10)}`;
const made = await api('POST', `/api/v1/auth/universal-auth/identities/${ident.id}/client-secrets`, { description: desc, ttl: SECRET_TTL });
let secret = typeof made.json?.clientSecret === 'string' ? made.json.clientSecret : null;
if (made.status !== 200 || !secret) die(9, `create client secret failed (HTTP ${made.status})`);
token = null;
log(`client secret created (${desc}, ${SECRET_TTL / 86_400} days) · handing the pair to the save tool`);

// --- 4. save it on this box, unseen ----------------------------------------------------------------
const child = spawn('python3', [TOOL, 'save', IDENTITY, '--stdin'], { stdio: ['pipe', 'inherit', 'inherit'] });
child.stdin.end(`${clientId}\n${secret}\n`);
secret = null;
const code = await new Promise((r) => { child.on('exit', (c) => r(c ?? 1)); child.on('error', () => r(127)); });
log(`save tool exit code ${code}`);
process.exit(code);
