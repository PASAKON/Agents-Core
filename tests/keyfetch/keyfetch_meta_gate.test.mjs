// node --test tests/keyfetch/keyfetch_meta_gate.test.mjs   (no Chrome, no network, no Infisical)
// The metadata gate in scripts/keyfetch/keyfetch_lib.mjs (skill ALL_Rules_Secrets rule 2): a planned key
// write without a §4d provider_name, a scope or an expires is refused before anything is clicked, and so is
// project Org-Infra. Every value here is fake.
import test from 'node:test';
import assert from 'node:assert/strict';
import { UsageError, NO_EXPIRY, parseArgs, checkKeyMeta, metaMap, runPuts } from '../../scripts/keyfetch/keyfetch_lib.mjs';

const GOOD = {
  provider_name: 'ag-core-prod-rw-exp2099-01-31', console_url: 'https://example.test/keys',
  scope: 'fake-scope', expires: '2099-01-31', owner: 'CTO',
};
const metaList = (over = {}) => Object.entries({ ...GOOD, ...over }).filter(([, v]) => v !== null).map(([k, v]) => `${k}=${v}`);
const cfg = (over = {}, metaOver = {}) => ({ project: 'Agents-Core', env: 'prod', comment: 'fake purpose', meta: metaList(metaOver), ...over });
const refused = (c, re) => assert.throws(() => checkKeyMeta(c), e => e instanceof UsageError && re.test(e.message), `expected ${re}`);
const argv = (metaOver = {}, extra = []) => ['http://127.0.0.1:1', '--tab', 't', '--project', 'Agents-Core', '--env', 'prod',
  '--match', '/keys', '--field', 'key', '--name', 'FAL_API_KEY_RW', '--comment', 'fake purpose',
  ...metaList(metaOver).flatMap(m => ['--meta', m]), ...extra];

test('a full §4c set passes and returns the page exp date', () => {
  const r = checkKeyMeta(cfg());
  assert.equal(r.pageExp, '2099-01-31');
  assert.equal(r.md.scope, 'fake-scope');
});

test('provider_name: the optional -<host>, every brand, and exactly 40 characters pass', () => {
  const forty = 'ag-core-prod-admin-exp2099-01-31-contabo';
  assert.equal(forty.length, 40);
  checkKeyMeta(cfg({}, { provider_name: forty }));
  for (const brand of ['mx', 'ln', 'wc', 'lr', 'ag']) checkKeyMeta(cfg({}, { provider_name: `${brand}-x1-prod-ro-exp2099-01-31` }));
  checkKeyMeta(cfg({ env: 'dev' }, { provider_name: 'mx-claudeflow-dev-rw-exp2099-01-31' }));
});

test('each required field missing is refused by name', () => {
  for (const k of Object.keys(GOOD)) refused(cfg({}, { [k]: null }), new RegExp(`missing --meta .*${k}=`));
  refused(cfg({ comment: '' }), /missing --comment/);
  refused(cfg({ comment: '   ' }), /missing --comment/);
  refused(cfg({ comment: undefined }), /missing --comment/);
});

test('provider_name longer than 40 characters is refused even when the shape is right', () => {
  const long = 'mx-lineautomationx-prod-admin-exp2099-01-31';
  assert.ok(long.length > 40);
  refused(cfg({}, { provider_name: long }), /longer than 40/);
});

test('provider_name in any other shape is refused', () => {
  for (const bad of ['p', 'none', 'none (no name field)', 'zz-core-prod-rw-exp2099-01-31', 'MX-core-prod-rw-exp2099-01-31',
    'mx-core-prod-rw', 'mx-core-prod-full-exp2099-01-31', 'mx-core-staging-rw-exp2099-01-31', 'mx-core-prod-rw-exp2099-01-31-laptop',
    'mx-core-prod-rw-2099-01-31', 'mx-core-prod-rw-exp20990131', 'mx-Core-prod-rw-exp2099-01-31', 'mx--prod-rw-exp2099-01-31',
    'infra-dns-mac-rw-exp2099-01-31']) {
    refused(cfg({}, { provider_name: bad }), /does not read <brand>-<project>-<env>-<access>-exp<YYYY-MM-DD>/);
  }
});

test('an exp date that is not a calendar date is refused', () => {
  refused(cfg({}, { provider_name: 'mx-core-prod-rw-exp2099-02-30', expires: '2099-02-30' }), /not a real calendar date/);
  refused(cfg({}, { provider_name: 'mx-core-prod-rw-exp2099-13-01', expires: NO_EXPIRY }), /not a real calendar date/);
});

test('provider_name env must equal --env', () => {
  refused(cfg({ env: 'prod' }, { provider_name: 'mx-core-dev-rw-exp2099-01-31' }), /says env dev but --env is prod/);
  refused(cfg({ env: 'dev' }), /says env prod but --env is dev/);
});

test('expires: an ISO date equal to the name, or the literal none-offered', () => {
  for (const bad of ['2099/01/31', '2099-1-31', 'next year', 'none', 'never', '2099-02-29']) {
    refused(cfg({}, { expires: bad }), /expires must be an ISO date YYYY-MM-DD, or none-offered/);
  }
  refused(cfg({}, { expires: '2099-01-30' }), /expires and the exp date in provider_name differ/);
  const r = checkKeyMeta(cfg({}, { expires: NO_EXPIRY }));
  assert.equal(r.md.expires, 'none-offered');
});

test('Org-Infra is refused in every spelling, before the metadata is even read', () => {
  for (const project of ['Org-Infra', 'org-infra', 'ORG_INFRA', ' Org-Infra ', 'OrgInfra', 'org infra', 'Org.Infra']) {
    refused(cfg({ project }), /Org-Infra values are entered by the CEO only/);
    refused({ project, env: 'prod' }, /Org-Infra/);
    // parseArgs refuses it on every run, a bare --check included
    assert.throws(() => parseArgs(['http://x', '--tab', 't', '--project', project, '--env', 'prod', '--check']), /Org-Infra/);
  }
});

test('malformed --meta items are refused by position, a repeated key by name', () => {
  for (const bad of ['scope', '=x', 'scope=', 'scope=   ', 'Scope=x', '1x=y', 'a-b=c']) {
    assert.throws(() => metaMap(['owner=CTO', bad]), e => e instanceof UsageError && /--meta #2 is not key=value/.test(e.message));
  }
  assert.throws(() => metaMap(['scope=a', 'scope=b']), /--meta scope is given twice/);
  assert.deepEqual(metaMap([' scope = a b ', 'why_wide=x=y']), { scope: 'a b', why_wide: 'x=y' });
});

test('no refusal echoes the bad value (a key typed into the wrong flag stays out of the error)', () => {
  const fake = 'FAKEFAKE-not-a-real-key-0000-zzzz';
  const pieces = Array.from({ length: fake.length - 7 }, (_, i) => fake.slice(i, i + 8));
  const cases = [
    cfg({}, { provider_name: fake }), cfg({}, { expires: fake }), cfg({ comment: 'x', meta: [...metaList(), fake] }),
    cfg({ meta: [...metaList(), `scope=${fake}`] }), cfg({}, { provider_name: `mx-core-prod-rw-exp2099-01-31${fake}` }),
  ];
  for (const c of cases) {
    let msg = '';
    try { checkKeyMeta(c); } catch (e) { msg = e.message; }
    assert.ok(msg, 'expected a refusal');
    for (const p of pieces) assert.ok(!msg.includes(p), `refusal echoed part of the value: ${p}`);
  }
});

test('parseArgs gates every planned write, --check rehearsals included; a bare --check needs no metadata', () => {
  const p = parseArgs(argv());
  assert.equal(p.mode, 'wire');
  assert.throws(() => parseArgs(argv({ scope: null })), /missing --meta scope=/);
  assert.throws(() => parseArgs(argv({ scope: null }, ['--check'])), /missing --meta scope=/);
  assert.deepEqual(parseArgs(['http://x', '--tab', 't', '--project', 'P', '--env', 'prod', '--check']).extractors, []);
});

test('parseArgs refuses a key that would be dead on arrival (expires, or the rotate-by date for none-offered)', () => {
  const at = (date, expires) => argv({ provider_name: `ag-core-prod-rw-exp${date}`, expires: expires ?? date });
  assert.throws(() => parseArgs(at('2030-05-01'), '2030-05-01'), /dead on arrival: expires 2030-05-01 is not after today 2030-05-01/);
  assert.throws(() => parseArgs(at('2030-04-30'), '2030-05-01'), /dead on arrival/);
  assert.throws(() => parseArgs(at('2030-05-01', NO_EXPIRY), '2030-05-01'), /the rotate-by date in provider_name 2030-05-01/);
  assert.equal(parseArgs(at('2030-05-02'), '2030-05-01').mode, 'wire');
  assert.equal(parseArgs(at('2030-05-02', NO_EXPIRY), '2030-05-01').mode, 'wire');
});

test('runPuts runs the gate again and spawns nothing when it refuses', async () => {
  const spawned = [];
  const deps = { spawn: (...a) => { spawned.push(a); throw new Error('must not spawn'); } };
  const entries = [{ name: 'FAL_API_KEY_RW', value: 'FAKEFAKE-not-a-real-key-0000-zzzz' }];
  await assert.rejects(runPuts(entries, { ...cfg({}, { expires: null }), python: 'x', tool: 'y', as: 'z', path: '/' }, deps), /missing --meta expires=/);
  await assert.rejects(runPuts(entries, { ...cfg({ project: 'Org-Infra' }), python: 'x', tool: 'y', as: 'z', path: '/' }, deps), /Org-Infra/);
  assert.equal(spawned.length, 0);
});
