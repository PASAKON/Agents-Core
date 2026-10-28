#!/usr/bin/env node
// Replay: create ONE OpenRouter Management key and store it in Infisical, zero model.
// Skill CTO_Procedure_KeyFetch · flags and quirks: docs/ops/keyfetch/openrouter.md
//
//   node scripts/browser/keyfetch_openrouter_mgmt.mjs <cdp-url> [--check]
//
// Needs a Browser Home already logged in to openrouter.ai (relay-login) and the write identity
// `keyfetch-writer` in /etc/infisical (docs/ops/keyfetch/infisical-setup-identity.md). Fills the "Create a
// Management Key" dialog (name, expiration 90 days), then hands over to scripts/keyfetch/capture_key.mjs,
// which clicks Create, takes the key off the wire and pipes it into `infisical_setup.py put --stdin`.
// This script never reads, prints or logs a value. --check fills the form, clicks nothing.
// Selectors likely to break: the "New Key" button text, input[name=name], the "Select expiration"
// button and its role=option list ("90 days"), the dialog's "Create" button.
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const cdp = (process.argv[2] || 'http://127.0.0.1:9289').replace(/\/$/, '');
const CHECK = process.argv.includes('--check');
const NAME = process.env.KEY_NAME || 'ag-core-prod-admin-exp2027-01-12';
const EXPIRY_OPTION = process.env.KEY_EXPIRY_OPTION || '90 days';
const PAGE = 'https://openrouter.ai/settings/management-keys';
const log = (...a) => console.log('[openrouter-mgmt]', ...a);
const die = (c, m) => { console.error('[openrouter-mgmt]', m); process.exit(c); };

const tabs = await (await fetch(`${cdp}/json/list`)).json().catch(() => die(3, `cannot reach ${cdp}`));
const tab = tabs.find(t => t.type === 'page' && /openrouter\.ai/.test(t.url));
if (!tab) die(3, 'no openrouter.ai tab');
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(); }).catch(() => die(3, 'ws'));
let n = 0; const waiting = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } };
const send = (method, params = {}) => new Promise(r => { const id = ++n; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const realClick = async ([x, y]) => {
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1, buttons: 1 });
};
const centre = sel => ev(`(() => { const el = (${sel}); if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
const DIALOG = `[...document.querySelectorAll('[role=dialog]')].find(d => d.getClientRects().length)`;

try {
  if (!tab.url.startsWith(PAGE)) { await send('Page.navigate', { url: PAGE }); await sleep(4000); }
  const st = await ev(`document.body.innerText.includes('Management Keys') ? 'ok' : 'no'`);
  if (st !== 'ok') die(4, 'not on the Management Keys page (logged out?)');
  if (!(await ev(`!!${DIALOG}`))) {
    const nk = await centre(`[...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'New Key')`);
    if (!nk) die(4, 'no "New Key" button');
    await realClick(nk); await sleep(1200);
  }
  const set = await ev(`(() => { const i = (${DIALOG})?.querySelector('input[name=name]'); if (!i) return false;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, ${JSON.stringify(NAME)});
    i.dispatchEvent(new Event('input', { bubbles: true })); return i.value === ${JSON.stringify(NAME)}; })()`);
  if (!set) die(4, 'cannot set the key name');
  const sel = await centre(`[...(${DIALOG}).querySelectorAll('button')].find(b => /^(select expiration|\\d+ (hour|day|year)s?|no expiration)/i.test(b.innerText.trim()))`);
  if (!sel) die(4, 'no expiration select');
  await realClick(sel); await sleep(900);
  const opt = await centre(`[...document.querySelectorAll('[role=option]')].find(e => e.innerText.trim() === ${JSON.stringify(EXPIRY_OPTION)})`);
  if (!opt) die(4, `no expiration option "${EXPIRY_OPTION}"`);
  await realClick(opt); await sleep(900);
  log(`form filled: name set, expiration "${EXPIRY_OPTION}", ${await ev(`(${DIALOG}).innerText.match(/Key will expire on:[^\\n]*/)?.[0] || '?'`)}`);
} finally { ws.close(); }

const args = [resolve(ROOT, 'scripts/keyfetch/capture_key.mjs'), cdp,
  '--tab', 'openrouter\\.ai/settings/management-keys', '--project', 'Agents-Core', '--env', 'prod', '--path', '/spend-guard',
  '--as', 'keyfetch-writer', '--new-only', '--click', '^create$',
  '--match', 'keys', '--field', 'key|data.key|data.secret|secret|data.token|token|data.api_key|api_key=OPENROUTER_API_KEY_ADMIN',
  '--comment', 'spend guard: read credits + per-key usage, pause a key (tools/spend_guard.py)',
  '--meta', `provider_name=${NAME}`, '--meta', `console_url=${PAGE}`,
  '--meta', 'scope=management-keys-list-patch-credits', '--meta', 'expires=2027-01-12', '--meta', 'owner=CTO'];
if (CHECK) args.push('--check');
const child = spawn('/opt/node-v22/bin/node', args, { stdio: 'inherit', env: { ...process.env, INFISICAL_SETUP_PY: resolve(ROOT, 'tools/infisical_setup.py'), PYTHON: process.env.PYTHON || 'python3' } });
process.exit(await new Promise(r => child.on('exit', c => r(c ?? 1))));
