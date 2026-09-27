"""Read-only probe of the TopView Wan3 Challenge submission form: open the challenge page, list buttons; with --open,
click the submit-work button and list the form's fields (labels, input types). Types nothing, submits nothing."""
import sys, time, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto("https://www.topview.ai/activity/topview-wan3-challenge", wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    btns = page.evaluate("""() => [...document.querySelectorAll('button, a[role=button], [role=button]')]
        .filter(e => e.offsetParent !== null).map(e => (e.innerText||'').trim()).filter(t => t && t.length < 40)""")
    print("BUTTONS:", json.dumps(btns[:40], ensure_ascii=False))
    if "--open" in sys.argv:
        cand = page.get_by_role("button", name=sys.argv[sys.argv.index("--open") + 1]).first
        cand.click(); time.sleep(6)
        fields = page.evaluate("""() => [...document.querySelectorAll('input, textarea, [contenteditable=true]')]
            .filter(e => e.offsetParent !== null || e.type === 'file')
            .map(e => { const l = e.closest('div') ; return [e.tagName, e.type || '', e.name || '', e.placeholder || '',
                        e.accept || '', (e.labels && e.labels[0] ? e.labels[0].innerText : '')] })""")
        for f in fields: print("FIELD:", json.dumps(f, ensure_ascii=False))
        labels = page.evaluate("""() => [...document.querySelectorAll('label, [class*=label], [class*=title]')]
            .filter(e => e.offsetParent !== null).map(e => (e.innerText||'').trim()).filter(t => t && t.length < 80)""")
        print("LABELS:", json.dumps(labels[:60], ensure_ascii=False))
    page.close()
