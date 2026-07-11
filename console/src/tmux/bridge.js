import pty from 'node-pty';
import { config } from '../config.js';

// One node-pty process per tmux session name, fanned out to every attached
// WebSocket client. This is the key invariant from TASK.md: two browser
// tabs on the same session must show identical live output, and we must
// never spawn a second independent tmux session for a slug that already
// exists. Reusing a single `tmux attach-session` pty per name and
// broadcasting its output to N clients satisfies both — tmux itself never
// sees more than one attach client from this process, and the underlying
// tmux *session* (started once via sessions.createSession) is the actual
// source of truth other real `tmux attach` clients (e.g. on the Mac
// directly) would mirror against too.
const bridges = new Map();

function spawnAttach(name) {
  const term = pty.spawn('tmux', ['attach-session', '-t', name], {
    name: 'xterm-256color',
    cols: 80,
    rows: 24,
    cwd: config.orgRoot,
    env: process.env,
  });

  const entry = { pty: term, clients: new Set(), cols: 80, rows: 24 };
  bridges.set(name, entry);

  term.onData((data) => {
    for (const client of entry.clients) {
      if (client.readyState === client.OPEN) client.send(data);
    }
  });

  term.onExit(() => {
    for (const client of entry.clients) {
      if (client.readyState === client.OPEN) {
        client.send('\r\n\x1b[2m[console] session ended.\x1b[0m\r\n');
      }
    }
    bridges.delete(name);
  });

  return entry;
}

export function attach(name, ws) {
  const entry = bridges.get(name) || spawnAttach(name);
  entry.clients.add(ws);
  return entry;
}

export function detach(name, ws) {
  const entry = bridges.get(name);
  if (!entry) return;
  entry.clients.delete(ws);
  if (entry.clients.size === 0) {
    // Kill only our attach client — the tmux session itself keeps running
    // server-side (it was started detached via `tmux new-session -d`).
    entry.pty.kill();
    bridges.delete(name);
  }
}

export function write(name, data) {
  bridges.get(name)?.pty.write(data);
}

export function resize(name, cols, rows) {
  const entry = bridges.get(name);
  if (!entry || !cols || !rows) return;
  entry.cols = cols;
  entry.rows = rows;
  try {
    entry.pty.resize(cols, rows);
  } catch {
    // pty already exited between the check above and here — ignore.
  }
}

export function clientCount(name) {
  return bridges.get(name)?.clients.size || 0;
}
