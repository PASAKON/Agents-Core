import { describe, it, expect } from 'vitest';
import { parseSessionListOutput } from '../src/tmux/sessions.js';
import { buildSessionName, parseSessionName, slugify } from '../src/tmux/names.js';

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
