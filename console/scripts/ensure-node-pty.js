// node-pty ships a prebuild-or-build install step. In some environments
// (fresh Node ABI without a published prebuild) that step exits 0 without
// actually producing build/Release/pty.node. This postinstall guard checks
// for the compiled binary and forces a source rebuild via node-gyp if it's
// missing, so `npm install` reliably leaves node-pty usable.
import { existsSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ptyDir = path.resolve(__dirname, '..', 'node_modules', 'node-pty');
const binPath = path.join(ptyDir, 'build', 'Release', 'pty.node');

if (!existsSync(ptyDir)) {
  // node-pty not installed (e.g. running `npm install` with --omit=optional
  // in some CI variant) — nothing to do.
  process.exit(0);
}

if (existsSync(binPath)) {
  process.exit(0);
}

console.log('[console] node-pty native binary missing — rebuilding from source...');
try {
  execSync('npx --yes node-gyp rebuild', { cwd: ptyDir, stdio: 'inherit' });
  console.log('[console] node-pty rebuilt OK.');
} catch (err) {
  console.error('[console] node-pty rebuild failed:', err.message);
  console.error('[console] Live terminal attach (tmux bridge) will not work until this is fixed.');
  console.error('[console] Requires Xcode Command Line Tools (macOS) or build-essential (Linux) + python3.');
}
