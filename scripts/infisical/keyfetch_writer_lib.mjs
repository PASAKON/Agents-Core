// Browser-free seat reconciliation. All effects go through the injected API.
export const IDENTITY_CAP = 5; // tools/infisical_setup.py: IDENTITY_CAP; users also count.
export const WRITER = 'keyfetch-writer';
// Infisical's attach default is a 30-day token (2592000 s); `infisical_setup.py save` refuses a writer
// token that lives over a day, so the seat sets the lifetime itself.
export const WRITER_TOKEN_TTL = 3600;
const WRITER_AUTH = { accessTokenTTL: WRITER_TOKEN_TTL, accessTokenMaxTTL: WRITER_TOKEN_TTL };
export class SeatError extends Error {}

export function parseManifest(text) {
  const source = text.split('\n').map(line => line.split('#')[0]).join('\n').trim();
  const match = /^projects:\s*\[([^\]]*)\]\s*$/.exec(source);
  if (!match) throw new SeatError('manifest: expected projects flow list');
  return validateProjects(match[1].split(',').map(s => s.trim()));
}

function validateProjects(projects) {
  if (!Array.isArray(projects) || !projects.length || projects.some(p =>
    typeof p !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(p) ||
    ['org-infra', 'org-node'].includes(p.toLowerCase())) ||
    new Set(projects.map(p => p.toLowerCase())).size !== projects.length) {
    throw new SeatError('manifest: forbidden project, duplicate, or invalid name');
  }
  return projects;
}

// API messages are untrusted: do not echo arbitrary words, IDs, credentials, or bodies.
// Preserve a small diagnostic vocabulary; all other message content is redacted.
const WORDS = new Set('you are not allowed to access this resource permission denied unauthorized forbidden invalid request role identity project organization found already exists missing required internal server error bad too many requests rate limit exceeded'.split(' '));
export function safeMessage(value) {
  if (typeof value !== 'string') return '[redacted]';
  return value.slice(0, 300).split(/\s+/).map(word => WORDS.has(word.toLowerCase()) ? word : '[redacted]').join(' ');
}
export async function checked(api, step, method, path, body) {
  let response;
  try { response = await api(method, path, body); }
  catch { throw new SeatError(`${step}: transport failed`); }
  if (!Number.isInteger(response?.status) || response.status < 200 || response.status >= 300) {
    throw new SeatError(`${step}: HTTP ${Number.isInteger(response?.status) ? response.status : '?'} ${safeMessage(response?.json?.message)}`);
  }
  return response.json;
}
function rows(data, key) {
  if (!Array.isArray(data?.[key]) || (data.totalCount !== undefined && data.totalCount !== data[key].length)) {
    throw new SeatError(`read ${key}: incomplete list; stopped`);
  }
  return data[key];
}
function roleText(role) {
  return ['no-access', 'admin', 'member', 'viewer', 'custom'].includes(role) ? role : '[redacted role]';
}

export async function reconcileSeat({ api, orgId, projects, go = false, log = console.log }) {
  validateProjects(projects); // Must precede even the first read.
  const call = (step, method, path, body) => checked(api, step, method, path, body);
  const identities = rows(await call('read identities', 'GET', `/api/v1/identities?orgId=${encodeURIComponent(orgId)}`), 'identities');
  if (identities.some(m => !m?.identity?.id || !m.identity.name)) throw new SeatError('read identities: invalid row');
  const find = name => {
    const matches = identities.filter(m => m.identity.name === name);
    if (matches.length > 1) throw new SeatError(`read ${name}: duplicate identity`);
    return matches[0];
  };
  const setup = find('setup');
  let writer = find(WRITER);
  const users = rows(await call('read users', 'GET', `/api/v2/organizations/${orgId}/memberships`), 'users');
  // Count every returned membership, including pending invitations (conservative).
  const seats = identities.length + users.length - (setup ? 1 : 0) + (writer ? 0 : 1);
  log(`seats: identities=${identities.length} users=${users.length} after=${seats} cap=${IDENTITY_CAP}`);
  if (seats > IDENTITY_CAP) throw new SeatError('seats: over cap; no writes');
  if (writer && writer.role !== 'no-access') throw new SeatError(`${WRITER}: org role ${roleText(writer.role)}; stopped`);
  if (writer && !Array.isArray(writer.identity.authMethods)) throw new SeatError('keyfetch-writer: authMethods missing; stopped');
  const live = rows(await call('read projects', 'GET', `/api/v2/organizations/${orgId}/workspaces`), 'workspaces');
  const targets = projects.map(name => {
    const found = live.filter(p => p.name === name);
    if (found.length !== 1 || !found[0].id) throw new SeatError(`${name}: project missing or ambiguous; no writes`);
    return found[0];
  });
  const memberships = new Map();
  for (const p of targets) {
    const members = rows(await call(`${p.name} read membership`, 'GET', `/api/v1/projects/${p.id}/identity-memberships?limit=100`), 'identityMemberships');
    if (members.length >= 100) throw new SeatError(`${p.name}: membership page full; stopped`);
    memberships.set(p.id, members);
  }
  let secrets = [];
  if (setup) {
    secrets = rows(await call('setup read client secrets', 'GET', `/api/v1/auth/universal-auth/identities/${setup.identity.id}/client-secrets`), 'clientSecretData').filter(s => !s.isClientSecretRevoked);
    if (secrets.some(s => !s.id)) throw new SeatError('setup: invalid client secret row');
  }
  const mode = go ? 'GO' : 'dry run';
  log(`${mode}: setup revoke=${secrets.length} delete=${setup ? 1 : 0}`);
  if (go && setup) {
    for (const s of secrets) await call('setup revoke client secret', 'POST', `/api/v1/auth/universal-auth/identities/${setup.identity.id}/client-secrets/${s.id}/revoke`, {});
    await call('setup delete identity', 'DELETE', `/api/v1/identities/${setup.identity.id}`);
    log(`setup: revoked=${secrets.length} deleted=1`);
  }
  log(`${mode}: ${WRITER} ${writer ? 'exists' : 'create'} org role=no-access`);
  if (go && !writer) {
    const made = await call('keyfetch-writer create identity', 'POST', '/api/v1/identities', { name: WRITER, organizationId: orgId, role: 'no-access' });
    if (!made?.identity?.id) throw new SeatError('keyfetch-writer create: missing identity');
    writer = { identity: { ...made.identity, authMethods: [] }, role: 'no-access' };
  }
  // authMethods comes from the identity list; fail closed on unknown existing state.
  const methods = writer?.identity.authMethods;
  const attached = methods?.includes('universal-auth');
  let ttlOk = true;
  if (attached) {
    const ua = (await call('keyfetch-writer read universal-auth', 'GET', `/api/v1/auth/universal-auth/identities/${writer.identity.id}`))?.identityUniversalAuth;
    ttlOk = [ua?.accessTokenTTL, ua?.accessTokenMaxTTL].every(t => Number.isInteger(t) && t > 0 && t <= WRITER_TOKEN_TTL);
  }
  log(`${mode}: ${WRITER} universal-auth ${!attached ? 'attach' : ttlOk ? 'exists' : 'set token ttl'} token ttl=${WRITER_TOKEN_TTL}s client secrets minted=0`);
  if (go && !attached) await call('keyfetch-writer attach universal-auth', 'POST', `/api/v1/auth/universal-auth/identities/${writer.identity.id}`, WRITER_AUTH);
  if (go && !ttlOk) await call('keyfetch-writer universal-auth token ttl', 'PATCH', `/api/v1/auth/universal-auth/identities/${writer.identity.id}`, WRITER_AUTH);
  for (const p of targets) {
    const membership = memberships.get(p.id).find(m => m.identity?.id === writer?.identity.id);
    if (membership) {
      const roles = (membership.roles || []).map(r => roleText(r.customRoleSlug || r.role));
      log(`${p.name}: ${WRITER} existing roles=${roles.join(',') || 'unknown'}; left alone`);
    } else {
      log(`${mode}: ${p.name} add ${WRITER} role=member`);
      if (go) await call(`${p.name} add membership`, 'POST', `/api/v1/projects/${p.id}/identity-memberships/${writer.identity.id}`, { role: 'member' });
    }
  }
}
