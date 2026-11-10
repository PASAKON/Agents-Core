// Minimal raw-CDP client (Node >= 22, global WebSocket). No Playwright: connect_over_cdp
// hangs on winbox Chrome 9226 when any other page is frozen. Own tab only: open with
// newTab(), close in finally with closeTab().
export const PORT = process.env.CDP_PORT || '9226';
const base = `http://127.0.0.1:${PORT}`;

export async function newTab(url = 'about:blank') {
  const r = await fetch(`${base}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
  return await r.json(); // {id, webSocketDebuggerUrl}
}
export async function closeTab(id) { try { await fetch(`${base}/json/close/${id}`); } catch {} }
export async function listTabs() { return (await fetch(`${base}/json/list`)).json(); }

export class Tab {
  constructor(info) { this.info = info; this.id = info.id; this.n = 0; this.pending = new Map(); this.events = []; }
  async open() {
    this.ws = new WebSocket(this.info.webSocketDebuggerUrl);
    await new Promise((res, rej) => { this.ws.onopen = res; this.ws.onerror = rej; });
    this.ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && this.pending.has(d.id)) {
        const { res, rej } = this.pending.get(d.id); this.pending.delete(d.id);
        d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result);
      } else if (d.method) this.events.push(d);
    };
    await this.send('Page.enable'); await this.send('DOM.enable'); await this.send('Runtime.enable');
    // background tabs paint no frames; keep layout alive
    await this.send('Emulation.setFocusEmulationEnabled', { enabled: true }).catch(() => {});
    return this;
  }
  send(method, params = {}, timeoutMs = 60000) {
    const id = ++this.n;
    return new Promise((res, rej) => {
      const t = setTimeout(() => { this.pending.delete(id); rej(new Error('timeout ' + method)); }, timeoutMs);
      this.pending.set(id, { res: (v) => { clearTimeout(t); res(v); }, rej: (e) => { clearTimeout(t); rej(e); } });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async eval(expr, timeoutMs = 60000) {
    const r = await this.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, timeoutMs);
    if (r.exceptionDetails) throw new Error('eval: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
    return r.result.value;
  }
  async goto(url, waitMs = 6000) {
    await this.send('Page.navigate', { url }, 45000).catch(() => {});
    await sleep(waitMs);
    await this.frame();
  }
  async frame() { // force a frame so layout/evaluate do not stall in a background tab
    await this.send('Page.captureScreenshot', { format: 'jpeg', quality: 10 }, 20000).catch(() => {});
  }
  async shot(path, fs) {
    const r = await this.send('Page.captureScreenshot', { format: 'png' }, 30000);
    (fs || (await import('node:fs'))).writeFileSync(path, Buffer.from(r.data, 'base64'));
  }
  async setFiles(selector, files) { // selector must resolve in the main document (light DOM or via pierce)
    const { root } = await this.send('DOM.getDocument', { depth: -1, pierce: true });
    const { nodeId } = await this.send('DOM.querySelector', { nodeId: root.nodeId, selector });
    if (!nodeId) throw new Error('no node ' + selector);
    await this.send('DOM.setFileInputFiles', { files, nodeId });
  }
  async setFilesEl(js, files) { // js expression returning the <input type=file> (works through shadow DOM)
    const r = await this.send('Runtime.evaluate', { expression: js });
    if (!r.result.objectId) throw new Error('setFilesEl: no element for ' + js.slice(0, 80));
    await this.send('DOM.setFileInputFiles', { files, objectId: r.result.objectId });
  }
  async chooseFile(clickJs, files, waitMs = 15000) { // trusted click on an Upload button, answer the native chooser over CDP
    await this.send('Page.setInterceptFileChooserDialog', { enabled: true });
    this.events = this.events.filter((e) => e.method !== 'Page.fileChooserOpened');
    await this.clickEl(clickJs);
    const t0 = Date.now(); let ev;
    while (Date.now() - t0 < waitMs && !(ev = this.events.find((e) => e.method === 'Page.fileChooserOpened'))) await sleep(200);
    if (!ev) throw new Error('chooseFile: no file chooser opened');
    await this.send('DOM.setFileInputFiles', { files, backendNodeId: ev.params.backendNodeId });
    await this.send('Page.setInterceptFileChooserDialog', { enabled: false });
  }
  async mouse(x, y) {
    for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
      await this.send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1, buttons: type === 'mousePressed' ? 1 : 0 });
  }
  async clickEl(js) { // js expression returning an element; clicks its centre with a trusted event
    const box = await this.eval(`(()=>{const e=(${js});if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);
    if (!box || !box.w) throw new Error('clickEl: not found/visible: ' + js.slice(0, 80));
    await this.mouse(box.x, box.y);
    return box;
  }
  close() { try { this.ws.close(); } catch {} }
}
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
