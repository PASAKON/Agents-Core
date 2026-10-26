#!/usr/bin/env node
// CEO Run card ONLY, on Contabo, using his signed-in Infisical Browser Home.
// The card is the authorization boundary; this CLI does not authenticate card provenance.
import { readFile } from 'node:fs/promises';
import { checked, parseManifest, reconcileSeat, SeatError } from './keyfetch_writer_lib.mjs';

async function main() {
  const args = process.argv.slice(2);
  if (args.some(a => a !== '--go' && a !== 'http://127.0.0.1:9281')) throw new SeatError('usage: keyfetch_writer_seat.mjs [http://127.0.0.1:9281] [--go]');
  const projects = parseManifest(await readFile(new URL('../../config/keyfetch-writer.yaml', import.meta.url), 'utf8'));
  const pages = await (await fetch('http://127.0.0.1:9281/json/list')).json();
  // Use only the already signed-in organization page; never navigate or click tabs.
  const tab = pages.find(t => {
    try { const u = new URL(t.url); return t.type === 'page' && u.origin === 'https://app.infisical.com' && /^\/organizations\/[^/]+\//.test(u.pathname); }
    catch { return false; }
  });
  if (!tab) throw new SeatError('session: no signed-in Infisical organization tab');
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  let auth;
  try {
    await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new SeatError('session: websocket failed')); });
    auth = await new Promise((ok, no) => {
      const timer = setTimeout(() => no(new SeatError('session: refresh timed out')), 15000);
      ws.onmessage = ev => {
        try {
          const m = JSON.parse(ev.data);
          if (m.id !== 1) return;
          clearTimeout(timer);
          if (m.error || m.result?.exceptionDetails) no(new SeatError('session: refresh failed'));
          else ok(m.result?.result?.value);
        } catch { clearTimeout(timer); no(new SeatError('session: invalid response')); }
      };
      ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: {
        expression: "fetch('/api/v1/auth/token', { method: 'POST', credentials: 'include' }).then(async r => ({status:r.status,json:await r.json()}))",
        awaitPromise: true, returnByValue: true,
      } }));
    });
  } finally { ws.close(); }
  const body = await checked(async () => auth, 'session refresh', 'POST', '/api/v1/auth/token');
  let token = body?.token;
  if (typeof token !== 'string') throw new SeatError('session: token missing');
  const claims = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
  const orgId = claims.organizationId || body.organizationId;
  // Unlike the older scripts, require an already selected org, including in dry runs.
  if (!orgId || new URL(tab.url).pathname.split('/')[2] !== orgId) throw new SeatError('session: select the organization in Browser Home first');
  const api = async (method, path, payload) => {
    const r = await fetch('https://app.infisical.com' + path, {
      method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
    let json = null;
    try { json = await r.json(); } catch { /* checked() handles errors without raw bodies */ }
    return { status: r.status, json };
  };
  try { await reconcileSeat({ api, orgId, projects, go: args.includes('--go') }); }
  finally { token = null; }
}
main().catch(error => {
  console.error(error instanceof SeatError ? error.message : 'seat: failed; response details withheld');
  process.exitCode = 1;
});
