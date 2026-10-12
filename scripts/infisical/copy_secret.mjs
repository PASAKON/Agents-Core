#!/usr/bin/env node
// Copy ONE existing secret from one Infisical project into another, zero-model: the value goes from the
// source listing straight into the target POST inside this process, is compared with the target in
// memory, and is dropped. Nothing prints it — not the value, not its length, not its last characters.
//
//   node copy_secret.mjs <cdp-url> --from <Project>:<env>:<name-regex> --to <Project>:<env>:<NAME>
//        --comment "<purpose>" [--meta k=v ...] [--dry]
//
// Session: borrowed from the CEO's logged-in app.infisical.com tab exactly as
// bootstrap_setup_identity.mjs does — ONE in-page POST /api/v1/auth/token (the refresh token is an
// httpOnly cookie), then plain HTTPS with that bearer token. Nothing is typed, clicked, read off the
// DOM or screenshotted.
//
// Source: every folder of the source env (Org-Infra: the PLAN §3b closed list, any other project: /);
// only shared secrets whose NAME matches the regex count, and exactly one must match or nothing is
// written (the matching names are printed, names only). One unreadable folder refuses too: the match
// could not be proven unique.
// Target: written at / of <Project>/<env>; it must not exist yet (HTTP 404), and Org-Infra is never a
// target (PLAN §3b rule 1: only the CEO writes there). Metadata = the --meta pairs (a real run needs
// provider_name console_url scope expires, as `infisical_setup.py put` does, PLAN §4c) plus, set here and
// not overridable: source, rotate_with=source, owner=CTO, created=<date> <session>, status=active.
// --dry stops after the source match and the target-absent check.
//
// Output: names, paths, HTTP statuses, MATCH / MISMATCH. Never a response body (an API error message
// can echo its input). Exit: 0 done (or dry ok) · 64 usage/refused · 3 CDP · 4 no signed-in tab ·
// 5 token · 6 org · 7 project/env/listing · 8 not exactly one match · 9 target exists ·
// 10 target state unknown · 11 write failed · 12 verify MISMATCH.
// Node 22+, or node 20 with --experimental-websocket. Tests: tests/js/copy_secret.test.mjs.
// INFISICAL_API_URL (tests only) may point the API at a loopback server, nowhere else.

const USAGE = 'usage: copy_secret.mjs <cdp-url> --from <Project>:<env>:<name-regex> --to <Project>:<env>:<NAME> --comment "<purpose>" [--meta k=v ...] [--dry]';
const ORG_INFRA = 'Org-Infra';
const ORG_INFRA_FOLDERS = ['/', '/dns', '/deploy', '/repo', '/net', '/db', '/vault']; // PLAN §3b closed list
const SET_HERE = ['source', 'rotate_with', 'owner', 'created', 'status'];
const NEEDED_META = ['provider_name', 'console_url', 'scope', 'expires']; // + owner, set here (PLAN §4c)
const LOOPBACK = new Set(['127.0.0.1', 'localhost', '[::1]']);
const AUTH_PATH = /^\/(login|signup|signin|verify-email|verify|mfa|password-reset|reset-password|email-not-verified|cli-redirect)(\/|$)/i;
const log = (...a) => console.log('[copy]', ...a);
const die = (code, msg) => { console.error('[copy]', msg); process.exit(code); };
const usage = (msg) => die(64, `${msg}\n${USAGE}`);
const isOrgInfra = (name) => String(name).toLowerCase() === ORG_INFRA.toLowerCase();

// --- 0. arguments: every refusal happens before the browser is touched ------------------------------
function spec(flag, raw, last) {
  const i = raw.indexOf(':'), j = i < 0 ? -1 : raw.indexOf(':', i + 1);
  if (j < 0) usage(`${flag} must be <Project>:<env>:${last}`);
  const project = raw.slice(0, i), env = raw.slice(i + 1, j), rest = raw.slice(j + 1);
  if (!/^[A-Za-z0-9][A-Za-z0-9-]{0,63}$/.test(project)) usage(`${flag}: bad project name`);
  if (!['dev', 'prod'].includes(env)) usage(`${flag}: env must be dev or prod`);
  if (!rest) usage(`${flag}: empty ${last}`);
  return { project, env, rest };
}

const argv = process.argv.slice(2);
const opt = { cdp: null, from: null, to: null, comment: null, meta: [], dry: false };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  const val = () => { if (i + 1 >= argv.length) usage(`${a} needs a value`); return argv[++i]; };
  if (a === '--dry') opt.dry = true;
  else if (a === '--from') opt.from = val();
  else if (a === '--to') opt.to = val();
  else if (a === '--comment') opt.comment = val();
  else if (a === '--meta') opt.meta.push(val());
  else if (a.startsWith('--')) usage(`unknown flag ${a}`);
  else if (opt.cdp === null) opt.cdp = a;
  else usage(`unexpected argument ${a}`);
}
if (!opt.cdp) usage('missing <cdp-url>');
if (!opt.from || !opt.to) usage('need --from and --to');

const from = spec('--from', opt.from, '<name-regex>');
try { from.re = new RegExp(from.rest); } catch { usage('--from: the name regex does not compile'); }
const to = spec('--to', opt.to, '<NAME>');
to.name = to.rest;
if (!/^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$/.test(to.name)) usage('--to: NAME must be UPPER_SNAKE_CASE with at least two parts (PLAN §4b)');
if (isOrgInfra(to.project)) usage('refused: Org-Infra is never a target — only the CEO writes there (PLAN §3b rule 1)');

const meta = {};
for (const item of opt.meta) {
  const k = item.slice(0, item.indexOf('=')).trim(), v = item.slice(item.indexOf('=') + 1).trim();
  if (item.indexOf('=') < 1 || !/^[a-z][a-z0-9_]{0,40}$/.test(k) || !v) usage(`bad --meta ${k || '?'}: use key=value`);
  if (SET_HERE.includes(k)) usage(`--meta ${k} is set by this script, drop it`);
  if (k in meta) usage(`--meta ${k} given twice`);
  meta[k] = v;
}
if (!opt.dry) {
  const missing = NEEDED_META.filter((k) => !(k in meta));
  if (missing.length || !opt.comment || !opt.comment.trim()) {
    usage(`refused: a new secret needs --comment <purpose> and --meta ${missing.map((k) => `${k}=…`).join(' ') || '(all given)'} (PLAN §4c)`);
  }
}

const loopback = (raw, what) => {
  let u; try { u = new URL(raw); } catch { usage(`${what} is not a URL`); }
  if (!['http:', 'https:'].includes(u.protocol) || !LOOPBACK.has(u.hostname)) usage(`${what} must be a loopback http(s) URL`);
  return u.origin;
};
const cdpUrl = loopback(opt.cdp, '<cdp-url>');   // the token comes back over this socket in clear
const API = process.env.INFISICAL_API_URL ? loopback(process.env.INFISICAL_API_URL, 'INFISICAL_API_URL') : 'https://app.infisical.com';
if (typeof WebSocket === 'undefined') die(64, 'this node has no global WebSocket: use node 22+, or node 20 with --experimental-websocket');

// --- 1. the logged-in tab (bootstrap_setup_identity.mjs §1) -------------------------------------------
let pages;
try { pages = (await (await fetch(`${cdpUrl}/json/list`)).json()).filter((t) => t.type === 'page'); }
catch { die(3, `cannot reach CDP at ${cdpUrl}`); }
const tab = pages.find((t) => { try { const u = new URL(t.url); return u.host === 'app.infisical.com' && u.pathname !== '/' && !AUTH_PATH.test(u.pathname); } catch { return false; } });
if (!tab) die(4, `no signed-in app.infisical.com tab — the CEO signs in through the relay (tabs: ${pages.map((t) => { try { const u = new URL(t.url); return u.host + u.pathname; } catch { return '?'; } }).join(' | ') || 'none'})`);
log(`tab ${String(tab.id).slice(0, 8)} at ${new URL(tab.url).pathname}`);

const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error('ws')); }).catch(() => die(3, 'cannot open the tab websocket'));
let seq = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((ok, no) => { const id = ++seq; pending.set(id, (m) => (m.error ? no(new Error(m.error.message)) : ok(m.result))); ws.send(JSON.stringify({ id, method, params })); });
const inPage = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error('page threw'); return r.result?.value; };

// --- 2. borrow the session: one fetch inside the page ---------------------------------------------------
const auth = await inPage(`fetch('/api/v1/auth/token', { method: 'POST', credentials: 'include' }).then(async (r) => ({ status: r.status, body: r.ok ? await r.json() : null }))`).catch(() => null);
ws.close();
if (auth && (auth.status === 401 || auth.status === 403)) die(4, `the tab is signed out (token refresh HTTP ${auth.status}) — the CEO signs in through the relay`);
if (!auth || auth.status !== 200 || !auth.body || typeof auth.body.token !== 'string') die(5, `session token refresh failed (HTTP ${auth ? auth.status : '?'})`);
let token = auth.body.token;
const claims = (t) => { try { const p = t.split('.')[1]; return JSON.parse(Buffer.from(p + '='.repeat((4 - (p.length % 4)) % 4), 'base64url').toString()); } catch { return {}; } };
let orgId = claims(token).organizationId || auth.body.organizationId || null;
log(`session token OK · org ${orgId ? String(orgId).slice(0, 8) : 'not yet selected'}`);

const api = async (method, path, query, body) => {
  const url = new URL(API + path);
  for (const [k, v] of Object.entries(query || {})) url.searchParams.set(k, v);
  let r;
  try { r = await fetch(url, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) }); }
  catch { return { status: 0, json: null }; }
  let json = null; try { json = await r.json(); } catch { /* no body */ }
  return { status: r.status, json };
};

if (!orgId) {
  const orgs = await api('GET', '/api/v1/organization');
  const list = orgs.json?.organizations || [];
  const org = list.find((o) => o.name === 'MoonieX') || (list.length === 1 ? list[0] : null);
  if (!org) die(6, `cannot pick the organization (${list.length} listed)`);
  const sel = await api('POST', '/api/v3/auth/select-organization', { }, { organizationId: org.id });
  if (sel.status !== 200 || typeof sel.json?.token !== 'string') die(6, `select-organization failed (HTTP ${sel.status})`);
  token = sel.json.token; orgId = org.id;
  log(`organization selected: ${org.name}`);
}

// --- 3. both projects, by name -----------------------------------------------------------------------
const listed = await api('GET', `/api/v2/organizations/${encodeURIComponent(orgId)}/workspaces`);
if (listed.status !== 200) die(7, `cannot list projects (HTTP ${listed.status})`);
const projects = Array.isArray(listed.json?.workspaces) ? listed.json.workspaces : [];
async function project(want, env) {
  const lc = want.toLowerCase();
  const p = projects.find((x) => x.name === want) || projects.find((x) => String(x.name).toLowerCase() === lc)
    || projects.find((x) => String(x.slug).toLowerCase() === lc);
  if (!p) die(7, `no project ${want} visible to this session (have: ${projects.map((x) => x.name).join(', ') || 'none'})`);
  let envs = Array.isArray(p.environments) ? p.environments : null;
  if (!envs) { const r = await api('GET', `/api/v1/projects/${encodeURIComponent(p.id)}`); envs = r.json?.project?.environments || []; }
  if (!envs.some((e) => e.slug === env)) die(7, `project ${p.name} has no environment ${env}`);
  return p;
}
const src = await project(from.project, from.env);
const dst = await project(to.project, to.env);
if (isOrgInfra(dst.name)) die(64, 'refused: Org-Infra is never a target — only the CEO writes there (PLAN §3b rule 1)');
const where = (p, env, folder) => `${p.name}/${env}${folder === '/' ? '' : folder}`;

// --- 4. the source: exactly one name matches ----------------------------------------------------------
const hits = [];
for (const folder of isOrgInfra(src.name) ? ORG_INFRA_FOLDERS : ['/']) {
  const r = await api('GET', '/api/v3/secrets/raw', { workspaceId: src.id, environment: from.env, secretPath: folder, expandSecretReferences: 'true', include_imports: 'false' });
  if (r.status === 404) { log(`source ${where(src, from.env, folder)}: HTTP 404 (no such folder)`); continue; }
  if (r.status !== 200 || !Array.isArray(r.json?.secrets)) die(7, `cannot list ${where(src, from.env, folder)} (HTTP ${r.status}); a folder that cannot be read means the match cannot be proven unique — nothing written`);
  const shared = r.json.secrets.filter((s) => s && typeof s.secretKey === 'string' && s.type !== 'personal');
  const matched = shared.filter((s) => from.re.test(s.secretKey));
  log(`source ${where(src, from.env, folder)}: HTTP 200 · ${shared.length} names · ${matched.length} match`);
  for (const s of matched) hits.push({ folder, name: s.secretKey, value: s.secretValue });
}
if (hits.length !== 1) {
  for (const h of hits) { log(`  match: ${where(src, from.env, h.folder)} ${h.name}`); h.value = null; }
  die(8, `${hits.length} names match /${from.rest}/ — need exactly one; nothing written`);
}
const hit = hits.pop();
let value = typeof hit.value === 'string' && hit.value !== '' ? hit.value : null;
hit.value = null;
if (value === null) die(8, `source ${where(src, from.env, hit.folder)} ${hit.name} holds no value; nothing written`);
const sourceRef = `${src.name}/${from.env}${hit.folder === '/' ? '' : hit.folder}/${hit.name}`;
log(`source match: ${sourceRef} (exactly one)`);

// --- 5. the target must not exist ---------------------------------------------------------------------
const at = { workspaceId: dst.id, environment: to.env, secretPath: '/' };
const dstWhere = where(dst, to.env, '/');
const exists = (await api('GET', `/api/v3/secrets/raw/${encodeURIComponent(to.name)}`, at)).status;
if (exists === 200) die(9, `target ${dstWhere} ${to.name} already exists (HTTP 200); refusing to overwrite`);
if (exists !== 404) die(10, `cannot confirm target ${dstWhere} ${to.name} is absent (HTTP ${exists}); nothing written`);
log(`target ${dstWhere} ${to.name}: absent (HTTP 404)`);
if (opt.dry) { value = null; log('dry run: stopping before any write'); process.exit(0); }

// --- 6. write, then verify in memory ------------------------------------------------------------------
const by = [process.env.CTO_SESSION_ID, process.env.CXO_SESSION_ID, process.env.ORG_TASK_ID].find((s) => /^[\w.-]{1,64}$/.test(s || '')) || 'cli';
const metadata = { ...meta, source: sourceRef, rotate_with: 'source', owner: 'CTO', created: `${new Date().toISOString().slice(0, 10)} ${by}`, status: 'active' };
const wrote = await api('POST', `/api/v3/secrets/raw/${encodeURIComponent(to.name)}`, {}, {
  ...at, secretValue: value, type: 'shared', secretComment: opt.comment.trim(),
  secretMetadata: Object.entries(metadata).map(([key, v]) => ({ key, value: v })),
});
if (wrote.status !== 200) {
  value = null;
  const kind = typeof wrote.json?.error === 'string' && /^[A-Za-z ]{1,40}$/.test(wrote.json.error) ? ` ${wrote.json.error}` : '';
  die(11, `write ${dstWhere} ${to.name} failed (HTTP ${wrote.status}${kind}); rerun once the cause is fixed (a rerun refuses if it did land)`);
}
log(`write ${dstWhere} ${to.name}: HTTP 200 · metadata ${Object.keys(metadata).join(' ')}`);

const back = await api('GET', `/api/v3/secrets/raw/${encodeURIComponent(to.name)}`, at);
let got = back.status === 200 && typeof back.json?.secret?.secretValue === 'string' ? back.json.secret.secretValue : null;
const same = got !== null && got === value;
const stored = new Set((back.json?.secret?.secretMetadata || []).map((m) => m && m.key));
value = null; got = null; back.json = null;
const lost = Object.keys(metadata).filter((k) => !stored.has(k));
if (back.status === 200 && lost.length) log(`warning: metadata not stored: ${lost.join(' ')}`);
log(`verify ${dstWhere} ${to.name}: HTTP ${back.status} · ${same ? 'MATCH' : 'MISMATCH'}`);
process.exit(same ? 0 : 12);
