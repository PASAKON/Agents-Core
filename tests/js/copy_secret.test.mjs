// find tests/js -name 'copy_secret.test.mjs' | xargs node --experimental-websocket --test
// scripts/infisical/copy_secret.mjs against a fake CDP browser and a fake Infisical, both on 127.0.0.1:
// no Chrome, no Infisical, no real value. Every run asserts that the fake value, its last 4 characters
// and the session token never reach stdout or stderr — including error bodies that echo the value.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = resolve(HERE, '../../scripts/infisical/copy_secret.mjs');
const NODE_FLAGS = Number(process.versions.node.split('.')[0]) < 22 ? ['--experimental-websocket'] : [];

const VALUE = 'fal-TESTONLY-not-a-key-0000-Q7zX';      // synthetic, never a real credential
const OTHER = 'cf-TESTONLY-other-value-8888-Wv3K';
const jwt = (claims) => ['e30', Buffer.from(JSON.stringify(claims)).toString('base64url'), 'sig'].join('.');
const TOKEN = jwt({ organizationId: 'org-1111aaaa', marker: 'browser' });
const TOKEN_NO_ORG = jwt({ marker: 'no-org' });
const TOKEN_SELECTED = jwt({ organizationId: 'org-1111aaaa', marker: 'selected' });
const NEVER_PRINTED = [VALUE, VALUE.slice(-4), OTHER, OTHER.slice(-4), TOKEN, TOKEN_NO_ORG, TOKEN_SELECTED];

const FROM = ['--from', 'Org-Infra:prod:^FAL'];
const TO = ['--to', 'MoonieX-Bedrock:prod:FAL_API_KEY'];
const META = ['--comment', 'Lumina Skies sound gen', '--meta', 'provider_name=fal', '--meta', 'console_url=https://fal.ai/dashboard/keys',
  '--meta', 'scope=as-source', '--meta', 'expires=as-source'];
const REAL = [...FROM, ...TO, ...META];
const s = (secretKey, secretValue, type = 'shared') => ({ id: `id-${secretKey}`, secretKey, secretValue, type });
const ONE_FAL = {
  '/': [s('CLOUDFLARE_DNS_MAC_TOKEN_RW', OTHER)],
  '/dns': [s('CLOUDFLARE_DNS_CONTABO_TOKEN_RW', OTHER)],
  '/deploy': [s('FAL_DEPLOY_MAC_API_KEY', VALUE), s('VERCEL_DEPLOY_MAC_TOKEN_RW', OTHER)],
  '/repo': [], '/net': [], '/db': [],
  // '/vault' absent -> the fake answers 404, which counts as an empty folder
};

// ------------------------------------------------------------------ fake CDP browser (same framing as tests/keyfetch)
function frame(text) {
  const b = Buffer.from(text);
  const head = b.length < 126 ? Buffer.from([0x81, b.length])
    : b.length < 65536 ? Buffer.from([0x81, 126, b.length >> 8, b.length & 255])
    : (() => { const h = Buffer.alloc(10); h[0] = 0x81; h[1] = 127; h.writeBigUInt64BE(BigInt(b.length), 2); return h; })();
  return Buffer.concat([head, b]);
}
function* readFrames(state, chunk) {
  state.buf = Buffer.concat([state.buf, chunk]);
  for (;;) {
    const buf = state.buf;
    if (buf.length < 2) return;
    let len = buf[1] & 127, off = 2;
    if (len === 126) { if (buf.length < 4) return; len = buf.readUInt16BE(2); off = 4; }
    else if (len === 127) { if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); off = 10; }
    const masked = (buf[1] & 128) !== 0;
    if (buf.length < off + (masked ? 4 : 0) + len) return;
    const mask = masked ? buf.subarray(off, off + 4) : null;
    const data = Buffer.from(buf.subarray(off + (masked ? 4 : 0), off + (masked ? 4 : 0) + len));
    if (mask) for (let i = 0; i < data.length; i++) data[i] ^= mask[i % 4];
    state.buf = buf.subarray(off + (masked ? 4 : 0) + len);
    if ((buf[0] & 15) === 8) return;
    yield data.toString('utf8');
  }
}

// opts: { path: the tab's pathname, auth: what the in-page token fetch returns }
async function fakeBrowser({ path = '/org/org-1111aaaa/secret-manager', auth = { status: 200, body: { token: TOKEN } } } = {}) {
  const hits = { list: 0, evals: [] };
  const server = createServer((req, res) => {
    if (req.url === '/json/list') {
      hits.list++;
      const { port } = server.address();
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify([
        { id: 'BLANK0000', type: 'page', url: 'about:blank', webSocketDebuggerUrl: `ws://127.0.0.1:${port}/devtools/page/0` },
        { id: 'TAB0123456789', type: 'page', url: `https://app.infisical.com${path}`, webSocketDebuggerUrl: `ws://127.0.0.1:${port}/devtools/page/1` },
      ]));
    } else { res.statusCode = 404; res.end(); }
  });
  server.on('upgrade', (req, sock) => {
    const accept = createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    sock.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
    const state = { buf: Buffer.alloc(0) };
    sock.on('error', () => {});
    sock.on('data', (chunk) => {
      for (const text of readFrames(state, chunk)) {
        const m = JSON.parse(text);
        let result = {};
        if (m.method === 'Runtime.evaluate') {
          hits.evals.push(m.params.expression);
          result = { result: { value: m.params.expression.includes('/api/v1/auth/token') ? auth : null } };
        }
        sock.write(frame(JSON.stringify({ id: m.id, result })));
      }
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  return { url: `http://127.0.0.1:${server.address().port}`, hits, close: () => server.close() };
}

// ------------------------------------------------------------------ fake Infisical
// world: { folders, folderStatus: {path: status}, targetExists, writeStatus, corrupt }
// --find worlds: { projects, tree: {'<pid>|<env>': folders}, status: {'<pid>|<env>|<path>|folders|secrets': s},
//                  projectStatus: {'<pid>': s}, limited: {'<pid>|<env>|<path>': n 429s first} }
async function fakeInfisical(world = {}) {
  const calls = [];
  const folders = world.folders ?? ONE_FAL;
  const store = new Map();
  if (world.targetExists) store.set('p-bed|prod|/|FAL_API_KEY', { secretKey: 'FAL_API_KEY', secretValue: OTHER, secretMetadata: [] });
  const projects = world.projects ?? [
    { id: 'p-infra', name: 'Org-Infra', slug: 'org-infra', environments: [{ slug: 'prod', name: 'Production', id: 'e1' }] },
    { id: 'p-bed', name: 'MoonieX-Bedrock', slug: 'mooniex-bedrock-x1y2', environments: [{ slug: 'dev', name: 'Development', id: 'e2' }, { slug: 'prod', name: 'Production', id: 'e3' }] },
  ];
  const treeOf = (pid, env) => (world.tree ? world.tree[`${pid}|${env}`] : pid === 'p-infra' && env === 'prod' ? folders : undefined);
  const limited = { ...(world.limited || {}) };
  const server = createServer(async (req, res) => {
    const u = new URL(req.url, 'http://fake');
    let raw = ''; for await (const c of req) raw += c;
    const body = raw ? JSON.parse(raw) : null;
    const q = Object.fromEntries(u.searchParams);
    calls.push({ method: req.method, path: u.pathname, query: q, body, auth: req.headers.authorization });
    const send = (status, obj) => { res.statusCode = status; res.setHeader('content-type', 'application/json'); res.end(JSON.stringify(obj)); };
    const bearer = req.headers.authorization;
    if (![TOKEN, TOKEN_NO_ORG, TOKEN_SELECTED].some((t) => bearer === `Bearer ${t}`)) return send(401, { message: 'unauthorized', error: 'Unauthorized' });
    const withOrg = bearer !== `Bearer ${TOKEN_NO_ORG}`;
    const one = u.pathname.match(/^\/api\/v3\/secrets\/raw\/([A-Z0-9_]+)$/);
    if (req.method === 'GET' && u.pathname === '/api/v1/organization') return send(200, { organizations: [{ id: 'org-other', name: 'Someone' }, { id: 'org-1111aaaa', name: 'MoonieX' }] });
    if (req.method === 'POST' && u.pathname === '/api/v3/auth/select-organization') return send(200, { token: TOKEN_SELECTED });
    if (!withOrg) return send(403, { message: 'select an organization first', error: 'Forbidden' });
    if (req.method === 'GET' && u.pathname === '/api/v2/organizations/org-1111aaaa/workspaces') return send(200, { workspaces: projects });
    const proj = u.pathname.match(/^\/api\/v1\/projects\/([\w-]+)$/);
    if (req.method === 'GET' && proj) {
      if (world.projectStatus?.[proj[1]]) return send(world.projectStatus[proj[1]], { message: `denied ${VALUE}`, error: 'Forbidden' });
      const p = projects.find((x) => x.id === proj[1]);
      return p ? send(200, { project: { ...p, environments: p.envs ?? [] } }) : send(404, { message: 'no project', error: 'NotFound' });
    }
    if (req.method === 'GET' && (u.pathname === '/api/v2/folders' || u.pathname === '/api/v3/secrets/raw')) {
      const lk = `${q.projectId ?? q.workspaceId}|${q.environment}|${q.path ?? q.secretPath}`;
      if (limited[lk] > 0) { limited[lk]--; res.setHeader('retry-after', '0'); return send(429, { message: `slow down ${VALUE}`, error: 'TooManyRequests' }); }
      const st = world.status?.[`${lk}|${u.pathname === '/api/v2/folders' ? 'folders' : 'secrets'}`];
      if (st) return send(st, { message: `denied while reading ${VALUE}`, error: 'Forbidden' });
    }
    if (req.method === 'GET' && u.pathname === '/api/v2/folders') {
      if (world.foldersStatus) return send(world.foldersStatus, { message: 'denied', error: 'Forbidden' });
      const tree = treeOf(q.projectId, q.environment);
      if (!tree) return send(404, { message: 'no such env', error: 'NotFound' });
      const base = q.path === '/' ? '' : q.path;
      const kids = Object.keys(tree).filter((k) => k !== '/' && k.startsWith(`${base}/`) && !k.slice(base.length + 1).includes('/'));
      return send(200, { folders: kids.map((k) => ({ id: `f${k}`, name: k.slice(base.length + 1) })) });
    }
    if (req.method === 'GET' && u.pathname === '/api/v3/secrets/raw') {
      const tree = treeOf(q.workspaceId, q.environment);
      if (!tree) return send(404, { message: 'no such env', error: 'NotFound' });
      const status = world.folderStatus?.[q.secretPath];
      if (status) return send(status, { message: `denied while reading ${VALUE}`, error: 'Forbidden' });
      if (!tree[q.secretPath]) return send(404, { message: `Folder with path '${q.secretPath}' not found`, error: 'NotFound' });
      return send(200, { secrets: tree[q.secretPath], imports: [] });
    }
    if (one) {
      const key = `${q.workspaceId}|${q.environment ?? body?.environment}|${q.secretPath ?? body?.secretPath}|${one[1]}`;
      if (req.method === 'GET') {
        const hit = store.get(key);
        return hit ? send(200, { secret: hit }) : send(404, { statusCode: 404, message: `Secret with name '${one[1]}' not found`, error: 'NotFound' });
      }
      if (req.method === 'POST') {
        const k = `${body.workspaceId}|${body.environment}|${body.secretPath}|${one[1]}`;
        if (world.writeStatus) return send(world.writeStatus, { message: `secretValue '${body.secretValue}' rejected`, error: 'BadRequest' });
        if (store.has(k)) return send(400, { message: 'already exists', error: 'BadRequest' });
        store.set(k, { secretKey: one[1], secretValue: world.corrupt ? OTHER : body.secretValue, secretComment: body.secretComment, secretMetadata: body.secretMetadata });
        return send(200, { secret: { secretKey: one[1] } });
      }
    }
    send(404, { message: 'no route', error: 'NotFound' });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  return { url: `http://127.0.0.1:${server.address().port}`, calls, store, close: () => server.close() };
}

async function run(args, { browser, world, env = {}, cdp } = {}) {
  const b = await fakeBrowser(browser);
  const inf = await fakeInfisical(world);
  const child = spawn(process.execPath, [...NODE_FLAGS, SCRIPT, cdp ?? b.url, ...args], {
    env: { ...process.env, INFISICAL_API_URL: inf.url, CTO_SESSION_ID: '', CXO_SESSION_ID: '', ORG_TASK_ID: 'task-test0001', ...env },
  });
  let text = '', out = '', err = '';
  child.stdout.on('data', (d) => { text += d; out += d; });
  child.stderr.on('data', (d) => { text += d; err += d; });
  const code = await new Promise((r) => child.on('close', (c) => r(c)));
  b.close(); inf.close();
  NEVER_PRINTED.forEach((x, i) => assert.ok(!text.includes(x), `forbidden string #${i} reached the output`));
  const writes = inf.calls.filter((c) => c.method === 'POST' && c.path.startsWith('/api/v3/secrets/raw'));
  return { code, text, out, err, calls: inf.calls, writes, store: inf.store, cdpHits: b.hits };
}

// ------------------------------------------------------------------ the five required cases

test('one match: writes once at / with source, comment and metadata, verifies MATCH, exit 0', async () => {
  const r = await run(REAL);
  assert.equal(r.code, 0, r.text);
  assert.equal(r.writes.length, 1);
  const w = r.writes[0];
  assert.equal(w.path, '/api/v3/secrets/raw/FAL_API_KEY');
  assert.equal(w.auth, `Bearer ${TOKEN}`);
  assert.deepEqual({ ws: w.body.workspaceId, env: w.body.environment, path: w.body.secretPath, type: w.body.type },
    { ws: 'p-bed', env: 'prod', path: '/', type: 'shared' });
  assert.ok(w.body.secretValue === VALUE, 'the source value was not the one written');
  assert.equal(w.body.secretComment, 'Lumina Skies sound gen');
  const md = Object.fromEntries(w.body.secretMetadata.map((m) => [m.key, m.value]));
  assert.match(md.created, /^\d{4}-\d{2}-\d{2} task-test0001$/);
  delete md.created;
  assert.deepEqual(md, {
    provider_name: 'fal', console_url: 'https://fal.ai/dashboard/keys', scope: 'as-source', expires: 'as-source',
    source: 'Org-Infra/prod/deploy/FAL_DEPLOY_MAC_API_KEY', rotate_with: 'source', owner: 'CTO', status: 'active',
  });
  const listed = r.calls.filter((c) => c.path === '/api/v3/secrets/raw').map((c) => c.query.secretPath);
  assert.deepEqual(listed, ['/', '/dns', '/deploy', '/repo', '/net', '/db', '/vault']);
  assert.match(r.text, /source match: Org-Infra\/prod\/deploy\/FAL_DEPLOY_MAC_API_KEY \(exactly one\)/);
  assert.match(r.text, /target MoonieX-Bedrock\/prod FAL_API_KEY: absent \(HTTP 404\)/);
  assert.match(r.text, /verify MoonieX-Bedrock\/prod FAL_API_KEY: HTTP 200 · MATCH$/m);
  assert.ok(!/MISMATCH/.test(r.text));
});

test('zero matches: exit 8, nothing written', async () => {
  const r = await run(REAL, { world: { folders: { '/': [s('CLOUDFLARE_DNS_MAC_TOKEN_RW', OTHER)], '/deploy': [s('VERCEL_DEPLOY_MAC_TOKEN_RW', OTHER)] } } });
  assert.equal(r.code, 8, r.text);
  assert.equal(r.writes.length, 0);
  assert.match(r.text, /0 names match \/\^FAL\/ — need exactly one; nothing written/);
});

test('two matches (two folders): exit 8, both names printed, nothing written, target never queried', async () => {
  const r = await run(REAL, { world: { folders: { ...ONE_FAL, '/vault': [s('FAL_VAULT_MAC_API_KEY', OTHER)] } } });
  assert.equal(r.code, 8, r.text);
  assert.equal(r.writes.length, 0);
  assert.match(r.text, /match: Org-Infra\/prod\/deploy FAL_DEPLOY_MAC_API_KEY/);
  assert.match(r.text, /match: Org-Infra\/prod\/vault FAL_VAULT_MAC_API_KEY/);
  assert.match(r.text, /2 names match/);
  assert.ok(!r.calls.some((c) => c.path === '/api/v3/secrets/raw/FAL_API_KEY'));
});

test('target exists: exit 9, refuses, nothing written, the existing value untouched', async () => {
  const r = await run(REAL, { world: { targetExists: true } });
  assert.equal(r.code, 9, r.text);
  assert.equal(r.writes.length, 0);
  assert.ok(r.store.get('p-bed|prod|/|FAL_API_KEY').secretValue === OTHER);
  assert.match(r.text, /already exists \(HTTP 200\); refusing to overwrite/);
});

test('Org-Infra target: refused (exit 64) before the browser or the API is touched', async () => {
  for (const to of ['Org-Infra:prod:FAL_API_KEY', 'org-infra:prod:FAL_API_KEY']) {
    const r = await run([...FROM, '--to', to, ...META]);
    assert.equal(r.code, 64, r.text);
    assert.match(r.text, /Org-Infra is never a target/);
    assert.equal(r.cdpHits.list, 0, 'the browser was contacted');
    assert.equal(r.calls.length, 0, 'the API was contacted');
  }
});

// ------------------------------------------------------------------ the rest of the contract

test('--dry: prints the match and the absent target, writes nothing, needs no --comment', async () => {
  const r = await run([...FROM, ...TO, '--dry']);
  assert.equal(r.code, 0, r.text);
  assert.equal(r.writes.length, 0);
  assert.match(r.text, /source match: Org-Infra\/prod\/deploy\/FAL_DEPLOY_MAC_API_KEY \(exactly one\)/);
  assert.match(r.text, /absent \(HTTP 404\)/);
  assert.match(r.text, /dry run: stopping before any write/);
});

test('the read-back differs: MISMATCH, exit 12', async () => {
  const r = await run(REAL, { world: { corrupt: true } });
  assert.equal(r.code, 12, r.text);
  assert.match(r.text, /· MISMATCH$/m);
});

test('an unreadable source folder refuses (exit 7) and its error body, which echoes the value, is never printed', async () => {
  const r = await run(REAL, { world: { folderStatus: { '/net': 403 } } });
  assert.equal(r.code, 7, r.text);
  assert.equal(r.writes.length, 0);
  assert.match(r.text, /cannot list Org-Infra\/prod\/net \(HTTP 403\)/);
});

test('a failed write: exit 11, status and error class only, never the echoing body', async () => {
  const r = await run(REAL, { world: { writeStatus: 422 } });
  assert.equal(r.code, 11, r.text);
  assert.match(r.text, /failed \(HTTP 422 BadRequest\)/);
  assert.ok(!r.text.includes('rejected'));
});

test('signed out: a /login tab, or a 401 token refresh, is exit 4 and nothing reaches the API', async () => {
  let r = await run(REAL, { browser: { path: '/login' } });
  assert.equal(r.code, 4, r.text);
  assert.match(r.text, /\(2 tab\(s\), 1 on app\.infisical\.com\)/);
  assert.doesNotMatch(r.text, /\/login/, 'a tab path can carry a capability token: count only');
  assert.equal(r.cdpHits.evals.length, 0);
  assert.equal(r.calls.length, 0);
  r = await run(REAL, { browser: { auth: { status: 401, body: null } } });
  assert.equal(r.code, 4, r.text);
  assert.match(r.text, /signed out/);
  assert.equal(r.calls.length, 0);
});

test('the borrow is one in-page fetch; a token without an org selects MoonieX and uses the new token', async () => {
  const r = await run(REAL, { browser: { auth: { status: 200, body: { token: TOKEN_NO_ORG } } } });
  assert.equal(r.code, 0, r.text);
  assert.equal(r.cdpHits.evals.length, 1);
  assert.match(r.cdpHits.evals[0], /fetch\('\/api\/v1\/auth\/token', \{ method: 'POST', credentials: 'include' \}\)/);
  assert.equal(r.calls.find((c) => c.path === '/api/v3/auth/select-organization').body.organizationId, 'org-1111aaaa');
  assert.equal(r.writes[0].auth, `Bearer ${TOKEN_SELECTED}`);
  assert.match(r.text, /organization selected: MoonieX/);
});

test('a key in a nested folder outside the §3b list is found by the folder walk', async () => {
  const r = await run(REAL, { world: { folders: { '/': [], '/dns': [], '/api': [], '/api/fal': [s('FAL_API_KEY_ADMIN', VALUE)] } } });
  assert.equal(r.code, 0, r.text);
  assert.equal(r.writes.length, 1);
  const md = Object.fromEntries(r.writes[0].body.secretMetadata.map((m) => [m.key, m.value]));
  assert.equal(md.source, 'Org-Infra/prod/api/fal/FAL_API_KEY_ADMIN');
  assert.match(r.text, /outside the §3b list: \/api \/api\/fal/);
  const listed = r.calls.filter((c) => c.path === '/api/v3/secrets/raw').map((c) => c.query.secretPath);
  assert.deepEqual(listed, ['/', '/dns', '/api', '/api/fal', '/deploy', '/repo', '/net', '/db', '/vault']);
});

test('a folder tree that cannot be read refuses (exit 7), nothing written', async () => {
  const r = await run(REAL, { world: { foldersStatus: 403 } });
  assert.equal(r.code, 7, r.text);
  assert.equal(r.writes.length, 0);
  assert.match(r.text, /cannot list the folders of Org-Infra\/prod \(HTTP 403\)/);
});

test('zero matches name the source environments, so a key in the wrong env is visible', async () => {
  const r = await run(REAL, { world: { folders: { '/': [] } } });
  assert.equal(r.code, 8, r.text);
  assert.match(r.text, /source project Org-Infra has environments: prod/);
});

test('personal secrets do not count as matches', async () => {
  const r = await run(REAL, { world: { folders: { ...ONE_FAL, '/': [s('FAL_PERSONAL_API_KEY', OTHER, 'personal')] } } });
  assert.equal(r.code, 0, r.text);
  assert.equal(r.writes.length, 1);
});

test('usage refusals exit 64 before the browser is touched', async () => {
  const cases = [
    [[...FROM, ...TO, '--comment', 'x'], /--meta provider_name=… console_url=… scope=… expires=…/],
    [[...FROM, ...TO, '--meta', 'provider_name=fal', '--meta', 'console_url=u', '--meta', 'scope=s', '--meta', 'expires=e'], /needs --comment/],
    [[...REAL, '--meta', 'owner=CEO'], /--meta owner is set by this script/],
    [[...REAL, '--meta', 'source=elsewhere'], /--meta source is set by this script/],
    [[...REAL, '--meta', 'scope=twice'], /given twice/],
    [[...FROM, '--to', 'MoonieX-Bedrock:prod:fal_api_key', ...META], /UPPER_SNAKE_CASE/],
    [[...FROM, '--to', 'MoonieX-Bedrock:staging:FAL_API_KEY', ...META], /env must be dev or prod/],
    [['--from', 'Org-Infra:prod:([', ...TO, ...META], /does not compile/],
    [['--from', 'Org-Infra:prod', ...TO, ...META], /must be <Project>:<env>/],
    [[...TO, ...META], /need --from and --to/],
    [[...REAL, '--bogus'], /unknown flag/],
  ];
  for (const [args, re] of cases) {
    const r = await run(args);
    assert.equal(r.code, 64, `${args.join(' ')}\n${r.text}`);
    assert.match(r.text, re);
    assert.equal(r.cdpHits.list, 0);
  }
});

test('the token and the value never leave for a non-loopback host', async () => {
  let r = await run(REAL, { env: { INFISICAL_API_URL: 'https://example.com' } });
  assert.equal(r.code, 64, r.text);
  assert.match(r.text, /INFISICAL_API_URL must be a loopback/);
  assert.equal(r.cdpHits.list, 0);
  r = await run(REAL, { cdp: 'http://10.0.0.5:9281' });
  assert.equal(r.code, 64, r.text);
  assert.match(r.text, /<cdp-url> must be a loopback/);
});

// ------------------------------------------------------------------ --find: every project, env and folder, names only

const FIND_PROJECTS = [
  { id: 'p-infra', name: 'Org-Infra', slug: 'org-infra', environments: [{ slug: 'prod', name: 'Production', id: 'e1' }] },
  { id: 'p-flow', name: 'MoonieX-ClaudeFlow', slug: 'mooniex-claudeflow', type: 'secret-manager', environments: [{ slug: 'dev', id: 'e4' }, { slug: 'prod', id: 'e5' }] },
  { id: 'p-web', name: 'MoonieX-Webapp', slug: 'mooniex-webapp', environments: [{ slug: 'prod', id: 'e6' }] },
  { id: 'p-bed', name: 'MoonieX-Bedrock', slug: 'mooniex-bedrock-x1y2', environments: [{ slug: 'dev', id: 'e2' }, { slug: 'prod', id: 'e3' }] },
  { id: 'p-kms', name: 'MoonieX-Keys', slug: 'mooniex-keys', type: 'kms', environments: [] },
];
const findTree = (adminValue = VALUE) => ({
  'p-infra|prod': { '/': [], '/dns': [s('CLOUDFLARE_DNS_CONTABO_TOKEN_RW', OTHER)] },
  'p-flow|dev': { '/': [s('OPENAI_API_KEY', OTHER)] },
  'p-flow|prod': { '/': [s('FAL_KEY', VALUE), s('KLING_API_KEY', OTHER), s('FAL_PERSONAL_KEY', OTHER, 'personal')], '/video': [], '/video/fal': [s('FAL_ADMIN_KEY', adminValue)] },
  'p-web|prod': { '/': [s('fal_lower_api_key', VALUE)] },
  'p-bed|dev': { '/': [] },
  'p-bed|prod': { '/': [s('LUMINA_SEED_TOKEN', OTHER)] },
});
const FIND = ['--find', '/FAL/i'];
// stdout of --find holds names, paths, statuses and counts — nothing else
const FIND_LINE = /^(?:[\w-]+\/[\w.-]+(?:\/[\w.-]+)*\/\w+|[\w-]+(?:\/[\w.-]+)*\/?: (?:HTTP \d+|more than \d+ folders, walk stopped)|scanned: \d+ projects · \d+ envs · \d+ folders · \d+ names · \d+ match · \d+ unreadable|values identical across matches: (?:yes|no|n\/a \(0 matches\))|value group \d+: .+)$/;
const findRun = async (args, world) => {
  const r = await run(args, { world: { projects: FIND_PROJECTS, tree: findTree(), ...world } });
  const lines = r.out.split('\n').filter(Boolean);
  for (const l of lines) assert.match(l, FIND_LINE, `unexpected stdout line in --find: ${l}`);
  for (const l of r.err.split('\n').filter(Boolean)) assert.match(l, /^\[find\] /, `unexpected stderr line in --find: ${l}`);
  assert.equal(r.calls.filter((c) => c.method !== 'GET').length, 0, '--find sent a write');
  return { ...r, lines };
};

test('--find: every project, env and nested folder; one stdout line per match; identical values say yes; exit 0', async () => {
  const r = await findRun(FIND);
  assert.equal(r.code, 0, r.text);
  assert.deepEqual(r.lines.filter((l) => !/^(scanned|values identical)/.test(l)),
    ['MoonieX-ClaudeFlow/prod/FAL_KEY', 'MoonieX-ClaudeFlow/prod/video/fal/FAL_ADMIN_KEY', 'MoonieX-Webapp/prod/fal_lower_api_key']);
  assert.ok(r.lines.includes('scanned: 4 projects · 6 envs · 9 folders · 7 names · 3 match · 0 unreadable'), r.out);
  assert.equal(r.lines.at(-1), 'values identical across matches: yes');
  const listed = new Set(r.calls.filter((c) => c.path === '/api/v3/secrets/raw').map((c) => `${c.query.workspaceId}|${c.query.environment}|${c.query.secretPath}`));
  for (const want of ['p-infra|prod|/', 'p-infra|prod|/dns', 'p-flow|dev|/', 'p-flow|prod|/video/fal', 'p-web|prod|/', 'p-bed|dev|/', 'p-bed|prod|/']) assert.ok(listed.has(want), want);
  assert.ok(![...listed].some((k) => k.startsWith('p-kms|')), 'a kms project was listed');
  assert.match(r.err, /\[find\] MoonieX-Keys: project type kms, not a secret manager; skipped/);
  assert.match(r.err, /\[find\] MoonieX-ClaudeFlow\/prod: 3 folder\(s\) · 3 names · 2 match/);
  assert.ok(!r.out.includes('FAL_PERSONAL_KEY'), 'a personal secret was reported');
});

test('--find: matches with different values say no and name the groups (equality only)', async () => {
  const r = await findRun(FIND, { tree: findTree(OTHER) });
  assert.equal(r.code, 0, r.text);
  assert.ok(r.lines.includes('values identical across matches: no'), r.out);
  assert.ok(r.lines.includes('value group 1: MoonieX-ClaudeFlow/prod/FAL_KEY MoonieX-Webapp/prod/fal_lower_api_key'), r.out);
  assert.ok(r.lines.includes('value group 2: MoonieX-ClaudeFlow/prod/video/fal/FAL_ADMIN_KEY'), r.out);
});

test('--find: a plain regex is case-sensitive; one match says yes; zero matches say n/a', async () => {
  let r = await findRun(['--find', '^FAL_ADMIN']);
  assert.equal(r.code, 0, r.text);
  assert.deepEqual(r.lines.slice(0, 1), ['MoonieX-ClaudeFlow/prod/video/fal/FAL_ADMIN_KEY']);
  assert.equal(r.lines.at(-1), 'values identical across matches: yes');
  r = await findRun(['--find', 'fal_lower|^FAL_KEY$']);
  assert.deepEqual(r.lines.slice(0, 2), ['MoonieX-ClaudeFlow/prod/FAL_KEY', 'MoonieX-Webapp/prod/fal_lower_api_key']);
  r = await findRun(['--find', '/^NOTHING_LIKE_THIS$/']);
  assert.equal(r.code, 0, r.text);
  assert.deepEqual(r.lines, ['scanned: 4 projects · 6 envs · 9 folders · 7 names · 0 match · 0 unreadable', 'values identical across matches: n/a (0 matches)']);
});

test('--find: an unreadable project or folder prints <project>/<env>/<path>: HTTP <status>, the walk goes on, exit 13', async () => {
  const projects = FIND_PROJECTS.map((p) => (p.id === 'p-web' ? { ...p, environments: undefined } : p));
  const r = await findRun(FIND, {
    projects,
    projectStatus: { 'p-web': 403 },                        // its env list cannot be read
    status: { 'p-flow|prod|/video|folders': 403,            // a subfolder's children cannot be listed
      'p-infra|prod|/|secrets': 403,                        // a root's secrets cannot be listed (body echoes the value)
      'p-bed|dev|/|folders': 500 },
  });
  assert.equal(r.code, 13, r.text);
  for (const want of ['MoonieX-Webapp: HTTP 403', 'MoonieX-ClaudeFlow/prod/video: HTTP 403', 'Org-Infra/prod/: HTTP 403', 'MoonieX-Bedrock/dev/: HTTP 500']) {
    assert.ok(r.lines.includes(want), `${want}\n${r.out}`);
  }
  assert.ok(r.lines.includes('MoonieX-ClaudeFlow/prod/FAL_KEY'), 'the walk stopped at the first unreadable path');
  assert.ok(!r.lines.includes('MoonieX-ClaudeFlow/prod/video/fal/FAL_ADMIN_KEY'));
  assert.ok(r.lines.includes('scanned: 4 projects · 5 envs · 6 folders · 5 names · 1 match · 4 unreadable'), r.out);
  const listed = r.calls.filter((c) => c.path === '/api/v3/secrets/raw').map((c) => `${c.query.workspaceId}|${c.query.environment}|${c.query.secretPath}`);
  assert.ok(listed.includes('p-bed|prod|/') && listed.includes('p-infra|prod|/dns'), 'later projects and folders were not walked');
});

test('--find: a 429 is retried and the walk completes', async () => {
  const r = await findRun(FIND, { limited: { 'p-flow|prod|/': 2, 'p-flow|prod|/video': 1 } });
  assert.equal(r.code, 0, r.text);
  assert.ok(r.lines.includes('MoonieX-ClaudeFlow/prod/FAL_KEY'), r.out);
  assert.ok(r.lines.includes('MoonieX-ClaudeFlow/prod/video/fal/FAL_ADMIN_KEY'), r.out);
  assert.ok(r.lines.includes('values identical across matches: yes'), r.out);
});

test('--find: leak check: the fake value, its last 4 and its length never reach stdout or stderr', async () => {
  const r = await findRun(FIND, { tree: findTree(OTHER), status: { 'p-bed|prod|/|secrets': 403 } });
  assert.equal(r.code, 13, r.text);
  for (const v of [VALUE, OTHER]) {
    assert.ok(!r.text.includes(v) && !r.text.includes(v.slice(-4)), 'a value or its last 4 reached the output');
    assert.ok(!new RegExp(`\\b${v.length}\\b`).test(r.text), 'a value length reached the output');
  }
  assert.ok(!/secretValue|denied while reading|slow down/.test(r.text), 'an API body reached the output');
});

test('--find refusals exit 64 before the browser is touched', async () => {
  const cases = [
    [[...FIND, ...FROM], /--find runs alone/],
    [[...FIND, '--dry'], /--find runs alone/],
    [[...FIND, '--meta', 'scope=x'], /--find runs alone/],
    [['--find', '/FAL/g'], /flags may be i, m, s and u/],
    [['--find', '/FAL/ii'], /flags may be i, m, s and u/],
    [['--find', '(['], /does not compile/],
    [['--find'], /--find needs a value/],
  ];
  for (const [args, re] of cases) {
    const r = await run(args);
    assert.equal(r.code, 64, `${args.join(' ')}\n${r.text}`);
    assert.match(r.text, re);
    assert.equal(r.cdpHits.list, 0);
  }
});
