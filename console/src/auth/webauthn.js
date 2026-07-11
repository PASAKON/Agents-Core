import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} from '@simplewebauthn/server';
import { config } from '../config.js';
import * as db from '../db.js';

// Registration/authentication challenges are short-lived and single-operator
// scoped for this MVP — an in-memory map is enough (no need for a DB table).
const challenges = new Map();
const CHALLENGE_TTL_MS = 5 * 60 * 1000;

function putChallenge(username, challenge) {
  challenges.set(username, { challenge, expires: Date.now() + CHALLENGE_TTL_MS });
}

function takeChallenge(username) {
  const entry = challenges.get(username);
  challenges.delete(username);
  if (!entry || entry.expires < Date.now()) return null;
  return entry.challenge;
}

export async function buildRegistrationOptions(username, operatorId) {
  const existing = db.getCredentialsForOperator(operatorId);
  const options = await generateRegistrationOptions({
    rpName: config.rpName,
    rpID: config.rpId,
    userName: username,
    attestationType: 'none',
    excludeCredentials: existing.map((c) => ({
      id: c.id,
      transports: c.transports ? JSON.parse(c.transports) : undefined,
    })),
    authenticatorSelection: { residentKey: 'preferred', userVerification: 'preferred' },
  });
  putChallenge(username, options.challenge);
  return options;
}

export async function verifyRegistration(username, response) {
  const expectedChallenge = takeChallenge(username);
  if (!expectedChallenge) throw new Error('registration challenge expired — try again');

  const verification = await verifyRegistrationResponse({
    response,
    expectedChallenge,
    expectedOrigin: config.origin,
    expectedRPID: config.rpId,
  });

  if (!verification.verified || !verification.registrationInfo) {
    throw new Error('passkey registration could not be verified');
  }
  return verification.registrationInfo;
}

export async function buildAuthenticationOptions(username) {
  const operator = db.getOperatorByUsername(username);
  const creds = operator ? db.getCredentialsForOperator(operator.id) : [];
  const options = await generateAuthenticationOptions({
    rpID: config.rpId,
    userVerification: 'preferred',
    allowCredentials: creds.map((c) => ({
      id: c.id,
      transports: c.transports ? JSON.parse(c.transports) : undefined,
    })),
  });
  putChallenge(username, options.challenge);
  return options;
}

export async function verifyAuthentication(username, response) {
  const expectedChallenge = takeChallenge(username);
  if (!expectedChallenge) throw new Error('login challenge expired — try again');

  const operator = db.getOperatorByUsername(username);
  if (!operator) throw new Error('unknown operator');

  const credential = db.getCredentialById(response.id);
  if (!credential || credential.operator_id !== operator.id) {
    throw new Error('unknown passkey credential');
  }

  const verification = await verifyAuthenticationResponse({
    response,
    expectedChallenge,
    expectedOrigin: config.origin,
    expectedRPID: config.rpId,
    credential: {
      id: credential.id,
      publicKey: Buffer.from(credential.public_key, 'base64url'),
      counter: credential.counter,
      transports: credential.transports ? JSON.parse(credential.transports) : undefined,
    },
  });

  if (!verification.verified) throw new Error('passkey login could not be verified');
  db.updateCredentialCounter(credential.id, verification.authenticationInfo.newCounter);
  return operator;
}
