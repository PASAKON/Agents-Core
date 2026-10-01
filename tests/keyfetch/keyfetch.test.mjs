// node --test tests/keyfetch/keyfetch.test.mjs   (no Chrome, no network beyond 127.0.0.1, no Tailscale)
// Covers scripts/keyfetch/keyfetch_lib.mjs and, through a fake CDP browser, capture_key.mjs itself:
// argument parsing, `--path`, two values from one create, both-or-nothing, --new-only.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { UsageError, parseArgs, pickFields, runPuts, checkAbsent } from '../../scripts/keyfetch/keyfetch_lib.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const CAPTURE = resolve(HERE, '../../scripts/keyfetch/capture_key.mjs');
const STUB = join(HERE, 'stub_put.mjs');

const ID = 'tskey-client-TESTID1234';           // synthetic, never a real credential
const SECRET = 'tskey-client-TESTID1234-SECRETVALUE9876';
const BASE = ['http://127.0.0.1:1', '--tab', 'tailscale', '--project', 'Agents-Core', '--env', 'prod'];
const TWO_WIRE = ['--match', '/oauth', '--field', 'id=TAILSCALE_OAUTH_CLIENT_ID', '--field', 'key=TAILSCALE_OAUTH_CLIENT_SECRET'];
const parse = extra => parseArgs([...BASE, ...extra]);
const usageError = (extra, re) => assert.throws(() => parse(extra), e => e instanceof UsageError && re.test(e.message));

// ------------------------------------------------------------------ argument parsing

test('single value form still works: bare --field + --name, path defaults to /', () => {
  const p = parse(['--match', '/keys', '--field', 'key', '--name', 'FAL_API_KEY_RW']);
  assert.deepEqual(p.extractors, [{ src: 'key', name: 'FAL_API_KEY_RW' }]);
  assert.equal(p.mode, 'wire');
  assert.equal(p.opts.path, '/');
  assert.equal(p.opts.as, 'setup');
});

test('single value page form: --dom + --name', () => {
  const p = parse(['--dom', 'input#secret', '--name', 'X_API_KEY']);
  assert.deepEqual(p.extractors, [{ src: 'input#secret', name: 'X_API_KEY' }]);
  assert.equal(p.mode, 'page');
});

test('two values from one create, in the order given, with --path', () => {
  const p = parse([...TWO_WIRE, '--path', '/org-join']);
  assert.deepEqual(p.extractors, [
    { src: 'id', name: 'TAILSCALE_OAUTH_CLIENT_ID' },
    { src: 'key', name: 'TAILSCALE_OAUTH_CLIENT_SECRET' },
  ]);
  assert.equal(p.opts.path, '/org-join');
});

test('page mode takes <css>=<NAME> and a selector may carry its own = signs', () => {
  const p = parse(['--dom', 'input[name="cid"]=X_CLIENT_ID', '--dom', '#sec=X_CLIENT_SECRET']);
  assert.deepEqual(p.extractors, [
    { src: 'input[name="cid"]', name: 'X_CLIENT_ID' },
    { src: '#sec', name: 'X_CLIENT_SECRET' },
  ]);
});

test('--meta is repeatable and --new-only is a bare flag', () => {
  const p = parse([...TWO_WIRE, '--meta', 'owner=ceo', '--meta', 'scope=a b c', '--new-only']);
  assert.deepEqual(p.opts.meta, ['owner=ceo', 'scope=a b c']);
  assert.equal(p.opts['new-only'], true);
});

test('--check needs no extractor', () => {
  const p = parse(['--check']);
  assert.deepEqual(p.extractors, []);
  assert.equal(p.opts.check, true);
});

test('refusals', () => {
  usageError([...TWO_WIRE, '--name', 'X_API_KEY'], /drop --name/);
  usageError(['--match', '/o', '--field', 'a=X_CLIENT_ID', '--field', 'b'], /every --field\/--dom must be/);
  usageError(['--match', '/o', '--field', 'a=X_CLIENT_ID', '--field', 'b=X_CLIENT_ID'], /same variable/);
  usageError(['--match', '/o', '--field', 'a=lower_case'], /missing --name/);
  usageError(['--match', '/o', '--field', 'a', '--name', 'lower'], /UPPER_SNAKE/);
  usageError(['--match', '/o', '--field', 'a=X_ID', '--dom', '#b=X_SECRET'], /exclusive/);
  usageError(['--field', 'a=X_CLIENT_ID'], /--field needs --match/);
  usageError(['--match', '/o'], /needs at least one --field/);
  usageError([], /need --match \+ --field/);
  usageError([...TWO_WIRE, '--path', 'org-join'], /--path/);
  usageError([...TWO_WIRE, '--path', '/a b'], /--path/);
  usageError([...TWO_WIRE, '--path', '/..'], /--path/);
  assert.throws(() => parseArgs(['http://x', '--tab', 't', '--project', 'Org-Infra', '--env', 'prod', ...TWO_WIRE]), /Org-Infra/);
  assert.throws(() => parseArgs(['http://x', '--tab', 't', '--project', 'P', '--env', 'staging', ...TWO_WIRE]), /dev or prod/);
  assert.throws(() => parseArgs(['http://x', '--tab', 't', '--project', 'P', '--env', 'prod', '--match']), /needs a value/);
  assert.throws(() => parseArgs(['http://x', 'http://y', '--tab', 't']), /unexpected argument/);
  assert.throws(() => parseArgs(['--tab', 't', '--project', 'P', '--env', 'prod']), /missing <cdp-url>/);
});

// ------------------------------------------------------------------ pickFields

test('pickFields returns both, and on a miss names (never values) of what is absent', () => {
  const body = { id: ID, key: SECRET, nested: { list: [{ v: 'deep' }] }, empty: '', num: 5 };
  const ex = n => ({ src: n, name: n.toUpperCase().replace(/\W/g, '_') + '_X' });
  assert.deepEqual(pickFields(body, [ex('id'), ex('key')]).entries.map(e => e.value), [ID, SECRET]);
  assert.equal(pickFields(body, [ex('nested.list[0].v')]).entries[0].value, 'deep');
  const r = pickFields(body, [{ src: 'id', name: 'A_ID' }, { src: 'empty', name: 'B_SECRET' }, { src: 'num', name: 'C_TOKEN' }, { src: 'no.such', name: 'D_URL' }]);
  assert.deepEqual(r.entries, [{ name: 'A_ID', value: ID }]);
  assert.deepEqual(r.missing, ['B_SECRET', 'C_TOKEN', 'D_URL']);
});

// ------------------------------------------------------------------ puts and the pre-check (stub tool)

function workdir() {
  const dir = mkdtempSync(join(tmpdir(), 'keyfetch-test-'));
  return { dir, out: join(dir, 'calls.jsonl') };
}
const calls = out => (existsSync(out) ? readFileSync(out, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l)) : []);
function cfg(extra = {}) {
  return { python: process.execPath, tool: STUB, project: 'Agents-Core', env: 'prod', path: '/org-join', as: 'setup',
           comment: 'join_api mints keys', meta: ['provider_name=p', 'owner=ceo'], multiline: false, ...extra };
}
const entries = [{ name: 'TAILSCALE_OAUTH_CLIENT_ID', value: ID }, { name: 'TAILSCALE_OAUTH_CLIENT_SECRET', value: SECRET }];

test('runPuts: each value goes on its own stdin, never in argv, --path and metadata passed', async () => {
  const { out } = workdir();
  process.env.STUB_OUT = out;
  delete process.env.STUB_FAIL;
  const r = await runPuts(entries, cfg());
  assert.deepEqual(r, { code: 0, saved: entries.map(e => e.name), failed: null, skipped: [] });
  const c = calls(out);
  assert.equal(c.length, 2);
  assert.deepEqual(c.map(x => x.stdin), [ID + '\n', SECRET + '\n']);
  for (const x of c) {
    assert.ok(!x.argv.some(a => a.includes('TESTID1234') || a.includes('SECRETVALUE')), 'value leaked into argv');
    assert.deepEqual(x.argv.slice(0, 3), ['put', 'Agents-Core', 'prod']);
    assert.ok(x.argv.includes('--stdin'));
    assert.equal(x.argv[x.argv.indexOf('--path') + 1], '/org-join');
    assert.equal(x.argv[x.argv.indexOf('--as') + 1], 'setup');
    assert.deepEqual(x.argv.filter((a, i) => x.argv[i - 1] === '--meta'), ['provider_name=p', 'owner=ceo']);
  }
});

test('runPuts: second put fails -> partial, first is reported as saved', async () => {
  const { out } = workdir();
  process.env.STUB_OUT = out;
  process.env.STUB_FAIL = 'TAILSCALE_OAUTH_CLIENT_SECRET';
  const r = await runPuts(entries, cfg());
  delete process.env.STUB_FAIL;
  assert.equal(r.code, 3);
  assert.deepEqual(r.saved, ['TAILSCALE_OAUTH_CLIENT_ID']);
  assert.equal(r.failed, 'TAILSCALE_OAUTH_CLIENT_SECRET');
});

test('runPuts: first put fails -> nothing saved and the second put is never attempted', async () => {
  const { out } = workdir();
  process.env.STUB_OUT = out;
  process.env.STUB_FAIL = 'TAILSCALE_OAUTH_CLIENT_ID';
  const r = await runPuts(entries, cfg());
  delete process.env.STUB_FAIL;
  assert.equal(r.code, 3);
  assert.deepEqual(r.saved, []);
  assert.deepEqual(r.skipped, ['TAILSCALE_OAUTH_CLIENT_SECRET']);
  assert.equal(calls(out).length, 1);
});

test('runPuts: a tool that cannot start is code 127, not a hang', async () => {
  const r = await runPuts(entries, cfg({ python: '/nonexistent/python' }));
  assert.equal(r.code, 127);
  assert.deepEqual(r.saved, []);
});

test('checkAbsent: absent vs present vs unreadable', async () => {
  const { out } = workdir();
  process.env.STUB_OUT = out;
  process.env.STUB_PRESENT = 'TAILSCALE_OAUTH_CLIENT_ID';
  process.env.STUB_ERROR = 'TAILSCALE_OAUTH_CLIENT_SECRET';
  const r = await checkAbsent([...entries.map(e => e.name), 'OTHER_SECRET'], cfg());
  delete process.env.STUB_PRESENT; delete process.env.STUB_ERROR;
  assert.deepEqual(r, { present: ['TAILSCALE_OAUTH_CLIENT_ID'], error: ['TAILSCALE_OAUTH_CLIENT_SECRET'] });
  const c = calls(out);
  assert.equal(c[0].argv[0], 'last4');
  assert.equal(c[0].argv[c[0].argv.indexOf('--path') + 1], '/org-join');
});

// ------------------------------------------------------------------ capture_key.mjs against a fake CDP browser

// Minimal WebSocket server: handshake plus small text frames, which is all CDP needs here.
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

// scenario: { body, status, pageValues, buttons }
async function fakeBrowser(scenario) {
  const log = { clicks: 0, escapes: 0 };
  const server = createServer((req, res) => {
    if (req.url === '/json/list') {
      const { port } = server.address();
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify([{ id: 'ABCDEF1234567890', type: 'page', url: 'https://login.tailscale.com/admin/settings/oauth', webSocketDebuggerUrl: `ws://127.0.0.1:${port}/devtools/page/1` }]));
    } else { res.statusCode = 404; res.end(); }
  });
  server.on('upgrade', (req, sock) => {
    const accept = createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    sock.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
    const state = { buf: Buffer.alloc(0) };
    const emit = (method, params) => sock.write(frame(JSON.stringify({ method, params })));
    sock.on('data', chunk => {
      for (const text of readFrames(state, chunk)) {
        const m = JSON.parse(text);
        let result = {};
        if (m.method === 'Runtime.evaluate') {
          const expr = m.params.expression;
          let value = null;
          if (expr.includes('getClientRects')) {
            value = { dialogs: 0, heading: 'OAuth clients', matches: scenario.buttons ?? 1, labels: ['Generate OAuth client'], disabled: false, fields: [] };
          } else if (expr.includes('.click()')) {
            log.clicks++;
            value = true;
            if (scenario.body !== undefined) setTimeout(() => {
              emit('Network.requestWillBeSent', { requestId: 'r1', request: { method: 'POST' } });
              emit('Network.responseReceived', { requestId: 'r1', response: { url: 'https://login.tailscale.com/api/oauth/clients', status: scenario.status ?? 200 } });
              emit('Network.loadingFinished', { requestId: 'r1' });
            }, 20);
          } else if (expr.includes('sels.map')) {
            value = scenario.pageValues;
          } else if (expr.includes('sels.forEach')) {
            log.blanked = true;
          } else if (expr.includes('role="dialog"')) {
            value = 0;
          }
          result = { result: { value } };
        } else if (m.method === 'Network.getResponseBody') {
          result = { body: JSON.stringify(scenario.body), base64Encoded: false };
        } else if (m.method === 'Input.dispatchKeyEvent' && m.params.type === 'keyDown') {
          log.escapes++;
        }
        sock.write(frame(JSON.stringify({ id: m.id, result })));
      }
    });
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  return { url: `http://127.0.0.1:${server.address().port}`, log, close: () => server.close() };
}

async function runCapture(browser, args, env = {}) {
  const { out } = workdir();
  const child = spawn(process.execPath, [CAPTURE, browser.url, '--tab', 'tailscale', '--project', 'Agents-Core', '--env', 'prod', ...args], {
    env: { ...process.env, INFISICAL_SETUP_PY: STUB, PYTHON: process.execPath, STUB_OUT: out, STUB_FAIL: '', STUB_PRESENT: '', STUB_ERROR: '', ...env },
  });
  let text = '';
  child.stdout.on('data', d => { text += d; });
  child.stderr.on('data', d => { text += d; });
  const code = await new Promise(r => child.on('exit', c => r(c)));
  browser.close();
  assert.ok(!text.includes('SECRETVALUE9876') && !text.includes('TESTID1234-SECRET'), 'a value reached the output');
  return { code, text, calls: calls(out) };
}
const META = ['--comment', 'join_api mints keys', '--meta', 'provider_name=p', '--meta', 'owner=ceo'];

test('capture_key wire: both values from one create -> two puts, exit 0, nothing printed', async () => {
  const b = await fakeBrowser({ body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, '--path', '/org-join', ...META]);
  assert.equal(r.code, 0, r.text);
  assert.deepEqual(r.calls.map(c => c.argv[3]), ['TAILSCALE_OAUTH_CLIENT_ID', 'TAILSCALE_OAUTH_CLIENT_SECRET']);
  assert.deepEqual(r.calls.map(c => c.stdin), [ID + '\n', SECRET + '\n']);
  assert.ok(r.calls.every(c => c.argv[c.argv.indexOf('--path') + 1] === '/org-join'));
  assert.match(r.text, /saved 2\/2/);
  assert.ok(b.log.escapes >= 1, 'Escape not pressed');
});

test('capture_key wire: single-value form still works', async () => {
  const b = await fakeBrowser({ body: { key: SECRET } });
  const r = await runCapture(b, ['--match', '/oauth', '--field', 'key', '--name', 'FAL_API_KEY_RW', ...META]);
  assert.equal(r.code, 0, r.text);
  assert.equal(r.calls.length, 1);
  assert.equal(r.calls[0].argv[3], 'FAL_API_KEY_RW');
  assert.equal(r.calls[0].argv[r.calls[0].argv.indexOf('--path') + 1], '/');
});

test('capture_key wire: one value missing from the response -> exit 7 and NO put at all', async () => {
  const b = await fakeBrowser({ body: { id: ID } });
  const r = await runCapture(b, [...TWO_WIRE, ...META]);
  assert.equal(r.code, 7, r.text);
  assert.equal(r.calls.length, 0);
  assert.match(r.text, /TAILSCALE_OAUTH_CLIENT_SECRET/);
  assert.match(r.text, /nothing saved/);
});

test('capture_key wire: second put fails -> exit 8, PARTIAL line names saved and failed', async () => {
  const b = await fakeBrowser({ body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, ...META], { STUB_FAIL: 'TAILSCALE_OAUTH_CLIENT_SECRET' });
  assert.equal(r.code, 8, r.text);
  assert.match(r.text, /PARTIAL: saved TAILSCALE_OAUTH_CLIENT_ID; TAILSCALE_OAUTH_CLIENT_SECRET FAILED/);
  assert.match(r.text, /EXISTS at the provider/);
});

test('capture_key wire: first put fails -> put\'s own exit code, second never attempted', async () => {
  const b = await fakeBrowser({ body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, ...META], { STUB_FAIL: 'TAILSCALE_OAUTH_CLIENT_ID' });
  assert.equal(r.code, 3, r.text);
  assert.equal(r.calls.length, 1);
  assert.match(r.text, /nothing saved/);
});

test('capture_key wire: provider answers 4xx -> exit 6, no put', async () => {
  const b = await fakeBrowser({ body: { message: 'forbidden' }, status: 403 });
  const r = await runCapture(b, [...TWO_WIRE, ...META]);
  assert.equal(r.code, 6, r.text);
  assert.equal(r.calls.length, 0);
});

test('capture_key page: two <css>=<NAME> elements -> read, blanked, two puts', async () => {
  const b = await fakeBrowser({ pageValues: [ID, SECRET] });
  const r = await runCapture(b, ['--dom', '#cid=TAILSCALE_OAUTH_CLIENT_ID', '--dom', '#sec=TAILSCALE_OAUTH_CLIENT_SECRET', ...META]);
  assert.equal(r.code, 0, r.text);
  assert.deepEqual(r.calls.map(c => c.stdin), [ID + '\n', SECRET + '\n']);
  assert.ok(b.log.blanked, 'page elements not blanked');
});

test('capture_key page: one element never shows a value -> exit 7, no put', async () => {
  const b = await fakeBrowser({ pageValues: [ID, null] });
  const r = await runCapture(b, ['--dom', '#cid=TAILSCALE_OAUTH_CLIENT_ID', '--dom', '#sec=TAILSCALE_OAUTH_CLIENT_SECRET', ...META], { KEYFETCH_WAIT_MS: '1500' });
  assert.equal(r.code, 7, r.text);
  assert.equal(r.calls.length, 0);
});

test('capture_key --new-only: an existing secret stops the run BEFORE the click (exit 9)', async () => {
  const b = await fakeBrowser({ body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, '--new-only', '--path', '/org-join', ...META], { STUB_PRESENT: 'TAILSCALE_OAUTH_CLIENT_ID' });
  assert.equal(r.code, 9, r.text);
  assert.equal(b.log.clicks, 0, 'clicked although a secret exists');
  assert.ok(r.calls.every(c => c.argv[0] === 'last4'), 'a put ran');
  assert.match(r.text, /already in Agents-Core\/prod\/org-join: TAILSCALE_OAUTH_CLIENT_ID/);
});

test('capture_key --new-only: a check that cannot be made also refuses (exit 9)', async () => {
  const b = await fakeBrowser({ body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, '--new-only', ...META], { STUB_ERROR: 'TAILSCALE_OAUTH_CLIENT_SECRET' });
  assert.equal(r.code, 9, r.text);
  assert.equal(b.log.clicks, 0);
});

test('capture_key --new-only: both absent -> proceeds and saves both', async () => {
  const b = await fakeBrowser({ body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, '--new-only', ...META]);
  assert.equal(r.code, 0, r.text);
  assert.deepEqual(r.calls.map(c => c.argv[0]), ['last4', 'last4', 'put', 'put']);
});

test('capture_key --check: finds exactly one button, clicks nothing, saves nothing', async () => {
  const b = await fakeBrowser({});
  const r = await runCapture(b, ['--check', '--click', '^generate']);
  assert.equal(r.code, 0, r.text);
  assert.equal(b.log.clicks, 0);
  assert.match(r.text, /buttons=1/);
});

test('capture_key: two Generate buttons -> --check exits 1, a real run refuses (exit 4)', async () => {
  let b = await fakeBrowser({ buttons: 2 });
  assert.equal((await runCapture(b, ['--check'])).code, 1);
  b = await fakeBrowser({ buttons: 2, body: { id: ID, key: SECRET } });
  const r = await runCapture(b, [...TWO_WIRE, ...META]);
  assert.equal(r.code, 4);
  assert.equal(b.log.clicks, 0);
});

test('capture_key: a usage error exits 64 before it touches the browser', async () => {
  const b = await fakeBrowser({});
  const r = await runCapture(b, ['--match', '/o', '--field', 'a=X_CLIENT_ID', '--field', 'b']);
  assert.equal(r.code, 64, r.text);
  assert.match(r.text, /every --field\/--dom must be/);
});
