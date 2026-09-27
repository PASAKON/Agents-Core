"""Read-only: open "My submissions" on the challenge page and print what our entry offers (edit / delete / resubmit),
without clicking any of it. Written 2026-09-27 to learn whether a submitted video can be replaced in place."""
import re, time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto("https://www.topview.ai/activity/topview-wan3-challenge", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    tab = page.get_by_text(re.compile(r"^\s*My submissions?\s*$", re.I))
    print("my-submissions elements:", tab.count())
    if tab.count():
        tab.first.click(); time.sleep(6)
    t = page.evaluate("() => document.body.innerText")
    i = t.find("THE SHADOW BELOW")
    print("found title:", i >= 0)
    if i >= 0:
        print("context:", t[max(0, i - 400):i + 600].replace("\n", " / "))
    # every clickable thing near the entry card: text, aria-label, title
    info = page.evaluate("""() => {
        const hit = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && /THE SHADOW BELOW/.test(e.textContent));
        if (!hit) return null;
        let card = hit; for (let k = 0; k < 8 && card.parentElement; k++) { card = card.parentElement;
            if (card.querySelectorAll('button, a, [role=button], svg').length >= 2) break; }
        const out = [];
        for (const el of card.querySelectorAll('button, a, [role=button], [class*=edit], [class*=Edit], [class*=more], [class*=More]'))
            out.push({tag: el.tagName, text: (el.innerText || '').trim().slice(0, 60), aria: el.getAttribute('aria-label'),
                      title: el.getAttribute('title'), cls: (el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className || '').slice(0, 80),
                      href: el.getAttribute('href')});
        return {cardText: card.innerText.slice(0, 500), controls: out};
    }""")
    print(info)
    page.close()
