import { describe, it, expect, beforeAll } from 'vitest';
import { parseSessionListOutput } from '../src/tmux/sessions.js';
import { buildSessionName, parseSessionName, slugify } from '../src/tmux/names.js';
import { openDb, setDb, setSessionDevice, getSessionDevices } from '../src/db.js';

beforeAll(() => {
  setDb(openDb(':memory:'));
});

describe('parseSessionListOutput', () => {
  it('parses tmux ls -F output into role/slug objects', () => {
    const stdout = [
      'cto-contabo-migration\t1750000000\t1',
      'cto-trader-mindset\t1750000100\t0',
      'cmo-geo-wave2\t1750000200\t0',
    ].join('\n');

    const sessions = parseSessionListOutput(stdout);

    expect(sessions).toEqual([
      { name: 'cto-contabo-migration', role: 'cto', slug: 'contabo-migration', createdAt: 1750000000000, attached: true },
      { name: 'cto-trader-mindset', role: 'cto', slug: 'trader-mindset', createdAt: 1750000100000, attached: false },
      { name: 'cmo-geo-wave2', role: 'cmo', slug: 'geo-wave2', createdAt: 1750000200000, attached: false },
    ]);
  });

  it('drops sessions whose role is not a known console role', () => {
    const stdout = 'unrelated-devwork\t1750000000\t0\ncto-ok\t1750000000\t0';
    const sessions = parseSessionListOutput(stdout);
    expect(sessions).toHaveLength(1);
    expect(sessions[0].name).toBe('cto-ok');
  });

  it('ignores blank lines and trailing newline', () => {
    const stdout = '\ncto-a\t1\t0\n\n';
    const sessions = parseSessionListOutput(stdout);
    expect(sessions).toHaveLength(1);
  });

  it('returns an empty array for empty input', () => {
    expect(parseSessionListOutput('')).toEqual([]);
  });
});

describe('buildSessionName / parseSessionName', () => {
  it('round-trips role + slug through a session name', () => {
    const name = buildSessionName('cto', 'contabo-migration');
    expect(name).toBe('cto-contabo-migration');
    expect(parseSessionName(name)).toEqual({ role: 'cto', slug: 'contabo-migration', name });
  });

  it('splits on the first dash only, so slugs may contain dashes', () => {
    expect(parseSessionName('cmo-geo-wave2')).toEqual({ role: 'cmo', slug: 'geo-wave2', name: 'cmo-geo-wave2' });
  });

  it('returns null for names without a dash', () => {
    expect(parseSessionName('nodash')).toBeNull();
  });
});

describe('slugify', () => {
  it('lowercases and dash-joins arbitrary input', () => {
    expect(slugify('Contabo Migration!!')).toBe('contabo-migration');
  });

  it('falls back to a generated slug for empty input', () => {
    expect(slugify('')).toMatch(/^session-/);
    expect(slugify(undefined)).toMatch(/^session-/);
  });
});

describe('session_devices', () => {
  it('persists a device label for a session', () => {
    setSessionDevice('cto-migration', 'iPhone #KS87U');
    const devices = getSessionDevices();
    const found = devices.find((d) => d.tmux_session_name === 'cto-migration');
    expect(found).toBeDefined();
    expect(found.device_label).toBe('iPhone #KS87U');
  });

  it('updates device label on upsert (same session name)', () => {
    setSessionDevice('cto-migration', 'iPhone #KS87U');
    setSessionDevice('cto-migration', 'Mac #ABC12');
    const devices = getSessionDevices();
    const rows = devices.filter((d) => d.tmux_session_name === 'cto-migration');
    expect(rows).toHaveLength(1);
    expect(rows[0].device_label).toBe('Mac #ABC12');
  });

  it('stores multiple sessions with different labels', () => {
    setSessionDevice('cto-alpha', 'iPhone #KS87U');
    setSessionDevice('cmo-beta', 'Mac #ABC12');
    const devices = getSessionDevices();
    expect(devices.length).toBeGreaterThanOrEqual(2);
    expect(devices.find((d) => d.tmux_session_name === 'cto-alpha').device_label).toBe('iPhone #KS87U');
    expect(devices.find((d) => d.tmux_session_name === 'cmo-beta').device_label).toBe('Mac #ABC12');
  });

  it('returns empty array when no devices stored', () => {
    // Fresh in-memory DB for this check
    const freshDb = openDb(':memory:');
    setDb(freshDb);
    const devices = getSessionDevices();
    expect(devices).toEqual([]);
    // Restore original for other tests
    setDb(openDb(':memory:'));
  });
});
