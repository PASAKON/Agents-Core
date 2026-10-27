// The browser-free parts of capture_key.mjs, split out so tests can run them with no Chrome.
// Skill: CTO_Procedure_KeyFetch. Nothing here prints, logs or returns a secret value as text:
// values live only in the `entries` arrays the caller hands in, and go to the put tool on stdin.
import { spawn } from 'node:child_process';

export class UsageError extends Error {}

const NAME_RE = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$/;
// An extractor with its own variable name: `<json.path or css selector>=<UPPER_SNAKE_NAME>`.
// The name is the LAST `=` group, so a selector like input[name="id"] keeps its own `=`.
const NAMED_RE = /^(.+)=([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$/s;
const BARE_FLAGS = new Set(['wait', 'check', 'multiline', 'new-only']);
const REPEATABLE = new Set(['meta', 'field', 'dom']);

// The metadata gate (skill ALL_Rules_Secrets rule 2, PLAN §4c/§4d). A key write without it is refused
// BEFORE anything is clicked: `put` refusing after the click leaves a live key at the provider with no home.
// Every message names the field and the rule, never the value, so a value typed into the wrong flag
// does not come back in the error.
export const BRANDS = ['mx', 'ln', 'wc', 'lr', 'ag'];           // PLAN §4d; a new brand is a PLAN edit first
const HOSTS = ['mac', 'contabo', 'winbox', 'ci', 'ceo'];        // PLAN §3b closed host list, the optional -<host>
const PAGE_NAME_MAX = 40;                                       // GitHub fine-grained PAT names cap at 40
const PAGE_NAME_RE = new RegExp(`^(?:${BRANDS.join('|')})-[a-z0-9]+-(dev|prod)-(?:ro|rw|admin)-exp(\\d{4}-\\d{2}-\\d{2})(?:-(?:${HOSTS.join('|')}))?$`);
const PAGE_NAME_SHAPE = `<brand>-<project>-<env>-<access>-exp<YYYY-MM-DD>[-<host>] (brand ${BRANDS.join('|')}, env dev|prod, access ro|rw|admin)`;
export const NO_EXPIRY = 'none-offered';                        // the provider offers no expiry; the name's exp is the rotate-by date
const REQUIRED_META = ['provider_name', 'console_url', 'scope', 'expires', 'owner'];  // = tools/infisical_setup.py REQUIRED_META
const META_KEY_RE = /^[a-z][a-z0-9_]*$/;

const isOrgInfra = project => String(project).toLowerCase().replace(/[^a-z0-9]/g, '') === 'orginfra';
// A real calendar date: Date.UTC rolls 02-30 over to March, so the round trip must give the same string.
const isIsoDate = s => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return false;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
};

// --meta items -> { key: value }, refusing anything `put` would refuse only after the click.
export function metaMap(items) {
  const out = {};
  items.forEach((item, i) => {
    const eq = item.indexOf('=');
    const key = eq > 0 ? item.slice(0, eq).trim() : '';
    const val = eq > 0 ? item.slice(eq + 1).trim() : '';
    if (!META_KEY_RE.test(key) || !val) throw new UsageError(`--meta #${i + 1} is not key=value with a lower_snake key and a non-empty value`);
    if (key in out) throw new UsageError(`--meta ${key} is given twice`);
    out[key] = val;
  });
  return out;
}

// The structural gate: no clock, so the same inputs pass here before the click and again in runPuts.
// Returns { md, pageExp } for the caller's own checks.
export function checkKeyMeta({ project, env, comment, meta }) {
  if (isOrgInfra(project)) throw new UsageError('Org-Infra values are entered by the CEO only (PLAN §3b, Q-20261026-1118-4d3d); KeyFetch writes into the key\'s own repo project');
  if (!comment || !String(comment).trim()) throw new UsageError('missing --comment <purpose> (PLAN §4c)');
  const md = metaMap(meta || []);
  const missing = REQUIRED_META.filter(k => !(k in md));
  if (missing.length) throw new UsageError(`missing --meta ${missing.map(k => `${k}=…`).join(' ')} (PLAN §4c; refused before anything is clicked)`);
  const name = md.provider_name;
  if (name.length > PAGE_NAME_MAX) throw new UsageError(`provider_name is longer than ${PAGE_NAME_MAX} characters (PLAN §4d)`);
  const m = PAGE_NAME_RE.exec(name);
  if (!m) throw new UsageError(`provider_name does not read ${PAGE_NAME_SHAPE} (PLAN §4d)`);
  const [, nameEnv, pageExp] = m;
  if (!isIsoDate(pageExp)) throw new UsageError('provider_name: the exp date is not a real calendar date');
  if (nameEnv !== env) throw new UsageError(`provider_name says env ${nameEnv} but --env is ${env}`);
  if (md.expires !== NO_EXPIRY) {
    if (!isIsoDate(md.expires)) throw new UsageError(`expires must be an ISO date YYYY-MM-DD, or ${NO_EXPIRY} when the provider offers no expiry`);
    if (md.expires !== pageExp) throw new UsageError('expires and the exp date in provider_name differ (PLAN §4c/§4d: both carry the provider\'s expiry)');
  }
  return { md, pageExp };
}

export function parseArgs(argv, today = new Date().toISOString().slice(0, 10)) {
  const opts = { meta: [], field: [], dom: [], method: 'POST', click: '^(create|generate|new|add)\\b', as: 'keyfetch-writer', path: '/' };
  let cdpUrl = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) {
      if (cdpUrl) throw new UsageError(`unexpected argument ${a}`);
      cdpUrl = a;
      continue;
    }
    const key = a.slice(2);
    if (BARE_FLAGS.has(key)) { opts[key] = true; continue; }
    const val = argv[++i];
    if (val === undefined) throw new UsageError(`--${key} needs a value`);
    if (REPEATABLE.has(key)) opts[key].push(val); else opts[key] = val;
  }
  if (!cdpUrl) throw new UsageError('missing <cdp-url>');
  for (const k of ['tab', 'project', 'env']) if (!opts[k]) throw new UsageError(`missing --${k}`);
  if (!/^(dev|prod)$/.test(opts.env)) throw new UsageError('--env must be dev or prod');
  if (isOrgInfra(opts.project)) throw new UsageError('Org-Infra values are entered by the CEO only (PLAN §3b, Q-20261026-1118-4d3d)');
  if (!/^\/(?:[A-Za-z0-9][A-Za-z0-9_-]*(?:\/[A-Za-z0-9][A-Za-z0-9_-]*)*)?$/.test(opts.path)) throw new UsageError(`--path ${opts.path} must be / or /folder[/sub]`);
  if (opts.field.length && opts.dom.length) throw new UsageError('--field (wire) and --dom (page) are exclusive');
  if (opts.field.length && !opts.match) throw new UsageError('--field needs --match <regex of the create request URL>');
  if (opts.match && !opts.field.length && !opts.check) throw new UsageError('--match needs at least one --field');
  const extractors = buildExtractors(opts.field.length ? opts.field : opts.dom, opts.name);
  if (!opts.check && !extractors.length) throw new UsageError('need --match + --field (wire) or --dom (page)');
  if (opts.name !== undefined && !NAME_RE.test(opts.name)) throw new UsageError(`--name ${opts.name} is not UPPER_SNAKE_CASE (PLAN §4b; the put tool lints the KIND)`);
  // Extractors mean a write is planned, --check included, so a rehearsal tests the metadata too;
  // a bare --check plans no write and needs none.
  if (extractors.length) {
    const { md, pageExp } = checkKeyMeta(opts);
    const until = md.expires === NO_EXPIRY ? pageExp : md.expires;
    if (until <= today) throw new UsageError(`the key would be dead on arrival: ${md.expires === NO_EXPIRY ? 'the rotate-by date in provider_name' : 'expires'} ${until} is not after today ${today}`);
  }
  return { opts, cdpUrl, extractors, mode: opts.field.length ? 'wire' : 'page' };
}

// [{ src, name }]: one entry per value to capture. The single-value form is a bare extractor plus
// --name; several values need `<src>=<NAME>` on every extractor and no --name.
export function buildExtractors(list, singleName) {
  const out = list.map(raw => {
    const m = NAMED_RE.exec(raw);
    return m ? { src: m[1], name: m[2] } : { src: raw, name: null };
  });
  if (out.length > 1 && out.some(e => !e.name)) throw new UsageError('several values: every --field/--dom must be <src>=<NAME>');
  if (out.length === 1 && !out[0].name) {
    if (!singleName) throw new UsageError('missing --name (or write the extractor as <src>=<NAME>)');
    out[0].name = singleName;
  } else if (singleName !== undefined && out.length) {
    throw new UsageError('--name goes with ONE bare extractor; with <src>=<NAME> drop --name');
  }
  const names = out.map(e => e.name);
  if (new Set(names).size !== names.length) throw new UsageError('two extractors name the same variable');
  for (const n of names) if (!NAME_RE.test(n)) throw new UsageError(`${n} is not UPPER_SNAKE_CASE (PLAN §4b; the put tool lints the KIND)`);
  return out;
}

// "a.b[0].c" -> value at that path, or undefined.
export function walkPath(node, path) {
  for (const part of path.split('.')) {
    const m = /^(.*?)(?:\[(\d+)\])?$/.exec(part);
    if (m[1]) node = node?.[m[1]];
    if (m[2] !== undefined) node = node?.[Number(m[2])];
  }
  return node;
}

// A wire extractor is one path, or several: `a|b` takes the first alternative that yields a value (a
// guess about the field name costs no second key), `a+b` joins the values with ':' (fal's key is
// `key_id:key_secret`). Paths use `.` and `[n]` only, so `|` and `+` are free.
export function resolveSrc(body, src) {
  for (const alt of src.split('|')) {
    const vals = alt.split('+').map(path => walkPath(body, path));
    if (vals.every(v => typeof v === 'string' && v.length)) return vals.join(':');
  }
  return undefined;
}

// Pull every wanted value out of one parsed JSON body. Returns the entries found and the NAMES
// (never values) of the ones that were not there.
export function pickFields(body, extractors) {
  const entries = [], missing = [];
  for (const e of extractors) {
    const v = resolveSrc(body, e.src);
    if (typeof v === 'string' && v.length) entries.push({ name: e.name, value: v }); else missing.push(e.name);
  }
  return { entries, missing };
}

// What a response looks like, for the "value MISSING" diagnosis: key names and JSON types only,
// three levels deep, at most 24 entries. A value never appears, not even its length.
export function describeShape(node, prefix = '', depth = 0, out = []) {
  if (!node || typeof node !== 'object' || depth >= 3) return out;
  for (const [k, v] of Object.entries(node)) {
    if (out.length >= 24) break;
    const p = `${prefix}${prefix ? '.' : ''}${k.replace(/[^A-Za-z0-9_-]/g, '?').slice(0, 32)}`;
    if (Array.isArray(v)) out.push(`${p}:array`);
    else if (v && typeof v === 'object') { out.push(`${p}:object`); describeShape(v, p, depth + 1, out); }
    else out.push(`${p}:${v === null ? 'null' : typeof v}`);
  }
  return out;
}

export function putArgs(tool, name, cfg) {
  const args = [tool, 'put', cfg.project, cfg.env, name, '--stdin', '--as', cfg.as, '--path', cfg.path];
  if (cfg.comment) args.push('--comment', cfg.comment);
  for (const m of cfg.meta) args.push('--meta', m);
  if (cfg.multiline) args.push('--multiline');
  return args;
}

const exited = child => new Promise(r => { child.on('exit', c => r(c ?? 1)); child.on('error', () => r(127)); });

// One `put --stdin` per entry, in order, stopping at the first failure. Returns
// { code, saved: [names], failed: name|null, skipped: [names] }: `saved` non-empty with a non-zero
// code is the partial case the caller must report (the key exists at the provider, one put is missing).
// The metadata gate runs again here, before the first spawn, for any caller that skipped parseArgs;
// it throws UsageError and nothing is written.
export async function runPuts(entries, cfg, deps = {}) {
  checkKeyMeta(cfg);
  const spawnFn = deps.spawn || spawn;
  const saved = [];
  for (let i = 0; i < entries.length; i++) {
    const { name, value } = entries[i];
    const child = spawnFn(cfg.python, putArgs(cfg.tool, name, cfg), { stdio: ['pipe', 'inherit', 'inherit'] });
    child.stdin.on('error', () => {});
    child.stdin.end(value + '\n');
    const code = await exited(child);
    if (code !== 0) return { code, saved, failed: name, skipped: entries.slice(i + 1).map(e => e.name) };
    saved.push(name);
  }
  return { code: 0, saved, failed: null, skipped: [] };
}

// --new-only: before anything is created at the provider, every target secret must be absent.
// `last4` prints a last4 on stdout when the secret exists; it is captured and thrown away.
// Returns { present: [names], error: [names] }.
export async function checkAbsent(names, cfg, deps = {}) {
  const spawnFn = deps.spawn || spawn;
  const present = [], error = [];
  for (const name of names) {
    const args = [cfg.tool, 'last4', cfg.project, cfg.env, name, '--as', cfg.as, '--path', cfg.path];
    const child = spawnFn(cfg.python, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let err = '';
    child.stdout.on('data', () => {});
    child.stderr.on('data', d => { err += d; });
    const code = await exited(child);
    if (code === 0) present.push(name);
    else if (!/has no secret/.test(err)) error.push(name);
  }
  return { present, error };
}
