import { WebSocketServer } from 'ws';
import { parseCookies, COOKIE_NAME, verifyCookie } from './auth/cookies.js';
import { getOperatorById } from './db.js';
import { buildSessionName, ROLES } from './tmux/names.js';
import { sessionExists } from './tmux/sessions.js';
import * as bridge from './tmux/bridge.js';

const ROUTE_RE = /^\/ws\/agent\/([a-z]+)\/([a-z0-9-]+)$/i;

export function attachWebSocketServer(server) {
  const wss = new WebSocketServer({ noServer: true });

  server.on('upgrade', async (req, socket, head) => {
    const url = new URL(req.url, 'http://localhost');
    const match = url.pathname.match(ROUTE_RE);
    if (!match) {
      socket.destroy();
      return;
    }
    const [, role, slug] = match;

    if (!ROLES.includes(role)) {
      socket.write('HTTP/1.1 404 Not Found\r\n\r\n');
      socket.destroy();
      return;
    }

    // Same auth guard as the page routes, applied to the WS upgrade —
    // an unauthenticated client can't attach to a live terminal even if it
    // guesses the URL.
    const cookies = parseCookies(req.headers.cookie || '');
    const payload = verifyCookie(cookies[COOKIE_NAME]);
    const operator = payload && getOperatorById(payload.sub);
    if (!operator) {
      socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
      socket.destroy();
      return;
    }

    const name = buildSessionName(role, slug);
    if (!(await sessionExists(name))) {
      socket.write('HTTP/1.1 404 Not Found\r\n\r\n');
      socket.destroy();
      return;
    }

    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit('connection', ws, { name });
    });
  });

  wss.on('connection', (ws, { name }) => {
    bridge.attach(name, ws);

    ws.on('message', (raw) => {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch {
        return;
      }
      if (msg.type === 'input' && typeof msg.data === 'string') {
        bridge.write(name, msg.data);
      } else if (msg.type === 'resize' && msg.cols && msg.rows) {
        bridge.resize(name, msg.cols, msg.rows);
      }
    });

    ws.on('close', () => bridge.detach(name, ws));
    ws.on('error', () => bridge.detach(name, ws));
  });

  return wss;
}
