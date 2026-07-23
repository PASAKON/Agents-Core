import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { buildSessionName, parseSessionName, ROLES } from './names.js';
import { roleCommand } from './command.js';
import { config } from '../config.js';
import { setSessionDevice, getSessionDevices } from '../db.js';

const execFileAsync = promisify(execFile);

// Pure parser, split out so it's unit-testable without shelling out to a
// real tmux server (see test/sessions.test.js).
export function parseSessionListOutput(stdout) {
  return stdout
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, created, attached] = line.split('\t');
      const parsed = parseSessionName(name);
      if (!parsed || !ROLES.includes(parsed.role)) return null;
      return {
        name,
        role: parsed.role,
        slug: parsed.slug,
        createdAt: created ? Number(created) * 1000 : null,
        attached: attached === '1',
      };
    })
    .filter(Boolean);
}

export async function listSessions() {
  let stdout;
  try {
    ({ stdout } = await execFileAsync('tmux', [
      'list-sessions',
      '-F',
      '#{session_name}\t#{session_created}\t#{session_attached}',
    ]));
  } catch (err) {
    // tmux exits 1 with "no server running on ..." when nothing has been
    // started yet — that's an empty session list, not an error.
    if (err.code === 1) return [];
    throw err;
  }
  const sessions = parseSessionListOutput(stdout);
  // Enrich with device labels from DB
  const deviceMap = Object.fromEntries(
    getSessionDevices().map((d) => [d.tmux_session_name, d.device_label]),
  );
  for (const s of sessions) {
    s.deviceLabel = deviceMap[s.name] || null;
  }
  return sessions;
}

export async function sessionExists(name) {
  try {
    await execFileAsync('tmux', ['has-session', '-t', name]);
    return true;
  } catch {
    return false;
  }
}

export async function createSession(role, slug, deviceLabel) {
  const name = buildSessionName(role, slug);
  if (await sessionExists(name)) {
    return { name, role, slug, created: false };
  }
  const command = roleCommand(role);
  await execFileAsync('tmux', ['new-session', '-d', '-s', name, '-c', config.orgRoot, command]);
  if (deviceLabel) {
    setSessionDevice(name, deviceLabel);
  }
  return { name, role, slug, created: true, deviceLabel: deviceLabel || null };
}
