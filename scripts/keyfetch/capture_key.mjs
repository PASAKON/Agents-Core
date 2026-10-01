#!/usr/bin/env node
// Create ONE new API key on a provider's web page and hand it straight to Infisical, so that no
// person, no model, no screenshot and no log ever holds the value. Skill: CTO_Procedure_KeyFetch.
// Generalised from scripts/infisical/capture_client_secret.mjs (proven 2026-09-26).
//
//   node scripts/keyfetch/capture_key.mjs <cdp-url> --tab <url regex> --project <P> --env <dev|prod>
//        [--path /folder] [--comment "<purpose>"] [--meta k=v ...] [--as <identity>] [--multiline]
//        [--new-only]   refuse (exit 9) when any target secret already exists, BEFORE clicking
//        one value:   --name <VAR>  with a bare extractor
//        (wire)  --match <regex of the create request URL> [--method POST] --field <json.path>
//        (page)  --dom <css selector of the element that shows the new key>
//        several values from ONE create (a client id AND its secret): drop --name and repeat the
//        extractor as <src>=<VAR>, e.g.  --field id=TAILSCALE_OAUTH_CLIENT_ID --field key=TAILSCALE_OAUTH_CLIENT_SECRET
//        or  --dom 'input#cid=X_CLIENT_ID' --dom 'input#sec=X_CLIENT_SECRET'. Every value is captured
//        first; the puts run in the order given, each its own `put --stdin`.
//        [--click <button label regex>]   default: ^(create|generate|new|add)\b (in the open dialog)
//        [--wait]   do not click: a person clicks Create within 5 min (the script only listens)
//        [--check]  attach, find the tab and the button, print what was found, click nothing
//
// Where the value goes: `python3 tools/infisical_setup.py put <P> <env> <VAR> --stdin ...`.
// What this prints: its own status lines, the put tool's output (name · last4 · expires), exit
// codes. Never the response body, never the value, never its length.
//
// Exit codes: 64 usage · 3 cannot attach · 4 button not found / refused · 5 no response ·
// 6 provider answered non-2xx · 7 a value not found in the response or the page (nothing saved) ·
// 8 PARTIAL: some puts landed, one failed (the key exists at the provider: revoke it) ·
// 9 --new-only: a target secret already exists, or could not be checked (nothing clicked) ·
// otherwise put's own code (nothing saved).
// Node 22+ (global WebSocket + fetch). Env: INFISICAL_SETUP_PY, PYTHON, CDP_TARGET_ID.
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { UsageError, parseArgs, pickFields, runPuts, checkAbsent } from './keyfetch_lib.mjs';

// --- arguments --------------------------------------------------------------------------------
function usage(msg) {
  console.error(`capture_key: ${msg}\nusage: capture_key.mjs <cdp-url> --tab <re> --project P --env E [--path /folder] (--name VAR | <src>=<VAR> per value) (--match <re> --field <path> | --dom <css>) [--comment ..] [--meta k=v]... [--click <re>] [--new-only] [--wait] [--check]`);
  process.exit(64);
}
let parsed;
try { parsed = parseArgs(process.argv.slice(2)); }
catch (e) { if (e instanceof UsageError) usage(e.message); throw e; }
const { opts, cdpUrl, extractors, mode } = parsed;

const TOOL = process.env.INFISICAL_SETUP_PY
  || resolve(dirname(fileURLToPath(import.meta.url)), '../../tools/infisical_setup.py');
const PYTHON = process.env.PYTHON || 'python3';
const WAIT_MS = Number(process.env.KEYFETCH_WAIT_MS) || (opts.wait ? 5 * 60_000 : 60_000);   // env: tests only
const log = (...a) => console.log('[keyfetch]', ...a);
const fail = (code, msg) => { console.error('[keyfetch]', msg); process.exit(code); };
const re = (s, f = 'i') => { try { return new RegExp(s, f); } catch { usage(`bad regex ${s}`); } };
const TAB_RE = re(opts.tab), CLICK_RE = re(opts.click), MATCH_RE = opts.match ? re(opts.match) : null;
const putCfg = {
  python: PYTHON, tool: TOOL, project: opts.project, env: opts.env, path: opts.path, as: opts.as,
  comment: opts.comment, meta: opts.meta, multiline: !!opts.multiline,
};
const where = `${opts.project}/${opts.env}${opts.path === '/' ? '' : opts.path}`;
const names = extractors.map(e => e.name);

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

// --- --new-only: nothing is created at the provider while a target secret already exists --------
if (opts['new-only']) {
  const { present, error } = await checkAbsent(names, putCfg);
  if (present.length || error.length) {
    ws.close();
    fail(9, `--new-only: ${present.length ? `already in ${where}: ${present.join(', ')}` : ''}` +
            `${present.length && error.length ? '; ' : ''}${error.length ? `could not check: ${error.join(', ')}` : ''}; nothing clicked`);
  }
  log(`--new-only: ${names.join(', ')} absent in ${where}`);
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

// --- take the values: from the wire, or from the page -----------------------------------------
let entries = [], missing = names;
if (mode === 'wire') {
  let hit;
  try { hit = await capture; } catch (e) {
    ws.close(); fail(5, e.message === 'timeout' ? `no ${opts.method} response matching /${opts.match}/ seen` : 'the create request failed in the browser');
  }
  if (hit.status < 200 || hit.status > 299) { ws.close(); fail(6, `provider answered HTTP ${hit.status}; nothing saved`); }
  try {
    const r = await send('Network.getResponseBody', { requestId: hit.target });
    ({ entries, missing } = pickFields(JSON.parse(r.base64Encoded ? Buffer.from(r.body, 'base64').toString('utf8') : r.body), extractors));
  } catch { /* the whole body is unreadable: every name stays missing */ }
  await send('Network.disable').catch(() => {});
  log(`provider answered HTTP ${hit.status}; ${names.map(n => `${n}: ${missing.includes(n) ? 'MISSING' : 'present'}`).join(' · ')}`);
} else {
  // Page mode waits until EVERY element shows a value: two fields rarely paint in the same tick.
  const sels = extractors.map(e => e.src);
  const READ = `((sels) => sels.map(sel => { const el = document.querySelector(sel); if (!el) return null;
    const v = (el.value ?? el.getAttribute('value') ?? el.innerText ?? el.textContent ?? '').trim(); return v || null; }))(${JSON.stringify(sels)})`;
  const deadline = Date.now() + WAIT_MS;
  let got = [];
  while (Date.now() < deadline) {
    got = (await evaluate(READ).catch(() => null)) || [];
    if (got.length === sels.length && got.every(Boolean)) break;
    await new Promise(r => setTimeout(r, 500));
  }
  entries = extractors.flatMap((e, i) => (got[i] ? [{ name: e.name, value: got[i] }] : []));
  missing = names.filter(n => !entries.some(e => e.name === n));
  got = [];
  await evaluate(`((sels) => sels.forEach(sel => { const el = document.querySelector(sel); if (el) { if ('value' in el) el.value = ''; el.textContent = ''; } }))(${JSON.stringify(sels)})`).catch(() => {});
  log(`page elements: ${names.map(n => `${n}: ${missing.includes(n) ? 'MISSING' : 'read and blanked'}`).join(' · ')}`);
}

// Close whatever dialog shows the key so nothing later can screenshot or read it.
for (const type of ['keyDown', 'keyUp']) {
  await send('Input.dispatchKeyEvent', { type, key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }).catch(() => {});
}
await new Promise(r => setTimeout(r, 600));
const open = await evaluate(`document.querySelectorAll('[role="dialog"]').length`).catch(() => null);
log(`dialogs still open: ${open ?? '?'}${open ? ' (close it without reading it)' : ''}`);
ws.close();
// Both-or-nothing: one value missing means no put at all, so Infisical never holds half a pair.
if (missing.length) fail(7, `no value captured for ${missing.join(', ')}; nothing saved`);

// --- hand each value to the put tool on stdin; print only what the tool prints ----------------
log(`handing ${names.length} value(s) to ${PYTHON} ${TOOL} put ${where}: ${names.join(', ')} (--stdin)`);
const res = await runPuts(entries, putCfg);
entries = [];
log(`put exit code ${res.code}`);
if (res.code === 0) { log(`saved ${res.saved.length}/${names.length}: ${res.saved.join(', ')}`); process.exit(0); }
if (res.saved.length) {
  console.error(`[keyfetch] PARTIAL: saved ${res.saved.join(', ')}; ${res.failed} FAILED${res.skipped.length ? `; not attempted ${res.skipped.join(', ')}` : ''}. ` +
                'The key EXISTS at the provider: revoke it there (or rerun the failed put by hand), do not leave a half pair.');
  process.exit(8);
}
console.error(`[keyfetch] nothing saved (${res.failed} failed); the key EXISTS at the provider: revoke it there and rerun.`);
process.exit(res.code);
