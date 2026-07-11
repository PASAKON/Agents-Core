const pathParts = window.location.pathname.split('/').filter(Boolean); // ['agent', role, slug]
const role = pathParts[1];
const slug = pathParts[2];

const term = new Terminal({
  fontFamily: 'Menlo, Monaco, "SF Mono", monospace',
  fontSize: 12.5,
  cursorBlink: true,
  convertEol: true,
  theme: {
    background: '#000000',
    foreground: '#c7c7c7',
    cursor: '#c7c7c7',
    red: '#c91b00',
    green: '#00c200',
    yellow: '#c7c400',
    blue: '#6871ff',
    magenta: '#ca30c7',
    cyan: '#00c5c7',
    black: '#000000',
    white: '#c7c7c7',
  },
});
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.open(document.getElementById('terminal'));
fitAddon.fit();

const winTitleEl = document.getElementById('win-title');
const connDotEl = document.getElementById('conn-dot');
winTitleEl.textContent = `${role}/${slug}`;

let ws;
let reconnectDelay = 1000;

function setConn(state) {
  connDotEl.className = 'conn-dot ' + state;
}

function sendResize() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
  }
}

function sendInput(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'input', data }));
  }
}

function connect() {
  setConn('connecting');
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${window.location.host}/ws/agent/${role}/${slug}`);

  ws.addEventListener('open', () => {
    setConn('up');
    reconnectDelay = 1000;
    sendResize();
  });

  ws.addEventListener('message', (evt) => {
    term.write(evt.data);
  });

  ws.addEventListener('close', () => {
    setConn('down');
    setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 10000);
  });

  ws.addEventListener('error', () => ws.close());
}

term.onData((data) => sendInput(data));

window.addEventListener('resize', () => {
  fitAddon.fit();
  sendResize();
});

// bottom composer bar — sends a full line + Enter, since iPhone soft
// keyboards don't have a convenient way to send raw keystrokes as you type.
const composerInput = document.getElementById('composer-input');

function sendComposerLine() {
  const text = composerInput.value;
  if (!text) return;
  sendInput(text + '\r');
  composerInput.value = '';
}

document.getElementById('btn-send').addEventListener('click', sendComposerLine);
composerInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    sendComposerLine();
  }
});

// helper-key row — raw control bytes iPhone keyboards can't otherwise send.
const KEY_BYTES = {
  esc: '\x1b',
  tab: '\t',
  'ctrl-c': '\x03',
  up: '\x1b[A',
  down: '\x1b[B',
  enter: '\r',
};
document.querySelectorAll('.key').forEach((btn) => {
  btn.addEventListener('click', () => {
    const bytes = KEY_BYTES[btn.dataset.key];
    if (bytes) sendInput(bytes);
  });
});

connect();
