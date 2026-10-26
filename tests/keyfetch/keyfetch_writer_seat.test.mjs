import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseManifest, reconcileSeat, SeatError } from '../../scripts/infisical/keyfetch_writer_lib.mjs';

const projects = parseManifest(readFileSync(new URL('../../config/keyfetch-writer.yaml', import.meta.url), 'utf8'));
const SECRET = 'sk-test-NEVER-PRINT-THIS-SECRET-123456789';
function fake({ setup = true, writer = false, role = 'no-access', users = 1, attached = true, members = true, missing = false, fail = '' } = {}) {
  const calls = [], lines = [];
  const identities = ['contabo', 'mac', 'winbox'].map(name => ({ identity: { name, id: name } }));
  if (setup) identities.push({ identity: { name: 'setup', id: 'setup-id-long-123456789' }, role: 'admin' });
  if (writer) identities.push({ identity: { name: 'keyfetch-writer', id: 'writer-id-long-123456789', authMethods: attached ? ['universal-auth'] : [] }, role });
  const memberships = new Map(projects.map((name, i) => [`p${i}`, writer && members ? [{ identity: { id: 'writer-id-long-123456789' }, roles: [{ role: 'member' }] }] : []]));
  const secrets = [{ id: 'secret-id-long-123456789', isClientSecretRevoked: false, clientSecret: SECRET }];
  const api = async (method, path, body) => {
    calls.push({ method, path, body });
    if (fail && path.includes(fail)) return { status: 403, json: { message: `Permission denied ${SECRET}`, token: SECRET } };
    let json = { token: SECRET };
    if (method === 'GET') {
      if (path.startsWith('/api/v1/identities?')) json.identities = identities;
      else if (path.endsWith('/memberships')) json.users = Array.from({ length: users }, () => ({ user: { username: SECRET } }));
      else if (path.endsWith('/workspaces')) json.workspaces = projects.slice(missing ? 1 : 0).map(name => ({ name, id: `p${projects.indexOf(name)}` }));
      else if (path.endsWith('/client-secrets')) json.clientSecretData = secrets;
      else if (path.includes('/identity-memberships?')) json.identityMemberships = memberships.get(path.split('/')[4]);
      else assert.fail(`unexpected GET ${path}`);
    } else if (method === 'DELETE') {
      identities.splice(identities.findIndex(m => m.identity.name === 'setup'), 1);
    } else if (path.endsWith('/revoke')) secrets[0].isClientSecretRevoked = true;
    else if (path === '/api/v1/identities') {
      const row = { identity: { id: 'writer-id-long-123456789', name: body.name, authMethods: [] }, role: body.role };
      identities.push(row); json.identity = row.identity;
    } else if (path.includes('/identity-memberships/')) {
      memberships.get(path.split('/')[4]).push({ identity: { id: 'writer-id-long-123456789' }, roles: [{ role: body.role }] });
    } else if (path.startsWith('/api/v1/auth/universal-auth/identities/')) {
      identities.find(m => m.identity.name === 'keyfetch-writer').identity.authMethods = ['universal-auth'];
    } else assert.fail(`unexpected write ${path}`);
    return { status: 200, json };
  };
  return { api, calls, lines, memberships, run: (go = false, names = projects) => reconcileSeat({ api, orgId: 'org-long-123456789', projects: names, go, log: s => lines.push(s) }) };
}
const writes = f => f.calls.filter(c => c.method !== 'GET');

test('dry run prints complete plan without writes', async () => {
  const f = fake(); await f.run();
  assert.equal(writes(f).length, 0);
  assert.match(f.lines.join('\n'), /after=5 cap=5/);
  assert.match(f.lines.join('\n'), /create org role=no-access/);
  assert.equal(f.lines.filter(l => l.includes('role=member')).length, 3);
  if (process.env.SEAT_SAMPLE) console.log(f.lines.join('\n'));
});
test('go revokes and deletes setup before no-access create, then attaches and adds member', async () => {
  const f = fake(); await f.run(true);
  const w = writes(f);
  assert.match(w[0].path, /\/revoke$/);
  assert.equal(w[1].method, 'DELETE');
  assert.equal(w[2].path, '/api/v1/identities');
  assert.deepEqual(w[2].body, { name: 'keyfetch-writer', organizationId: 'org-long-123456789', role: 'no-access' });
  assert.equal(w.length, 7);
  assert.equal(w.filter(c => c.body?.role === 'member').length, 3);
  assert.ok(!w.some(c => c.body?.role === 'admin' || c.path.endsWith('/client-secrets')));
  f.calls.length = 0; await f.run(true);
  assert.equal(writes(f).length, 0, 'completed migration reruns without writes');
});
for (const names of [['Org-Infra'], ['Org-Node'], ['Agents-Core', 'agents-core'], []]) {
  test(`manifest rejects ${JSON.stringify(names)} before any API call`, async () => {
    const f = fake(); await assert.rejects(f.run(true, names), SeatError); assert.equal(f.calls.length, 0);
  });
}
test('loader refuses malformed manifests', () => {
  for (const s of ['projects: [Org-Infra]', 'projects: [Org-Node]', 'projects: [A, A]', 'projects: []', 'projects: [A]\nextra: true']) assert.throws(() => parseManifest(s));
});
test('cap counts users and stops before any writes', async () => {
  const f = fake({ users: 2 }); await assert.rejects(f.run(true), /over cap/); assert.equal(writes(f).length, 0);
});
test('missing live project stops before deleting setup', async () => {
  const f = fake({ missing: true }); await assert.rejects(f.run(true), /missing or ambiguous/); assert.equal(writes(f).length, 0);
});
test('existing wrong org role is reported and never changed', async () => {
  const f = fake({ setup: false, writer: true, role: 'admin' }); await assert.rejects(f.run(true), /org role admin/); assert.equal(writes(f).length, 0);
});
test('already complete sends no writes', async () => {
  const f = fake({ setup: false, writer: true }); await f.run(true); assert.equal(writes(f).length, 0);
});
test('resume after create attaches missing auth and memberships only', async () => {
  const f = fake({ setup: false, writer: true, attached: false, members: false }); await f.run(true);
  assert.equal(writes(f).length, 4); assert.ok(!writes(f).some(c => c.path === '/api/v1/identities'));
});
test('existing different project role is left alone', async () => {
  const f = fake({ setup: false, writer: true }); f.memberships.get('p0')[0].roles = [{ role: 'viewer' }];
  await f.run(true); assert.equal(writes(f).length, 0); assert.match(f.lines.join('\n'), /roles=viewer; left alone/);
});
test('API error prints step, status, sanitized message; never secrets or long IDs', async () => {
  const f = fake({ fail: '/revoke' });
  await assert.rejects(f.run(true), e => {
    f.lines.push(e.message); return /setup revoke client secret: HTTP 403 Permission denied/.test(e.message);
  });
  assert.equal(writes(f).length, 1);
  assert.ok(!f.lines.join('\n').includes(SECRET));
  assert.ok(!/id-long-123456789/.test(f.lines.join('\n')));
});
test('success output never contains response credentials', async () => {
  const f = fake(); await f.run(true); assert.ok(!f.lines.join('\n').includes(SECRET));
});
test('transport exceptions cannot disclose credentials', async () => {
  const lines = [];
  await assert.rejects(reconcileSeat({ api: async () => { throw new Error(SECRET); }, orgId: 'fake', projects, log: s => lines.push(s) }), e => {
    lines.push(e.message); return /transport failed/.test(e.message);
  });
  assert.ok(!lines.join('\n').includes(SECRET));
});
