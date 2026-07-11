import { Router } from 'express';
import * as db from '../db.js';
import * as webauthn from './webauthn.js';
import * as totp from './totp.js';
import { makeSessionCookieValue, serializeCookie, clearCookie } from './cookies.js';
import { getAuthenticatedOperator, requireAuthApi } from './middleware.js';

export const authRouter = Router();

// First operator ever created gets to self-register (bootstrap). After
// that, adding more credentials requires already being signed in — this is
// a single-operator-by-default console, not an open signup form.
function bootstrapOpen() {
  return db.getOperatorCount() === 0;
}

function resolveOperatorForEnrollment(req, username) {
  const authed = getAuthenticatedOperator(req);
  let operator = db.getOperatorByUsername(username);

  if (!operator) {
    if (!bootstrapOpen()) return { error: 'registration closed — operator already provisioned' };
    operator = db.createOperator(username);
    return { operator };
  }

  if (!authed || authed.id !== operator.id) {
    return { error: 'sign in first to add another credential' };
  }
  return { operator };
}

authRouter.post('/api/auth/webauthn/register-options', async (req, res) => {
  const { username } = req.body || {};
  if (!username) return res.status(400).json({ error: 'username required' });

  const { operator, error } = resolveOperatorForEnrollment(req, username);
  if (error) return res.status(401).json({ error });

  try {
    const options = await webauthn.buildRegistrationOptions(username, operator.id);
    res.json(options);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

authRouter.post('/api/auth/webauthn/register-verify', async (req, res) => {
  const { username, response } = req.body || {};
  if (!username || !response) return res.status(400).json({ error: 'username and response required' });

  const operator = db.getOperatorByUsername(username);
  if (!operator) return res.status(400).json({ error: 'unknown operator — call register-options first' });

  try {
    const info = await webauthn.verifyRegistration(username, response);
    db.addCredential({
      id: info.credential.id,
      operatorId: operator.id,
      publicKey: Buffer.from(info.credential.publicKey).toString('base64url'),
      counter: info.credential.counter,
      transports: info.credential.transports ? JSON.stringify(info.credential.transports) : null,
      deviceType: info.credentialDeviceType,
      backedUp: info.credentialBackedUp,
    });
    res.setHeader('Set-Cookie', serializeCookie(makeSessionCookieValue(operator.id)));
    res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

authRouter.post('/api/auth/webauthn/login-options', async (req, res) => {
  const { username } = req.body || {};
  if (!username) return res.status(400).json({ error: 'username required' });

  const operator = db.getOperatorByUsername(username);
  if (!operator) return res.status(400).json({ error: 'unknown operator' });

  try {
    const options = await webauthn.buildAuthenticationOptions(username);
    res.json(options);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

authRouter.post('/api/auth/webauthn/login-verify', async (req, res) => {
  const { username, response } = req.body || {};
  if (!username || !response) return res.status(400).json({ error: 'username and response required' });

  try {
    const operator = await webauthn.verifyAuthentication(username, response);
    res.setHeader('Set-Cookie', serializeCookie(makeSessionCookieValue(operator.id)));
    res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

authRouter.post('/api/auth/totp/setup', async (req, res) => {
  const { username } = req.body || {};
  if (!username) return res.status(400).json({ error: 'username required' });

  const { operator, error } = resolveOperatorForEnrollment(req, username);
  if (error) return res.status(401).json({ error });

  const secret = totp.createTotpSecret();
  db.setTotpSecret(operator.id, secret);
  const uri = await totp.totpProvisioningUri(username, secret);
  res.json({ secret, uri });
});

authRouter.post('/api/auth/totp/verify', async (req, res) => {
  const { username, token } = req.body || {};
  if (!username || !token) return res.status(400).json({ error: 'username and token required' });

  const operator = db.getOperatorByUsername(username);
  const record = operator && db.getTotpSecret(operator.id);
  if (!operator || !record) return res.status(400).json({ error: 'TOTP not set up for this operator' });

  const ok = await totp.verifyTotpToken(token, record.secret);
  if (!ok) return res.status(401).json({ error: 'invalid code' });

  res.setHeader('Set-Cookie', serializeCookie(makeSessionCookieValue(operator.id)));
  res.json({ ok: true });
});

authRouter.post('/api/auth/logout', requireAuthApi, (_req, res) => {
  res.setHeader('Set-Cookie', clearCookie());
  res.json({ ok: true });
});

authRouter.get('/api/auth/status', (req, res) => {
  const operator = getAuthenticatedOperator(req);
  res.json({
    authenticated: Boolean(operator),
    username: operator?.username || null,
    bootstrap: bootstrapOpen(),
  });
});
