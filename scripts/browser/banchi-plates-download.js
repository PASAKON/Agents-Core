// Replay notes for downloading every plate in a Google Flow "ตัวละคร" tab,
// once, to disk. Written for task-75926848 (banchi-plates-20260918).
//
// STATUS: proven for 2/20 assets, then Chrome's per-site "automatic downloads
// blocked" permission tripped and stayed tripped for the rest of the session
// (survived a full page reload and several minutes of elapsed time). This is
// NOT the documented "download button is dead, pull the CDN URL" video trap —
// it reproduces on Flow's own native per-tile download button too, once
// tripped. It needs a ONE-TIME human click on Chrome's blocked-downloads
// indicator in the real address bar ("Always allow multiple automatic
// downloads from flow.google.com"), which no available browser/computer-use
// tool can reach (browsers are click-blocked/read-tier for computer-use, and
// claude-in-chrome only reaches page content, never browser chrome).
//
// Once a human has granted that permission ONCE for flow.google.com, this
// whole flow should run to completion in one pass.

const STEPS = [
  // 1. Get into the project's ตัวละคร (Characters) tab as normal (see
  //    google-flow-ops skill for project navigation).

  // 2. In the page console (javascript_tool), define the helper:
  `
  function tileImg(handle){
    const label = [...document.querySelectorAll('*')].find(e=>e.children.length===0 && e.textContent.trim()===handle);
    let node = label;
    for(let i=0;i<8 && node;i++){ node = node.parentElement; }
    return node ? node.querySelector('img') : null;
  }
  async function processVisible(){
    window.__dl = window.__dl || new Set();
    const results = [];
    const labels = [...document.querySelectorAll('*')].filter(e=>e.children.length===0 && /^@[a-zA-Z0-9_]+$/.test(e.textContent.trim()));
    for (const label of labels){
      const handle = label.textContent.trim();
      if (window.__dl.has(handle)) continue;
      const img = tileImg(handle);
      if (!img || !img.naturalWidth) continue;
      try {
        const resp = await fetch(img.src);
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = handle.slice(1) + '.png';
        document.body.appendChild(a); a.click(); a.remove();
        await new Promise(r=>setTimeout(r,200));
        URL.revokeObjectURL(url);
        window.__dl.add(handle);
        results.push(handle+':'+blob.size);
      } catch(e){ results.push(handle+':ERR:'+e.message); }
    }
    return results;
  }
  `,

  // 3. IMPORTANT — the ตัวละคร grid is a cdk-virtual-scroll list. If
  //    document.hidden reads true (background/non-focused tab), scrollTop
  //    assignment moves the scrollbar but the DOM never re-renders new tiles.
  //    Fix confirmed working this run:
  `
  Object.defineProperty(document, 'hidden', {get: () => false, configurable: true});
  Object.defineProperty(document, 'visibilityState', {get: () => 'visible', configurable: true});
  document.dispatchEvent(new Event('visibilitychange'));
  `,
  // Setting document.hidden=false did NOT by itself fix rendering — what
  // actually worked was a REAL mouse-wheel scroll via the computer tool's
  // `scroll` action (dispatches a trusted wheel event), not a JS
  // `el.scrollTop = N` assignment (even with a dispatched 'scroll' event).
  // Do the visibility override for safety, but drive scrolling with
  // computer.scroll(direction:'down', amount:10) at a point inside the grid,
  // then call processVisible() again. Repeat until scrollTop stops changing
  // near el.scrollHeight (el = document.querySelector('.cdk-virtual-scrollable.page-container')).

  // 4. Verify completeness: collect all `@handle` leaf-text nodes across every
  //    scroll stop (top to bottom) into one Set, and diff against the task's
  //    checklist. Do NOT trust a single unscrolled snapshot — the virtualized
  //    grid renders only ~7 tiles at a time.

  // 5. After each processVisible() call, verify files actually landed on disk
  //    (`ls ~/Downloads`) — do NOT trust the JS "success" log alone. This run's
  //    JS reported 20/20 successful blob+click sequences, but only 2 files
  //    ever reached disk; the other 18 anchor.click() calls were silently
  //    swallowed by Chrome once the automatic-downloads gate tripped. Trust
  //    the filesystem, not the script's own return values — see the
  //    org memory rule "Our own ledger is not the system."
];

module.exports = { note: 'reference only, not directly executable — see comments above' };
