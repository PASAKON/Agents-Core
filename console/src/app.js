import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cookieParserMiddleware } from './auth/cookies.js';
import { authRouter } from './auth/routes.js';
import { pagesRouter } from './routes/pages.js';
import { apiRouter } from './routes/api.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONSOLE_DIR = path.resolve(__dirname, '..');
const PUBLIC_DIR = path.join(CONSOLE_DIR, 'public');
const NODE_MODULES = path.join(CONSOLE_DIR, 'node_modules');

export function createApp() {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json());
  app.use(cookieParserMiddleware);

  // Browser-side vendor bundles served straight out of node_modules — no
  // bundler needed for this MVP (xterm.js and simplewebauthn both ship
  // ready-to-serve browser builds).
  app.use('/vendor/xterm', express.static(path.join(NODE_MODULES, '@xterm', 'xterm')));
  app.use('/vendor/xterm-addon-fit', express.static(path.join(NODE_MODULES, '@xterm', 'addon-fit')));
  app.use(
    '/vendor/simplewebauthn-browser',
    express.static(path.join(NODE_MODULES, '@simplewebauthn', 'browser', 'dist', 'bundle'))
  );

  app.use('/css', express.static(path.join(PUBLIC_DIR, 'css')));
  app.use('/js', express.static(path.join(PUBLIC_DIR, 'js')));

  app.use(authRouter);
  app.use(apiRouter);
  app.use(pagesRouter);

  app.use((_req, res) => res.status(404).send('not found'));

  return app;
}
