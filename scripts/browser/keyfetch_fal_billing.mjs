#!/usr/bin/env node
// Replay: create ONE fal.ai API key with the BILLING preset (read-only: usage, invoices, FOCUS reports)
// and store it in Infisical, zero model. Skill CTO_Procedure_KeyFetch · flags and quirks:
// docs/ops/keyfetch/fal.md
//
//   node scripts/browser/keyfetch_fal_billing.mjs <cdp-url> [--check] [--rotate]
//
// Needs a Browser Home already logged in to fal.ai (relay-login), the write identity `setup` in
// /etc/infisical, and the folder /spend-guard in Agents-Core prod. Fills the "Create API key" dialog
// (name, preset BILLING, expiration 1 year), then hands over to scripts/keyfetch/capture_key.mjs,
// which clicks "Create preset key", takes `key_id` + `key_secret` off the create response, joins
// them as `key_id:key_secret` (the form fal's Authorization header wants) and pipes the result into
// `infisical_setup.py put --stdin`. This script never reads, prints or logs a value.
// --check fills the form, clicks nothing.
// --rotate replaces an existing FAL_BILLING_API_KEY_RO (no --new-only). Revoke the old key at fal once
// tools/spend_guard.py reads the new one. The name (KEY_NAME, default one year from today, UTC) carries
// the exp date that expires= repeats.
// Selectors likely to break: the "Add key" button, the dialog's first <input> (name), the preset
// <label> text "Billing … 8 permissions" + button[role=radio][value=BILLING], the expiration button
// ("No expiration") and its role=option list, the "Create preset key" button.
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const cdp = (process.argv[2] || 'http://127.0.0.1:9290').replace(/\/$/, '');
const CHECK = process.argv.includes('--check');
const ROTATE = process.argv.includes('--rotate');
const inAYear = new Date(); inAYear.setUTCFullYear(inAYear.getUTCFullYear() + 1);
const NAME = process.env.KEY_NAME || `ag-core-prod-ro-exp${inAYear.toISOString().slice(0, 10)}`;
const EXPIRES = /-exp(\d{4}-\d{2}-\d{2})(?:-|$)/.exec(NAME)?.[1];
const EXPIRY_OPTION = process.env.KEY_EXPIRY_OPTION || '1 year';
const PAGE = 'https://fal.ai/dashboard/keys';
const log = (...a) => console.log('[fal-billing]', ...a);
const die = (c, m) => { console.error('[fal-billing]', m); process.exit(c); };
if (!EXPIRES) die(64, `KEY_NAME "${NAME}" carries no -expYYYY-MM-DD`);

const tabs = await (await fetch(`${cdp}/json/list`)).json().catch(() => die(3, `cannot reach ${cdp}`));
const tab = tabs.find(t => t.type === 'page' && /fal\.ai/.test(t.url));
if (!tab) die(3, 'no fal.ai tab');
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
const centre = sel => ev(`(() => { const el = (${sel}); if (!el) return null; el.scrollIntoView({ block: 'center' }); const r = el.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
const DIALOG = `[...document.querySelectorAll('[role=dialog]')].find(d => d.getClientRects().length)`;

try {
  if (!tab.url.startsWith(PAGE)) { await send('Page.navigate', { url: PAGE }); await sleep(5000); }
  if (!(await ev(`document.body.innerText.includes('API Keys')`))) die(4, 'not on the API Keys page (logged out?)');
  if (!(await ev(`!!${DIALOG}`))) {
    // a Radix button opens on pointerdown; the first "Add key" is the page header's
    const add = await centre(`[...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Add key')`);
    if (!add) die(4, 'no "Add key" button');
    await realClick(add); await sleep(1500);
  }
  const set = await ev(`(() => { const i = (${DIALOG})?.querySelector('input'); if (!i) return false;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, ${JSON.stringify(NAME)});
    i.dispatchEvent(new Event('input', { bubbles: true })); return i.value === ${JSON.stringify(NAME)}; })()`);
  if (!set) die(4, 'cannot set the key name');
  const preset = await centre(`[...(${DIALOG}).querySelectorAll('label')].find(l => /^billing\\s*8 permissions/i.test(l.innerText.trim()))`);
  if (!preset) die(4, 'no BILLING preset label');
  await realClick(preset); await sleep(800);
  const picked = await ev(`[...(${DIALOG}).querySelectorAll('button[role=radio]')].filter(b => b.getAttribute('aria-checked') === 'true').map(b => b.value).join(',')`);
  if (picked !== 'BILLING') die(4, `preset is "${picked}", not BILLING`);
  const sel = await centre(`[...(${DIALOG}).querySelectorAll('button')].find(b => /^(no expiration|\\d+ (hour|day|year)s?)$/i.test(b.innerText.trim()))`);
  if (!sel) die(4, 'no expiration select');
  await realClick(sel); await sleep(900);
  const opt = await centre(`[...document.querySelectorAll('[role=option]')].find(e => e.innerText.trim() === ${JSON.stringify(EXPIRY_OPTION)})`);
  if (!opt) die(4, `no expiration option "${EXPIRY_OPTION}"`);
  await realClick(opt); await sleep(900);
  const exp = await ev(`[...(${DIALOG}).querySelectorAll('button')].map(b => b.innerText.trim()).find(t => /^(no expiration|\\d+ (hour|day|year)s?)$/i.test(t))`);
  log(`form filled: name set, preset BILLING, expiration "${exp}"`);
} finally { ws.close(); }

const args = [resolve(ROOT, 'scripts/keyfetch/capture_key.mjs'), cdp,
  '--tab', 'fal\\.ai/dashboard/keys', '--project', 'Agents-Core', '--env', 'prod', '--path', '/spend-guard',
  '--as', 'setup', ...(ROTATE ? [] : ['--new-only']), '--click', '^create preset key',
  '--match', '/keys', '--field', 'key_id+key_secret=FAL_BILLING_API_KEY_RO',
  '--comment', 'spend guard: read credits + per-key usage, pause a key (tools/spend_guard.py)',
  '--meta', `provider_name=${NAME}`, '--meta', `console_url=${PAGE}`,
  '--meta', 'scope=BILLING-preset', '--meta', `expires=${EXPIRES}`, '--meta', 'owner=CTO'];
if (CHECK) args.push('--check');
const child = spawn('/opt/node-v22/bin/node', args, { stdio: 'inherit', env: { ...process.env, INFISICAL_SETUP_PY: resolve(ROOT, 'tools/infisical_setup.py'), PYTHON: process.env.PYTHON || 'python3' } });
process.exit(await new Promise(r => child.on('exit', c => r(c ?? 1))));
