import http from 'node:http';
import { createApp } from './app.js';
import { attachWebSocketServer } from './ws.js';
import { config } from './config.js';

const app = createApp();
const server = http.createServer(app);
attachWebSocketServer(server);

server.listen(config.port, () => {
  console.log(`[console] MoonieX Console listening on http://localhost:${config.port}`);
  console.log(`[console] org root: ${config.orgRoot}`);
  console.log(`[console] python:   ${config.pythonBin}`);
});
