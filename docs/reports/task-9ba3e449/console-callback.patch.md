# MoonieX-Console Patch — Public `GET /tiktok/callback` for TikTok Login Kit v2 (`task-9ba3e449`)

**Target repository:** `MoonieX-Console` (`/opt/MoonieXHQ/Projects/MoonieX/Console`)  
**Do NOT apply from Agents-Core worker:** prepared for CTO review and application per task brief.

## Contract with `tools/tiktok_post.py` (Agents-Core)

1. `bash scripts/hub/org-python.sh tools/tiktok_post.py auth-url --account black_liquidity`
   writes `/opt/MoonieXHQ/Agents/Core/state/tiktok/pending-<state>.json` (`0600`) and prints the
   TikTok Login Kit v2 authorize URL with `redirect_uri=https://terminal.mooniex.com/tiktok/callback`.
2. After the user authorizes in the browser, TikTok redirects the browser to:
   `GET https://terminal.mooniex.com/tiktok/callback?code=<code>&scopes=<scopes>&state=<state>`
3. The public `GET /tiktok/callback` route in `MoonieX-Console`:
   - Must be reachable **without** operator passkey session cookie (or exempted in the public path allowlist, since TikTok redirects from `tiktok.com` and top-level cross-site navigation may or may not carry `SameSite=Strict` cookies).
   - Validates `state` against `/^[A-Za-z0-9_-]{16,64}$/` (strictly alphanumeric, `_`, `-`; prevents any path traversal).
   - Validates `code` is a non-empty string (`1..1024` chars, no control chars).
   - Verifies `/opt/MoonieXHQ/Agents/Core/state/tiktok/pending-<state>.json` exists (prevents unauthenticated callers from creating arbitrary `callback-*.json` files on disk unless a pending OAuth flow was started by `tools/tiktok_post.py`).
   - Atomically writes `{"state": "<state>", "code": "<code>"}\n` with mode `0600` to:
     `/opt/MoonieXHQ/Agents/Core/state/tiktok/callback-<state>.json`
   - Never logs `code`.
   - Sets `Cache-Control: no-store` and `Referrer-Policy: no-referrer` and returns an HTML page showing:
     `เชื่อมต่อสำเร็จ ปิดหน้านี้ได้`
4. `tools/tiktok_post.py exchange --state <state>` picks up `callback-<state>.json`, exchanges the code at `POST https://open.tiktokapis.com/v2/oauth/token/`, writes `tokens-<account>.json` (`0600`), and deletes `callback-<state>.json`.

---

## Suggested Module: `src/tiktok/callback.js`

```js
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const STATE_RE = /^[A-Za-z0-9_-]{16,64}$/;
const CODE_RE = /^[\x21-\x7e]{1,1024}$/;

const DEFAULT_AGENTS_CORE =
  process.env.RUN_INBOX_AGENTS_CORE || '/opt/MoonieXHQ/Agents/Core';
const DEFAULT_TIKTOK_STATE_DIR =
  process.env.TIKTOK_STATE_DIR || path.join(DEFAULT_AGENTS_CORE, 'state', 'tiktok');

function writeJson0600(filePath, payload) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const tmpPath = `${filePath}.tmp.${process.pid}.${Date.now()}`;
  const data = `${JSON.stringify(payload, null, 2)}\n`;
  const fd = fs.openSync(tmpPath, 'w', 0o600);
  try {
    fs.fchmodSync(fd, 0o600);
    fs.writeFileSync(fd, data, 'utf8');
  } finally {
    fs.closeSync(fd);
  }
  fs.chmodSync(tmpPath, 0o600);
  fs.renameSync(tmpPath, filePath);
  fs.chmodSync(filePath, 0o600);
}

function handleTikTokCallback(req, res, opts = {}) {
  const stateDir = opts.stateDir || DEFAULT_TIKTOK_STATE_DIR;
  const requirePending = opts.requirePending !== false;

  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Referrer-Policy', ' no-referrer'.trim());
  res.setHeader('X-Content-Type-Options', 'nosniff');

  const state = typeof req.query?.state === 'string' ? req.query.state : '';
  const code = typeof req.query?.code === 'string' ? req.query.code : '';
  const oauthError = typeof req.query?.error === 'string' ? req.query.error : '';

  if (!STATE_RE.test(state)) {
    res.status(400).type('text/plain; charset=utf-8').send('invalid_state');
    return;
  }

  if (oauthError) {
    res.status(400).type('text/plain; charset=utf-8').send('oauth_denied');
    return;
  }

  if (!CODE_RE.test(code)) {
    res.status(400).type('text/plain; charset=utf-8').send('invalid_code');
    return;
  }

  const pendingPath = path.join(stateDir, `pending-${state}.json`);
  if (requirePending && !fs.existsSync(pendingPath)) {
    res.status(404).type('text/plain; charset=utf-8').send('unknown_state');
    return;
  }

  const callbackPath = path.join(stateDir, `callback-${state}.json`);
  writeJson0600(callbackPath, { state, code });

  res
    .status(200)
    .type('text/html; charset=utf-8')
    .send(
      '<!doctype html><html lang="th"><head><meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<title>TikTok Connected</title></head>' +
        '<body style="font-family:system-ui,sans-serif;padding:2rem;text-align:center;">' +
        '<p>เชื่อมต่อสำเร็จ ปิดหน้านี้ได้</p>' +
        '</body></html>\n'
    );
}

module.exports = {
  STATE_RE,
  handleTikTokCallback,
  writeJson0600,
};
```

---

## Wiring in `MoonieX-Console` (`server.js` / Express app)

Register the public `GET /tiktok/callback` route before passkey auth middleware (or add `/tiktok/callback` to the public route allowlist):

```diff
+const { handleTikTokCallback } = require('./src/tiktok/callback');
+
+// Public OAuth redirect callback for TikTok Login Kit v2 (writes 0600 callback-<state>.json)
+app.get('/tiktok/callback', (req, res) => handleTikTokCallback(req, res));
```
