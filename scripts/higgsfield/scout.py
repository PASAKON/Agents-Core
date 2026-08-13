#!/usr/bin/env python3
"""Recon Higgsfield Seedance gen page over CDP. READ-ONLY — dumps interactive elements.

Usage: ensure Chrome is running with --remote-debugging-port=9222 and you are logged
into higgsfield.ai with the seedance gen page open (or this will open it).
Run: /Users/gob/Projects/Agents/.venv/bin/python scripts/higgsfield/scout.py
"""
import json
import sys
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
GEN_URL = "https://higgsfield.ai/ai/video?model=seedance_2_0"


def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP)
        except Exception as e:
            print("CDP_CONNECT_FAILED:", e, file=sys.stderr)
            print("Did you launch Chrome with --remote-debugging-port=9222?", file=sys.stderr)
            sys.exit(1)

        ctx = browser.contexts[0] if browser.contexts else browser.new_context()

        # find existing higgsfield tab, else open one
        page = None
        for pg in ctx.pages:
            if "higgsfield.ai" in pg.url:
                page = pg
                break
        if page is None:
            page = ctx.new_page()
            page.goto(GEN_URL, wait_until="domcontentloaded")

        print("TAB_URL:", page.url)
        try:
            print("TITLE:", page.title())
        except Exception as e:
            print("TITLE_ERR:", e)

        page.wait_for_timeout(4000)  # let SPA hydrate

        # dump visible interactive elements
        els = page.evaluate(
            """() => {
              const out = [];
              const sel = 'input, textarea, select, button, [role=button], [role=combobox], a[href], [contenteditable=true]';
              document.querySelectorAll(sel).forEach(n => {
                const r = n.getBoundingClientRect();
                out.push({
                  tag: n.tagName.toLowerCase(),
                  type: n.type || null,
                  role: n.getAttribute('role'),
                  name: n.name || null,
                  id: n.id || null,
                  cls: (n.className && n.className.toString) ? n.className.toString().slice(0,140) : null,
                  text: (n.innerText||n.value||'').trim().slice(0,100),
                  ph: n.placeholder || null,
                  aria: n.getAttribute('aria-label') || null,
                  href: n.getAttribute('href') ? n.getAttribute('href').slice(0,80) : null,
                  vis: !!(r.width && r.height),
                  x: Math.round(r.x), y: Math.round(r.y),
                });
              });
              return out;
            }"""
        )
        vis = [e for e in els if e.get("vis")]
        print("VISIBLE_INTERACTIVE_COUNT:", len(vis))
        print("ELEMENTS_JSON_START")
        print(json.dumps(vis, ensure_ascii=False, indent=2))
        print("ELEMENTS_JSON_END")

        # body text snippet — detect login state / quota wording
        body = page.evaluate("() => (document.body.innerText||'').slice(0,4000)")
        print("---BODY_SNIPPET_START---")
        print(body)
        print("---BODY_SNIPPET_END---")


if __name__ == "__main__":
    main()
