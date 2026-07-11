import { COOKIE_NAME, verifyCookie } from './cookies.js';
import { getOperatorById } from '../db.js';

export function getAuthenticatedOperator(req) {
  const cookies = req.cookies || {};
  const payload = verifyCookie(cookies[COOKIE_NAME]);
  if (!payload) return null;
  return getOperatorById(payload.sub);
}

// Page routes (`/`, `/agent/*`) — unauthenticated requests redirect to /login.
export function requireAuth(req, res, next) {
  const operator = getAuthenticatedOperator(req);
  if (!operator) return res.redirect('/login');
  req.operator = operator;
  next();
}

// JSON API routes — unauthenticated requests get a 401, not a redirect.
export function requireAuthApi(req, res, next) {
  const operator = getAuthenticatedOperator(req);
  if (!operator) return res.status(401).json({ error: 'unauthenticated' });
  req.operator = operator;
  next();
}
