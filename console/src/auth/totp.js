import { generateSecret, generate, verify, generateURI } from 'otplib';
import { config } from '../config.js';

export function createTotpSecret() {
  return generateSecret();
}

export async function currentTotpToken(secret) {
  return generate({ secret, type: 'totp' });
}

export async function verifyTotpToken(token, secret) {
  const result = await verify({ token: String(token), secret, type: 'totp' });
  return Boolean(result?.valid);
}

export async function totpProvisioningUri(username, secret) {
  return generateURI({ secret, type: 'totp', label: username, issuer: config.rpName });
}
