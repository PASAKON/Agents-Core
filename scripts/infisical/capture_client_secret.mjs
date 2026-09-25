#!/usr/bin/env node
// Capture a freshly created Infisical Universal Auth client secret straight off the wire and hand it
// to `tools/infisical_setup.py save <identity> --stdin`, so no person and no model ever sees it.
//
//   node capture_client_secret.mjs <cdp-url> <identity-name> <client-id> [--check | --wait]
//
//   (default)  enable Network, click the Create button of the open "create client secret" form,
//              catch the response of POST .../api/v1/auth/universal-auth/identities/<id>/client-secrets,
//              read `clientSecret` from its body, close the dialog (Escape) and pipe
//              "<clientId>\n<clientSecret>\n" into the save tool.
//   --wait     same, but do not click: wait up to 5 min for a person to click Create.
//   --check    attach, find the Create button, print what was found, click nothing, exit.
//
// Output: only this script's own status lines (no values), the save tool's stdout/stderr, and its
// exit code. Never the response body, never the secret, never its length.
//
// Node 22+ (global WebSocket + fetch). Env overrides: INFISICAL_SETUP_PY (path to the tool),
// PYTHON (interpreter, default python3), CDP_TARGET_ID (pick a tab by id).
// Brief: docs/ops/briefs/infisical-setup-secret.md · Plan: docs/design/secrets-infisical/PLAN.md §6.
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const [cdpUrl, identity, clientId, mode = ''] = process.argv.slice(2);
if (!cdpUrl || !identity || !clientId || !['', '--check', '--wait'].includes(mode)) {
  console.error('usage: capture_client_secret.mjs <cdp-url> <identity-name> <client-id> [--check|--wait]');
  process.exit(64);
}
if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(identity)) { console.error(`bad identity name: ${identity}`); process.exit(64); }
if (!/^[A-Za-z0-9-]{8,64}$/.test(clientId)) { console.error('client id does not look like an id'); process.exit(64); }

const TOOL = process.env.INFISICAL_SETUP_PY
  || resolve(dirname(fileURLToPath(import.meta.url)), '../../tools/infisical_setup.py');
const PYTHON = process.env.PYTHON || 'python3';
const SECRET_URL = /\/api\/v\d+\/auth\/universal-auth\/identities\/[^/?#]+\/client-secrets(?:[?#]|$)/;
const WAIT_MS = mode === '--wait' ? 5 * 60_000 : 60_000;
const log = (...a) => console.log('[capture]', ...a);
const fail = (code, msg) => { console.error('[capture]', msg); process.exit(code); };

// --- attach ----------------------------------------------------------------------------------
let targets;
try { targets = await (await fetch(`${cdpUrl.replace(/\/$/, '')}/json/list`)).json(); }
catch { fail(3, `cannot reach CDP at ${cdpUrl}`); }
const page = process.env.CDP_TARGET_ID
  ? targets.find(t => t.id === process.env.CDP_TARGET_ID)
  : targets.find(t => t.type === 'page' && /infisical/i.test(t.url));
if (!page) fail(3, 'no Infisical tab found on that CDP endpoint');

const ws = new WebSocket(page.webSocketDebuggerUrl);
let seq = 0;
const pending = new Map();
const listeners = new Set();
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method) for (const fn of listeners) fn(m);
};
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error('ws error')); })
  .catch(() => fail(3, 'cannot open the tab websocket'));
const send = (method, params = {}) => new Promise((ok, no) => {
  const id = ++seq;
  pending.set(id, m => (m.error ? no(new Error(`${method}: ${m.error.message}`)) : ok(m.result)));
  ws.send(JSON.stringify({ id, method, params }));
});
const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result?.value;
log(`attached to tab ${page.id.slice(0, 8)} (${new URL(page.url).pathname})`);

// --- find the Create button of the open create-client-secret form ------------------------------
// Tags the button with data-capture-create so the click hits exactly what was checked. Reads only
// labels and field names; the secret does not exist yet at this point.
const FIND = `(() => {
  const dialogs = [...document.querySelectorAll('[role="dialog"]')].filter(d => d.offsetParent !== null || d.getClientRects().length);
  const scope = dialogs.at(-1) || document;
  const buttons = [...scope.querySelectorAll('button')].filter(b => b.getClientRects().length);
  const label = b => (b.innerText || b.textContent || '').trim().replace(/\\s+/g, ' ');
  let hits = buttons.filter(b => /^create$/i.test(label(b)));
  if (hits.length === 0) hits = buttons.filter(b => /^create\\b/i.test(label(b)) && b.type === 'submit');
  document.querySelectorAll('[data-capture-create]').forEach(b => b.removeAttribute('data-capture-create'));
  if (hits.length === 1) hits[0].setAttribute('data-capture-create', '1');
  const fields = [...scope.querySelectorAll('input')].map(i => i.name || i.placeholder || i.type).filter(Boolean);
  return { dialogs: dialogs.length, heading: (scope.querySelector('h1,h2,h3,[class*="title" i]')?.innerText || '').trim().slice(0, 80),
           matches: hits.length, label: hits[0] ? label(hits[0]) : null, disabled: hits[0]?.disabled ?? null, fields };
})()`;
const found = await evaluate(FIND);
log(`dialogs=${found.dialogs} heading="${found.heading}" create-buttons=${found.matches}` +
    (found.label ? ` label="${found.label}" disabled=${found.disabled}` : '') + ` fields=[${found.fields.join(', ')}]`);
if (mode === '--check') { ws.close(); process.exit(found.matches === 1 && !found.disabled ? 0 : 1); }
if (mode !== '--wait' && (found.matches !== 1 || found.disabled)) {
  ws.close(); fail(4, 'refusing to click: need exactly one enabled Create button in the open dialog');
}

// --- arm the network capture, then click ----------------------------------------------------
const methods = new Map();
let target = null;             // requestId of the POST we want
let status = 0;
const done = new Promise((ok, no) => {
  const timer = setTimeout(() => no(new Error('timeout')), WAIT_MS);
  listeners.add(m => {
    const p = m.params || {};
    if (m.method === 'Network.requestWillBeSent') methods.set(p.requestId, p.request.method);
    if (m.method === 'Network.responseReceived' && !target && SECRET_URL.test(p.response.url)
        && methods.get(p.requestId) === 'POST') {
      target = p.requestId; status = p.response.status;
    }
    if (m.method === 'Network.loadingFinished' && p.requestId === target) { clearTimeout(timer); ok(); }
    if (m.method === 'Network.loadingFailed' && p.requestId === target) { clearTimeout(timer); no(new Error('request failed')); }
  });
});
await send('Network.enable', { maxResourceBufferSize: 1 << 20, maxTotalBufferSize: 8 << 20 });

if (mode === '--wait') log(`armed; waiting up to ${WAIT_MS / 60000} min for Create to be clicked`);
else {
  const clicked = await evaluate(`(() => { const b = document.querySelector('[data-capture-create]'); if (!b) return false; b.click(); return true; })()`);
  if (!clicked) { ws.close(); fail(4, 'the Create button disappeared before the click'); }
  log('clicked Create');
}

try { await done; } catch (e) {
  ws.close(); fail(5, e.message === 'timeout' ? 'no client-secrets POST response seen' : 'the client-secrets POST failed in the browser');
}
if (status < 200 || status > 299) { ws.close(); fail(6, `client-secrets POST returned HTTP ${status}; nothing saved`); }

// --- read the body in memory, close the dialog, pipe to the save tool -------------------------
let secret = null;
try {
  const r = await send('Network.getResponseBody', { requestId: target });
  const json = JSON.parse(r.base64Encoded ? Buffer.from(r.body, 'base64').toString('utf8') : r.body);
  secret = typeof json.clientSecret === 'string' ? json.clientSecret : null;
} catch { secret = null; }
await send('Network.disable').catch(() => {});

// Close the "copy your secret" dialog at once so nothing later can screenshot or read it.
for (const type of ['keyDown', 'keyUp']) {
  await send('Input.dispatchKeyEvent', { type, key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }).catch(() => {});
}
await new Promise(r => setTimeout(r, 600));
const open = await evaluate(`document.querySelectorAll('[role="dialog"]').length`).catch(() => null);
log(`secret dialog closed: ${open === 0 ? 'yes' : `no (${open} dialog(s) still open, close it without reading it)`}`);
ws.close();

if (!secret) fail(7, 'response had no clientSecret field; nothing saved');
log(`created (HTTP ${status}); handing the pair to ${PYTHON} ${TOOL} save ${identity} --stdin`);

const child = spawn(PYTHON, [TOOL, 'save', identity, '--stdin'], { stdio: ['pipe', 'inherit', 'inherit'] });
child.stdin.end(`${clientId}\n${secret}\n`);
secret = null;
const code = await new Promise(r => { child.on('exit', c => r(c ?? 1)); child.on('error', () => r(127)); });
log(`save tool exit code ${code}`);
process.exit(code);
