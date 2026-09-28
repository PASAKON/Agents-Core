#!/usr/bin/env node
// Create ONE new API key on a provider's web page and hand it straight to Infisical, so that no
// person, no model, no screenshot and no log ever holds the value. Skill: CTO_Procedure_KeyFetch.
// Generalised from scripts/infisical/capture_client_secret.mjs (proven 2026-09-26).
//
//   node scripts/keyfetch/capture_key.mjs <cdp-url> --tab <url regex> --project <P> --env <dev|prod>
//        --name <VAR> [--comment "<purpose>"] [--meta k=v ...] [--as <identity>] [--multiline]
//        (wire)  --match <regex of the create request URL> [--method POST] --field <json.path>
//        (page)  --dom <css selector of the element that shows the new key>
//        [--click <button label regex>]   default: ^(create|generate|new|add)\b (in the open dialog)
//        [--wait]   do not click: a person clicks Create within 5 min (the script only listens)
//        [--check]  attach, find the tab and the button, print what was found, click nothing
//
// Where the value goes: `python3 tools/infisical_setup.py put <P> <env> <VAR> --stdin ...`.
// What this prints: its own status lines, the put tool's output (name · last4 · expires), exit
// codes. Never the response body, never the value, never its length.
//
// Exit codes: 64 usage · 3 cannot attach · 4 button not found / refused · 5 no response ·
// 6 provider answered non-2xx · 7 value not found in the response or the page · put's own code.
// Node 22+ (global WebSocket + fetch). Env: INFISICAL_SETUP_PY, PYTHON, CDP_TARGET_ID.
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// --- arguments --------------------------------------------------------------------------------
const argv = process.argv.slice(2);
const opts = { meta: [], method: 'POST', click: '^(create|generate|new|add)\\b', as: 'setup' };
const flags = new Set(['wait', 'check', 'multiline']);
let cdpUrl = null;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) { if (cdpUrl) usage(`unexpected argument ${a}`); cdpUrl = a; continue; }
  const key = a.slice(2);
  if (flags.has(key)) { opts[key] = true; continue; }
  const val = argv[++i];
  if (val === undefined) usage(`--${key} needs a value`);
  if (key === 'meta') opts.meta.push(val); else opts[key] = val;
}
function usage(msg) {
  console.error(`capture_key: ${msg}\nusage: capture_key.mjs <cdp-url> --tab <re> --project P --env E --name VAR (--match <re> --field <path> | --dom <css>) [--comment ..] [--meta k=v]... [--click <re>] [--wait] [--check]`);
  process.exit(64);
}
if (!cdpUrl) usage('missing <cdp-url>');
for (const k of ['tab', 'project', 'env', 'name']) if (!opts[k]) usage(`missing --${k}`);
if (!opts.check && !opts.dom && !(opts.match && opts.field)) usage('need --match + --field (wire) or --dom (page)');
if (!/^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$/.test(opts.name)) usage(`--name ${opts.name} is not UPPER_SNAKE_CASE (PLAN §4b; the put tool lints the KIND)`);
if (!/^(dev|prod)$/.test(opts.env)) usage('--env must be dev or prod');
if (/^org-infra$/i.test(opts.project)) usage('Org-Infra values are entered by the CEO only (PLAN §3b)');

const TOOL = process.env.INFISICAL_SETUP_PY
  || resolve(dirname(fileURLToPath(import.meta.url)), '../../tools/infisical_setup.py');
const PYTHON = process.env.PYTHON || 'python3';
const WAIT_MS = opts.wait ? 5 * 60_000 : 60_000;
const log = (...a) => console.log('[keyfetch]', ...a);
const fail = (code, msg) => { console.error('[keyfetch]', msg); process.exit(code); };
const re = (s, f = 'i') => { try { return new RegExp(s, f); } catch { usage(`bad regex ${s}`); } };
const TAB_RE = re(opts.tab), CLICK_RE = re(opts.click), MATCH_RE = opts.match ? re(opts.match) : null;

// --- attach ----------------------------------------------------------------------------------
let targets;
try { targets = await (await fetch(`${cdpUrl.replace(/\/$/, '')}/json/list`)).json(); }
catch { fail(3, `cannot reach CDP at ${cdpUrl}`); }
const page = process.env.CDP_TARGET_ID
  ? targets.find(t => t.id === process.env.CDP_TARGET_ID)
  : targets.find(t => t.type === 'page' && TAB_RE.test(t.url));
if (!page) fail(3, `no page tab matching /${opts.tab}/ on ${cdpUrl}`);

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
log(`attached to tab ${page.id.slice(0, 8)} (${new URL(page.url).host}${new URL(page.url).pathname})`);

// --- find the button (labels and field names only; the key does not exist yet) -----------------
const FIND = `((clickSrc) => {
  const clickRe = new RegExp(clickSrc, 'i');
  const visible = el => el.getClientRects().length > 0;
  const dialogs = [...document.querySelectorAll('[role="dialog"]')].filter(visible);
  const scope = dialogs.at(-1) || document;
  const label = b => (b.innerText || b.textContent || b.value || '').trim().replace(/\\s+/g, ' ');
  const buttons = [...scope.querySelectorAll('button, input[type="submit"], [role="button"]')].filter(visible);
  const hits = buttons.filter(b => clickRe.test(label(b)));
  document.querySelectorAll('[data-keyfetch-click]').forEach(b => b.removeAttribute('data-keyfetch-click'));
  if (hits.length === 1) hits[0].setAttribute('data-keyfetch-click', '1');
  const fields = [...scope.querySelectorAll('input, select')].map(i => i.name || i.placeholder || i.type).filter(Boolean).slice(0, 12);
  return { dialogs: dialogs.length, heading: (scope.querySelector('h1,h2,h3,[class*="title" i]')?.innerText || document.title || '').trim().slice(0, 80),
           matches: hits.length, labels: hits.slice(0, 5).map(label), disabled: hits[0]?.disabled ?? null, fields };
})(${JSON.stringify(opts.click)})`;
const found = await evaluate(FIND);
log(`dialogs=${found.dialogs} heading="${found.heading}" buttons=${found.matches} [${found.labels.join(' | ')}]` +
    (found.matches ? ` disabled=${found.disabled}` : '') + ` fields=[${found.fields.join(', ')}]`);
if (opts.check) { ws.close(); process.exit(found.matches === 1 && !found.disabled ? 0 : 1); }
if (!opts.wait && (found.matches !== 1 || found.disabled)) {
  ws.close(); fail(4, 'refusing to click: need exactly one enabled button matching --click in the open dialog or page');
}

// --- arm the capture, then click (or wait for a person to) ------------------------------------
let capture = null;
if (MATCH_RE) {
  const methods = new Map();
  let target = null;
  let status = 0;
  capture = new Promise((ok, no) => {
    const timer = setTimeout(() => no(new Error('timeout')), WAIT_MS);
    listeners.add(m => {
      const p = m.params || {};
      if (m.method === 'Network.requestWillBeSent') methods.set(p.requestId, p.request.method);
      if (m.method === 'Network.responseReceived' && !target && MATCH_RE.test(p.response.url)
          && methods.get(p.requestId) === opts.method.toUpperCase()) {
        target = p.requestId; status = p.response.status;
      }
      if (m.method === 'Network.loadingFinished' && p.requestId === target) { clearTimeout(timer); ok({ target, status }); }
      if (m.method === 'Network.loadingFailed' && p.requestId === target) { clearTimeout(timer); no(new Error('request failed')); }
    });
  });
  await send('Network.enable', { maxResourceBufferSize: 1 << 20, maxTotalBufferSize: 8 << 20 });
}
if (opts.wait) log(`armed; waiting up to ${WAIT_MS / 60000} min for a person to click`);
else {
  const clicked = await evaluate(`(() => { const b = document.querySelector('[data-keyfetch-click]'); if (!b) return false; b.click(); return true; })()`);
  if (!clicked) { ws.close(); fail(4, 'the button disappeared before the click'); }
  log('clicked');
}

// --- take the value: from the wire, or from the page ------------------------------------------
let value = null;
if (capture) {
  let hit;
  try { hit = await capture; } catch (e) {
    ws.close(); fail(5, e.message === 'timeout' ? `no ${opts.method} response matching /${opts.match}/ seen` : 'the create request failed in the browser');
  }
  if (hit.status < 200 || hit.status > 299) { ws.close(); fail(6, `provider answered HTTP ${hit.status}; nothing saved`); }
  try {
    const r = await send('Network.getResponseBody', { requestId: hit.target });
    let node = JSON.parse(r.base64Encoded ? Buffer.from(r.body, 'base64').toString('utf8') : r.body);
    for (const part of opts.field.split('.')) {
      const m = /^(.*?)(?:\[(\d+)\])?$/.exec(part);
      if (m[1]) node = node?.[m[1]];
      if (m[2] !== undefined) node = node?.[Number(m[2])];
    }
    value = typeof node === 'string' && node.length ? node : null;
  } catch { value = null; }
  await send('Network.disable').catch(() => {});
  log(`provider answered HTTP ${hit.status}; field ${opts.field}: ${value ? 'present' : 'MISSING'}`);
} else {
  const deadline = Date.now() + WAIT_MS;
  const READ = `((sel) => { const el = document.querySelector(sel); if (!el) return null;
    const v = (el.value ?? el.getAttribute('value') ?? el.innerText ?? el.textContent ?? '').trim(); return v || null; })(${JSON.stringify(opts.dom)})`;
  while (Date.now() < deadline && !value) {
    value = await evaluate(READ).catch(() => null);
    if (!value) await new Promise(r => setTimeout(r, 500));
  }
  if (value) await evaluate(`((sel) => { const el = document.querySelector(sel); if (el) { if ('value' in el) el.value = ''; el.textContent = ''; } })(${JSON.stringify(opts.dom)})`).catch(() => {});
  log(`page element ${opts.dom}: ${value ? 'read and blanked' : 'MISSING'}`);
}

// Close whatever dialog shows the key so nothing later can screenshot or read it.
for (const type of ['keyDown', 'keyUp']) {
  await send('Input.dispatchKeyEvent', { type, key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }).catch(() => {});
}
await new Promise(r => setTimeout(r, 600));
const open = await evaluate(`document.querySelectorAll('[role="dialog"]').length`).catch(() => null);
log(`dialogs still open: ${open ?? '?'}${open ? ' (close it without reading it)' : ''}`);
ws.close();
if (!value) fail(7, 'no value captured; nothing saved');

// --- hand it to the put tool on stdin; print only what the tool prints ------------------------
const args = [TOOL, 'put', opts.project, opts.env, opts.name, '--stdin', '--as', opts.as];
if (opts.comment) args.push('--comment', opts.comment);
for (const m of opts.meta) args.push('--meta', m);
if (opts.multiline) args.push('--multiline');
log(`handing the value to ${PYTHON} ${TOOL} put ${opts.project} ${opts.env} ${opts.name} --stdin`);
const child = spawn(PYTHON, args, { stdio: ['pipe', 'inherit', 'inherit'] });
child.stdin.end(value + '\n');
value = null;
const code = await new Promise(r => { child.on('exit', c => r(c ?? 1)); child.on('error', () => r(127)); });
log(`put exit code ${code}`);
process.exit(code);
