import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const CONSOLE_ROOT = path.resolve(__dirname, '..');

const envPath = path.join(CONSOLE_ROOT, '.env');
if (existsSync(envPath)) {
  process.loadEnvFile(envPath);
}

function defaultPythonBin(orgRoot) {
  const venvPython = path.join(orgRoot, '.venv', 'bin', 'python');
  return existsSync(venvPython) ? venvPython : 'python3';
}

const port = Number(process.env.PORT || 4300);
const orgRoot = path.resolve(CONSOLE_ROOT, process.env.ORG_ROOT || '..');

export const config = {
  port,
  rpId: process.env.WEBAUTHN_RP_ID || 'localhost',
  rpName: process.env.WEBAUTHN_RP_NAME || 'MoonieX Console',
  origin: process.env.WEBAUTHN_ORIGIN || `http://localhost:${port}`,
  sessionSecret: process.env.SESSION_SECRET || 'dev-secret-change-me',
  dbPath: path.resolve(CONSOLE_ROOT, process.env.DB_PATH || './data/console.db'),
  orgRoot,
  pythonBin: process.env.PYTHON_BIN || defaultPythonBin(orgRoot),
  cookieSecure: process.env.COOKIE_SECURE === 'true',
  consoleRoot: CONSOLE_ROOT,
};
