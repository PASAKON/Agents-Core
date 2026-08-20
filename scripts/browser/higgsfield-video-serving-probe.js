// Probe: does Higgsfield actually serve video bytes right now (GH #92 diagnostic)?
// Run inside the target page's context via javascript_tool (or any CDP eval),
// NOT as a standalone node script -- it needs document/fetch in the page origin.
//
// Usage: navigate to the folder URL, wait for `[data-asset-id]` cards to
// populate, then run this. It hovers the first 3 cards to force their
// preview <video> to mount (cards render <img> only until hovered), then
// GETs each currentSrc with a 1KB Range request -- costs nothing, downloads
// nothing.
//
// Folder used for GH #92: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/folders/a0deb5ca-6aa8-45c0-90f2-3b7131fe575e

async function probeHiggsfieldVideoServing() {
  // 1. wait for grid
  for (let i = 0; i < 16; i++) {
    if (document.querySelectorAll('[data-asset-id]').length > 0) break;
    await new Promise(r => setTimeout(r, 1000));
  }
  const cardCount = document.querySelectorAll('[data-asset-id]').length;
  if (cardCount === 0) return { error: 'grid never populated' };

  // 2. force preview videos to mount (hover-only, no click)
  const cards = [...document.querySelectorAll('[data-asset-id]')].slice(0, 3);
  for (const c of cards) {
    c.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    c.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
  }
  for (let i = 0; i < 10; i++) {
    if (document.querySelectorAll('video').length > 0) break;
    await new Promise(r => setTimeout(r, 500));
  }

  // 3. harvest + probe
  const vids = [...document.querySelectorAll('video')];
  const urls = vids.map(v => v.currentSrc).filter(Boolean).slice(0, 3);
  if (urls.length === 0) return { error: 'no video currentSrc after hover', cardCount };

  const results = [];
  for (const u of urls) {
    try {
      const r = await fetch(u, { method: 'GET', headers: { Range: 'bytes=0-1023' } });
      results.push({ url: u.slice(-70), status: r.status, type: r.headers.get('content-type'), len: r.headers.get('content-length'), range: r.headers.get('content-range') });
    } catch (e) {
      results.push({ url: u.slice(-70), error: String(e) });
    }
  }

  const v0 = vids[0];
  const playerState = {
    readyState: v0.readyState,
    networkState: v0.networkState,
    error: v0.error ? { code: v0.error.code, message: v0.error.message } : null,
  };

  const serving = results.some(r => r.status === 200 || r.status === 206);
  return { cardCount, results, playerState, verdict: serving ? 'SERVING' : 'NOT SERVING' };
}

probeHiggsfieldVideoServing();
