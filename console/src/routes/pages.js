import { Router } from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { requireAuth, getAuthenticatedOperator } from '../auth/middleware.js';
import { ROLES } from '../tmux/names.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.resolve(__dirname, '..', '..', 'public');

export const pagesRouter = Router();

pagesRouter.get('/login', (req, res) => {
  // Already signed in — no need to show the login screen again.
  if (getAuthenticatedOperator(req)) return res.redirect('/');
  res.sendFile(path.join(PUBLIC_DIR, 'login.html'));
});

pagesRouter.get('/', requireAuth, (_req, res) => {
  res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
});

pagesRouter.get('/agent/:role/:slug', requireAuth, (req, res) => {
  if (!ROLES.includes(req.params.role)) {
    return res.status(404).send('unknown role');
  }
  res.sendFile(path.join(PUBLIC_DIR, 'chat.html'));
});
