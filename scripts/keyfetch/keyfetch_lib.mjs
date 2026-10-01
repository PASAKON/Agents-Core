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

export function parseArgs(argv) {
  const opts = { meta: [], field: [], dom: [], method: 'POST', click: '^(create|generate|new|add)\\b', as: 'setup', path: '/' };
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
  if (/^org-infra$/i.test(opts.project)) throw new UsageError('Org-Infra values are entered by the CEO only (PLAN §3b)');
  if (!/^\/(?:[A-Za-z0-9][A-Za-z0-9_-]*(?:\/[A-Za-z0-9][A-Za-z0-9_-]*)*)?$/.test(opts.path)) throw new UsageError(`--path ${opts.path} must be / or /folder[/sub]`);
  if (opts.field.length && opts.dom.length) throw new UsageError('--field (wire) and --dom (page) are exclusive');
  if (opts.field.length && !opts.match) throw new UsageError('--field needs --match <regex of the create request URL>');
  if (opts.match && !opts.field.length && !opts.check) throw new UsageError('--match needs at least one --field');
  const extractors = buildExtractors(opts.field.length ? opts.field : opts.dom, opts.name);
  if (!opts.check && !extractors.length) throw new UsageError('need --match + --field (wire) or --dom (page)');
  if (opts.name !== undefined && !NAME_RE.test(opts.name)) throw new UsageError(`--name ${opts.name} is not UPPER_SNAKE_CASE (PLAN §4b; the put tool lints the KIND)`);
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

// Pull every wanted value out of one parsed JSON body. Returns the entries found and the NAMES
// (never values) of the ones that were not there.
export function pickFields(body, extractors) {
  const entries = [], missing = [];
  for (const e of extractors) {
    const v = walkPath(body, e.src);
    if (typeof v === 'string' && v.length) entries.push({ name: e.name, value: v }); else missing.push(e.name);
  }
  return { entries, missing };
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
export async function runPuts(entries, cfg, deps = {}) {
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
