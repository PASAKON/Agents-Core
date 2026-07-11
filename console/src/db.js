import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { config } from './config.js';

// Vite/vitest's static-import resolver doesn't yet recognize `node:sqlite`
// as a builtin (it's a newer addition than their hardcoded builtin list),
// so it tries to resolve it as an npm package named "sqlite" and fails.
// process.getBuiltinModule() is a runtime lookup, not a static specifier,
// so it sidesteps that entirely — works identically under `node` and under
// vitest.
const { DatabaseSync } = process.getBuiltinModule('node:sqlite');

let db;

export function openDb(dbPath = config.dbPath) {
  if (dbPath !== ':memory:') {
    mkdirSync(dirname(dbPath), { recursive: true });
  }
  const conn = new DatabaseSync(dbPath);
  conn.exec(`
    CREATE TABLE IF NOT EXISTS operators (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS webauthn_credentials (
      id TEXT PRIMARY KEY,
      operator_id INTEGER NOT NULL REFERENCES operators(id),
      public_key TEXT NOT NULL,
      counter INTEGER NOT NULL DEFAULT 0,
      transports TEXT,
      device_type TEXT,
      backed_up INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS totp_secrets (
      operator_id INTEGER PRIMARY KEY REFERENCES operators(id),
      secret TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
  return conn;
}

function getDb() {
  if (!db) db = openDb();
  return db;
}

// Allows tests to swap in an isolated (e.g. in-memory) database.
export function setDb(conn) {
  db = conn;
}

export function getOperatorCount() {
  return getDb().prepare('SELECT COUNT(*) AS c FROM operators').get().c;
}

export function createOperator(username) {
  const info = getDb().prepare('INSERT INTO operators (username) VALUES (?)').run(username);
  return getOperatorById(Number(info.lastInsertRowid));
}

export function getOperatorByUsername(username) {
  return getDb().prepare('SELECT * FROM operators WHERE username = ?').get(username) || null;
}

export function getOperatorById(id) {
  if (id === undefined || id === null) return null;
  return getDb().prepare('SELECT * FROM operators WHERE id = ?').get(id) || null;
}

export function addCredential({ id, operatorId, publicKey, counter, transports, deviceType, backedUp }) {
  getDb()
    .prepare(
      `INSERT INTO webauthn_credentials (id, operator_id, public_key, counter, transports, device_type, backed_up)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .run(id, operatorId, publicKey, counter, transports ?? null, deviceType ?? null, backedUp ? 1 : 0);
}

export function getCredentialsForOperator(operatorId) {
  return getDb().prepare('SELECT * FROM webauthn_credentials WHERE operator_id = ?').all(operatorId);
}

export function getCredentialById(id) {
  return getDb().prepare('SELECT * FROM webauthn_credentials WHERE id = ?').get(id) || null;
}

export function updateCredentialCounter(id, counter) {
  getDb().prepare('UPDATE webauthn_credentials SET counter = ? WHERE id = ?').run(counter, id);
}

export function setTotpSecret(operatorId, secret) {
  getDb()
    .prepare(
      `INSERT INTO totp_secrets (operator_id, secret) VALUES (?, ?)
       ON CONFLICT(operator_id) DO UPDATE SET secret = excluded.secret`
    )
    .run(operatorId, secret);
}

export function getTotpSecret(operatorId) {
  return getDb().prepare('SELECT * FROM totp_secrets WHERE operator_id = ?').get(operatorId) || null;
}
