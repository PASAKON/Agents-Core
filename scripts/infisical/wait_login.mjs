// Poll a CDP endpoint until an app.infisical.com tab leaves the auth pages and shows the org UI.
// Prints host+path only (never query strings). Clicks nothing, types nothing.
//   node wait_login.mjs <cdp-url> [intervalSec=15] [maxMin=25] [--once]
const [cdp = 'http://127.0.0.1:9281', intervalArg = '15', maxArg = '25', onceFlag = ''] = process.argv.slice(2);
const INTERVAL = Number(intervalArg) * 1000;
const DEADLINE = Date.now() + Number(maxArg) * 60_000;
const ONCE = onceFlag === '--once';
const AUTH = /^\/(login|signup|signin|sign-up|verify-email|verify|signupinvite|requestnewinvite|password-reset|reset-password|email-not-verified|mfa|cli-redirect|select-org|select-organization|sso|saml|oidc|ldap|auth|account-recovery|org-not-found)(\/|$)/i;
const WORDS = ['Projects', 'Organization', 'Access Control', 'Secrets Management', 'Secret Management',
  'Identities', 'Members', 'App Connections', 'Audit Logs', 'Overview', 'Add New Project', 'New Project'];

const hp = u => { try { const x = new URL(u); return x.host + x.pathname; } catch { return String(u).split(/[?#]/)[0].slice(0, 60); } };

async function evalIn(t, expr) {
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error('ws error')); });
  const r = await new Promise((ok, no) => {
    const timer = setTimeout(() => no(new Error('eval timeout')), 8000);
    ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id === 1) { clearTimeout(timer); ok(m); } };
    ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true } }));
  });
  ws.close();
  return r.result?.result?.value;
}

let last = '';
let lastBeat = Date.now();
for (;;) {
  let pages = [];
  try { pages = (await (await fetch(`${cdp}/json/list`)).json()).filter(t => t.type === 'page'); }
  catch (e) { console.log(`[wait] ${new Date().toISOString().slice(11, 19)} cdp unreachable`); }
  const seen = pages.map(t => hp(t.url)).join(' | ');
  if (seen !== last) { console.log(`[wait] ${new Date().toISOString().slice(11, 19)} tabs: ${seen || '(none)'}`); last = seen; lastBeat = Date.now(); }
  else if (Date.now() - lastBeat > 5 * 60_000) { console.log(`[wait] ${new Date().toISOString().slice(11, 19)} still: ${seen}`); lastBeat = Date.now(); }

  for (const t of pages) {
    let u; try { u = new URL(t.url); } catch { continue; }
    if (u.host !== 'app.infisical.com') continue;
    if (u.pathname === '/' || AUTH.test(u.pathname)) continue;
    try {
      const hits = await evalIn(t, `(() => { const s = document.body ? document.body.innerText : ''; return ${JSON.stringify(WORDS)}.filter(w => s.includes(w)); })()`);
      console.log(`[wait] candidate ${t.id.slice(0, 8)} ${hp(t.url)} words=[${(hits || []).join(', ')}]`);
      if ((hits || []).length >= 2) { console.log(`[wait] LOGGED-IN tab=${t.id} at ${hp(t.url)}`); process.exit(0); }
    } catch (e) { console.log(`[wait] candidate ${hp(t.url)} eval failed: ${e.message}`); }
  }
  if (ONCE) {
    // prove the websocket path works on whatever infisical tab exists (reads document.title only)
    const any = pages.find(t => /infisical/.test(t.url));
    if (any) { try { console.log(`[wait] probe title="${await evalIn(any, 'document.title')}"`); } catch (e) { console.log(`[wait] probe failed: ${e.message}`); } }
    process.exit(3);
  }
  if (Date.now() > DEADLINE) { console.log(`relay-login: contabo:9281 — still on login (last: ${seen})`); process.exit(2); }
  await new Promise(r => setTimeout(r, INTERVAL));
}
