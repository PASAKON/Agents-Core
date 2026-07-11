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
  // Interface to bind to. Unset => Node's default (all interfaces / 0.0.0.0),
  // preserving the original local-dev behaviour. Deploys set this to a
  // specific interface IP (e.g. the tailnet IP) so nothing listens on the
  // public interface at all — see console/deploy + scripts/console-deploy.sh.
  host: process.env.HOST || undefined,
  // Optional TLS. When both files are set the server boots as HTTPS
  // (required by WebAuthn for a non-localhost origin); otherwise plain HTTP
  // for local dev. Paths point at a tailscale-issued cert/key on the box.
  tlsCertFile: process.env.TLS_CERT_FILE || '',
  tlsKeyFile: process.env.TLS_KEY_FILE || '',
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
