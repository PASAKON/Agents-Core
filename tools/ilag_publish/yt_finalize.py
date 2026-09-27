"""Finish the upload dialog that yt_studio_upload.py --stop-before-publish left open: read back every field, and with
--publish click Done (the visibility radio chosen earlier stays), then print the video link YouTube shows."""
import sys, time, json, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pages = [pg for pg in b.contexts[0].pages if "studio.youtube.com" in pg.url and pg.locator("ytcp-uploads-dialog").count()]
    if not pages:
        sys.exit("STOP: no open upload dialog")
    page = pages[-1]
    info = page.evaluate("""() => {
      const t = s => { const e = document.querySelector(s); return e ? e.innerText.trim() : null; };
      const links = [...document.querySelectorAll('ytcp-uploads-dialog a')].map(a => a.href).filter(h => /youtu\\.be|watch\\?v=|\\/video\\//.test(h));
      const radios = [...document.querySelectorAll('ytcp-uploads-dialog tp-yt-paper-radio-button')].filter(r => r.hasAttribute('checked') || r.getAttribute('aria-checked') === 'true').map(r => r.getAttribute('name'));
      return {title: t('#title-textarea #textbox'), progress: t('ytcp-video-upload-progress .progress-label') || t('.progress-label'),
              links: [...new Set(links)], checked: radios,
              thumb: !!document.querySelector('ytcp-uploads-dialog img[src^="data:"], ytcp-thumbnails-compact-editor-uploader img, #still-0 img')};
    }""")
    print(json.dumps(info, ensure_ascii=False))
    if "--publish" in sys.argv:
        page.locator("#done-button").first.click()
        time.sleep(8)
        after = page.evaluate("""() => { const d = document.querySelector('ytcp-video-share-dialog, ytcp-uploads-still-processing-dialog, tp-yt-paper-dialog');
            const links = [...document.querySelectorAll('a')].map(a => a.href).filter(h => /youtu\\.be\\/|watch\\?v=/.test(h));
            return {dialog: d ? d.innerText.trim().slice(0, 300) : null, links: [...new Set(links)].slice(0, 5)}; }""")
        print("AFTER:", json.dumps(after, ensure_ascii=False))
