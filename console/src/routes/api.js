import { Router } from 'express';
import { requireAuthApi } from '../auth/middleware.js';
import { listSessions, createSession } from '../tmux/sessions.js';
import { ROLES, slugify } from '../tmux/names.js';

export const apiRouter = Router();
// Scoped to /api/sessions specifically — apiRouter is mounted at the app
// root alongside pagesRouter, so an unscoped `apiRouter.use(requireAuthApi)`
// would intercept *every* request through this router (including `/` and
// `/login`) before pagesRouter ever got a chance to run.
apiRouter.use('/api/sessions', requireAuthApi);

apiRouter.get('/api/sessions', async (_req, res) => {
  try {
    const sessions = await listSessions();
    res.json({ sessions, roles: ROLES });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

apiRouter.post('/api/sessions', async (req, res) => {
  const { role, name, deviceLabel } = req.body || {};
  if (!ROLES.includes(role)) {
    return res.status(400).json({ error: `role must be one of: ${ROLES.join(', ')}` });
  }
  const slug = slugify(name);

  try {
    const result = await createSession(role, slug, deviceLabel || null);
    res.json({ ...result, url: `/agent/${result.role}/${result.slug}` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
