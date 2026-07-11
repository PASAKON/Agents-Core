import http from 'node:http';
import https from 'node:https';
import { readFileSync } from 'node:fs';
import { createApp } from './app.js';
import { attachWebSocketServer } from './ws.js';
import { config } from './config.js';

const app = createApp();

// TLS is opt-in: when both cert + key files are configured the server boots
// as HTTPS (WebAuthn refuses to run over plain HTTP for a non-localhost
// origin). With neither set it stays plain HTTP, unchanged from local dev.
const tlsEnabled = Boolean(config.tlsCertFile && config.tlsKeyFile);
const server = tlsEnabled
  ? https.createServer(
      { cert: readFileSync(config.tlsCertFile), key: readFileSync(config.tlsKeyFile) },
      app
    )
  : http.createServer(app);

attachWebSocketServer(server);

// config.host unset => listen on all interfaces (original behaviour).
// On the box it's pinned to the tailnet IP so the public interface has
// nothing listening at all.
const listenArgs = config.host ? [config.port, config.host] : [config.port];
server.listen(...listenArgs, () => {
  const scheme = tlsEnabled ? 'https' : 'http';
  const bind = config.host || 'localhost';
  console.log(`[console] MoonieX Console listening on ${scheme}://${bind}:${config.port}`);
  console.log(`[console] org root: ${config.orgRoot}`);
  console.log(`[console] python:   ${config.pythonBin}`);
});
