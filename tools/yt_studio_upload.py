"""Upload one video through YouTube Studio in the winbox automation Chrome (CDP), for channels the Data API cannot
post as (ILAG Studio is not in the OAuth chooser). Zero-model: Playwright only; every step prints what it saw.

    python yt_studio_upload.py --channel-id UC... --video F.mp4 --title T --description-file D.txt \
        [--thumbnail T.jpg] [--tags "a,b"] [--altered yes|no] [--visibility PUBLIC|UNLISTED|PRIVATE] [--stop-before-publish]

Built 2026-09-27 for THE SHADOW BELOW (CEO: "อัปขึ้นช่อง ILAG แบบ Public ... คุณทำเอง"). Selectors were read live from
the Thai-locale Studio that morning (the upload entry is #upload-icon on the channel dashboard; the old #create-icon
is gone). The switch to the channel happens first through youtube.com/channel_switcher, because Studio opens on
whichever channel the Google account last used. Nothing is published unless --visibility reaches the Done click, and
--stop-before-publish leaves the video as a draft with every field filled.
"""
import argparse, sys, time
from playwright.sync_api import sync_playwright


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def set_file_local(page, selector, path):
    """Point a file input at a file on the BROWSER's disk. Playwright's set_input_files refuses files over 50 MB when
    connected over CDP ("not co-located", measured 2026-09-27 with a 1.2 GB video on the same machine); CDP's
    DOM.setFileInputFiles makes Chrome read the path itself, so nothing is transferred."""
    cdp = page.context.new_cdp_session(page)
    root = cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})["root"]["nodeId"]
    node = cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
    if not node:
        raise SystemExit(f"STOP: no {selector}")
    cdp.send("DOM.setFileInputFiles", {"files": [path], "nodeId": node})
    cdp.detach()


def fill_box(page, sel, text):
    box = page.locator(sel).first
    box.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    # Synthetic paste: typing a multi-line text key by key is slow and has been lossy in other editors (Lexical).
    page.evaluate("""([sel, text]) => { const el = document.querySelector(sel);
        const dt = new DataTransfer(); dt.setData('text/plain', text);
        el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }""",
                  [sel, text])
    time.sleep(0.8)
    got = box.inner_text().strip()
    say(f"{sel}: {len(got)} chars (wanted {len(text)})")
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default="http://127.0.0.1:9224")
    ap.add_argument("--channel-name", default="ILAG Studio")
    ap.add_argument("--channel-id", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--description-file", required=True)
    ap.add_argument("--thumbnail")
    ap.add_argument("--tags", default="")
    ap.add_argument("--altered", choices=["yes", "no"], default="yes")
    ap.add_argument("--visibility", choices=["PUBLIC", "UNLISTED", "PRIVATE"], default="PRIVATE")
    ap.add_argument("--stop-before-publish", action="store_true")
    a = ap.parse_args()
    desc = open(a.description_file, encoding="utf-8").read().strip()

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(a.cdp)
        page = b.contexts[0].new_page()
        page.set_viewport_size({"width": 1400, "height": 1000})
        page.goto("https://www.youtube.com/channel_switcher", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        page.get_by_text(a.channel_name, exact=True).first.click()
        time.sleep(6)
        page.goto(f"https://studio.youtube.com/channel/{a.channel_id}", wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        name = page.evaluate("() => (document.querySelector('#entity-name') || {}).innerText")
        say("studio channel:", name)
        if not name or a.channel_name not in name:
            sys.exit(f"STOP: Studio is on {name!r}, not {a.channel_name!r}")

        page.locator("#upload-icon").first.click()
        time.sleep(4)
        set_file_local(page, "input[type=file]", a.video)
        say("file chosen:", a.video)
        page.wait_for_selector("#title-textarea #textbox", timeout=120000)
        time.sleep(3)
        fill_box(page, "#title-textarea #textbox", a.title)
        fill_box(page, "#description-textarea #textbox", desc)

        if a.thumbnail:
            thumbs = page.locator("input[type=file][accept*=image]")
            say("thumbnail inputs:", thumbs.count())
            if thumbs.count():
                thumbs.first.set_input_files(a.thumbnail)
                time.sleep(4)
                say("thumbnail set")

        page.locator("tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]").first.click()
        say("audience: not made for kids")
        page.locator("#toggle-button").first.click()  # show more
        time.sleep(2)
        altered = page.locator(f"tp-yt-paper-radio-button[name=VIDEO_HAS_ALTERED_CONTENT_{a.altered.upper()}]")
        if altered.count():
            altered.first.click(); say("altered content:", a.altered)
        else:
            say("altered-content radio not found (left as is)")
        if a.tags:
            tag = page.locator("#tags-container input, ytcp-free-text-chip-bar input").first
            if tag.count():
                tag.fill(a.tags + ","); time.sleep(1); say("tags filled")
            else:
                say("tags input not found")

        for step in range(3):
            page.locator("#next-button").first.click(); time.sleep(3)
            say("next", step + 1)
        vis = page.locator(f"tp-yt-paper-radio-button[name={a.visibility}]")
        if not vis.count():
            sys.exit("STOP: visibility radios not found")
        vis.first.click(); time.sleep(1)
        url = page.evaluate("() => { const a = document.querySelector('.video-url-fadeable a, a.ytcp-video-info');"
                            " return a ? a.href : null; }")
        say("video url:", url)
        # The upload lives in this tab: publishing is allowed mid-upload, but a closed tab loses the file. Wait until the
        # progress label stops counting upload percent (Thai "อัปโหลด 45%", English "Uploading 45%").
        import re
        for i in range(240):
            status = page.evaluate("() => (document.querySelector('ytcp-video-upload-progress .progress-label, "
                                   ".progress-label') || {}).innerText || ''")
            if not re.search(r"(อัปโหลด|Upload)\D{0,12}\d{1,3}\s?%", status):
                break
            if i % 4 == 0:
                say("uploading:", status.strip()[:80])
            time.sleep(15)
        say("upload status:", status.strip()[:120])
        if a.stop_before_publish:
            say("stopped before publish (draft with every field filled)")
            return
        page.locator("#done-button").first.click()
        time.sleep(6)
        say("published as", a.visibility, url)


if __name__ == "__main__":
    main()
