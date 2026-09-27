"""On a video's Studio details page: video language -> English, title/description language -> English, category ->
Film & Animation; Save; reload and read the three controls back."""
import sys, time, json
from playwright.sync_api import sync_playwright
vid = sys.argv[1]
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def pick(page, trigger, option):
    trigger.click(); time.sleep(2)
    opt = page.get_by_role("option", name=option, exact=True)
    say("options named", option, ":", opt.count())
    opt.first.click(); time.sleep(1.5)
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto(f"https://studio.youtube.com/video/{vid}/edit", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    page.locator("#toggle-button").first.click(); time.sleep(3)
    pick(page, page.locator("#language-input ytcp-dropdown-trigger").first, "อังกฤษ")
    pick(page, page.locator("ytcp-form-language-input", has_text="ภาษาของชื่อและคำอธิบาย").locator("ytcp-dropdown-trigger").first, "อังกฤษ")
    pick(page, page.locator("#category ytcp-dropdown-trigger").first, "ภาพยนตร์และแอนิเมชัน")
    save = page.locator("#save").first
    say("save disabled:", save.get_attribute("aria-disabled"), save.inner_text().strip())
    save.click(); time.sleep(8)
    page.reload(wait_until="domcontentloaded"); time.sleep(12)
    page.locator("#toggle-button").first.click(); time.sleep(3)
    read = page.evaluate("""() => ['#language-input', '#category'].map(s => { const e = document.querySelector(s); return e ? e.innerText.replace(/\\s+/g,' ').trim() : null; })""")
    say("after save:", json.dumps(read, ensure_ascii=False))
    page.close()
