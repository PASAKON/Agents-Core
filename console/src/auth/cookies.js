import crypto from 'node:crypto';
import { config } from '../config.js';

export const COOKIE_NAME = 'mx_console';
const MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

export function signCookie(payloadObj) {
  const body = Buffer.from(JSON.stringify(payloadObj)).toString('base64url');
  const sig = crypto.createHmac('sha256', config.sessionSecret).update(body).digest('base64url');
  return `${body}.${sig}`;
}

export function verifyCookie(value) {
  if (!value || typeof value !== 'string') return null;
  const dot = value.lastIndexOf('.');
  if (dot === -1) return null;
  const body = value.slice(0, dot);
  const sig = value.slice(dot + 1);
  const expected = crypto.createHmac('sha256', config.sessionSecret).update(body).digest('base64url');
  const sigBuf = Buffer.from(sig);
  const expBuf = Buffer.from(expected);
  if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) return null;
  try {
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8'));
    if (typeof payload.exp === 'number' && Date.now() > payload.exp) return null;
    return payload;
  } catch {
    return null;
  }
}

export function makeSessionCookieValue(operatorId) {
  return signCookie({ sub: operatorId, iat: Date.now(), exp: Date.now() + MAX_AGE_MS });
}

export function serializeCookie(value) {
  const parts = [`${COOKIE_NAME}=${value}`, 'Path=/', 'HttpOnly', 'SameSite=Lax', `Max-Age=${Math.floor(MAX_AGE_MS / 1000)}`];
  if (config.cookieSecure) parts.push('Secure');
  return parts.join('; ');
}

export function clearCookie() {
  return `${COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`;
}

export function parseCookies(header) {
  const out = {};
  if (!header) return out;
  header.split(';').forEach((pair) => {
    const idx = pair.indexOf('=');
    if (idx === -1) return;
    const k = pair.slice(0, idx).trim();
    const v = pair.slice(idx + 1).trim();
    if (k) out[k] = decodeURIComponent(v);
  });
  return out;
}

export function cookieParserMiddleware(req, _res, next) {
  req.cookies = parseCookies(req.headers.cookie || '');
  next();
}
