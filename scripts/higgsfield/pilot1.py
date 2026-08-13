#!/usr/bin/env python3
"""PILOT: one humanized Higgsfield generation.
Verifies config (15s/16:9/720p/High/Unlimited/enhance-off) — aborts if wrong so no credits burned.
Types prompt char-by-char, generates, waits for History completion, downloads to ~/Google Drive/, indexes.
Run: .venv/bin/python scripts/higgsfield/pilot1.py
"""
import csv
import random
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
# NOTE: ~/Google Drive is macOS CloudStorage (TCC blocks write without Full Disk Access).
# Output locally for now; sync to Drive later (FDA grant or rclone).
DRIVE_ROOT = Path.home() / "Projects" / "Agents" / "output" / "higgsfield-broll"
CATEGORY = "01_trading-finance"
OUTDIR = DRIVE_ROOT / CATEGORY
INDEX = DRIVE_ROOT / "00_INDEX.csv"

PROMPT = ("Slow cinematic dolly-in over a glowing financial candlestick chart, green and red candles rising, "
          "dark moody background, shallow depth of field, subtle camera drift, premium finance aesthetic, volumetric light. "
          "No text, no logo, no numbers, no watermark, no faces.")
CLIP_ID = "trade-charts-candleglow-001"
FILENAME = f"{CLIP_ID}-15s-720p-169.mp4"
COMPLETION_TIMEOUT_S = 420
POLL_S = 8


def human_pause(a=0.4, b=1.2):
    time.sleep(random.uniform(a, b))


def btn_text(page, label):
    try:
        return page.locator(f'button[aria-label="{label}"]').first.inner_text().replace("\n", "/")
    except Exception:
        return ""


def verify_config(page):
    checks = {
        "Duration=15s": ("15" in btn_text(page, "Duration")),
        "Ratio=16:9": ("16:9" in btn_text(page, "Ratio")),
        "Resolution=720p": ("720" in btn_text(page, "Resolution")),
        "Bitrate=High": ("High" in btn_text(page, "Bitrate")),
    }
    gen = page.query_selector('button[type=submit]').inner_text().replace("\n", "/")
    checks["Generate=Unlimited"] = ("Unlimited" in gen)
    cb = page.locator('input[name="enhancePrompt"]')
    enh_on = cb.evaluate("el=>el.checked") if cb.count() else True
    checks["enhance_OFF"] = (enh_on is False)
    for k, passed in checks.items():
        print(f"   {'OK  ' if passed else 'FAIL'} {k}")
    print("   Generate text:", gen)
    return all(checks.values())


def video_urls(page):
    return page.evaluate("""() => {
      const urls = [];
      document.querySelectorAll('video').forEach(v => {
        let s = v.src || v.currentSrc;
        const src = v.querySelector('source'); if(!s && src) s = src.src;
        if(s && !s.startsWith('blob:')) urls.push(s);
      });
      document.querySelectorAll('a[download]').forEach(a => { if(a.href && !a.href.startsWith('blob:')) urls.push(a.href); });
      return [...new Set(urls)];
    }""")


def download(url, path, page):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        cookies = page.context.cookies(url)
        if cookies:
            headers["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    except Exception:
        pass
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=240) as r, open(path, 'wb') as f:
        f.write(r.read())
    return path.stat().st_size


def append_index(row):
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    exists = INDEX.exists()
    with open(INDEX, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["clip_id", "category", "subcategory", "prompt", "palette",
                        "duration", "resolution", "gen_date", "filename", "rating"])
        w.writerow(row)


def type_prompt(page, text):
    box = page.locator('div[role=textbox]').first
    box.click(); page.wait_for_timeout(400)
    page.keyboard.press("Meta+A"); page.keyboard.press("Backspace"); page.wait_for_timeout(200)
    for ch in text:
        page.keyboard.type(ch); time.sleep(random.uniform(0.03, 0.11))
    print("   prompt typed:", len(text), "chars")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "higgsfield.ai" in pg.url), None)
        if page is None:
            print("NO_TAB"); sys.exit(1)
        try:
            page.bring_to_front()
        except Exception:
            pass
        print("TAB:", page.url)
        if page.query_selector(".hfnav-auth-login"):
            print("NOT_LOGGED_IN"); sys.exit(1)

        print("[1] verify config")
        if not verify_config(page):
            print("CONFIG_WRONG -> ABORT (not generating)"); sys.exit(1)

        print("[2] type prompt (human pace)")
        type_prompt(page, PROMPT); human_pause(0.6, 1.6)

        before = set(video_urls(page))
        print("   videos before:", len(before))
        print("[3] click Generate")
        page.query_selector('button[type=submit]').click()
        start = time.time()
        print(f"[4] poll completion (max {COMPLETION_TIMEOUT_S}s)...")

        new_url = None
        opened_history = False
        while time.time() - start < COMPLETION_TIMEOUT_S:
            now = set(video_urls(page))
            fresh = now - before
            if fresh:
                new_url = sorted(fresh)[-1]
                print(f"   NEW result after {int(time.time()-start)}s: {new_url[:120]}")
                break
            el = int(time.time() - start)
            if not opened_history and el > 30:
                try:
                    page.locator('button:has-text("History")').first.click(timeout=2000)
                    opened_history = True
                    print(f"   opened History @{el}s")
                except Exception:
                    pass
            if el % 24 == 0:
                print(f"   ...{el}s videos={len(now)}")
            time.sleep(POLL_S)

        if not new_url:
            print("TIMEOUT_NO_RESULT")
            print("urls now:", video_urls(page))
            sys.exit(2)

        print("[5] download ->", FILENAME)
        out = OUTDIR / FILENAME
        try:
            size = download(new_url, out, page)
            print(f"   saved {size} bytes ({size/1_048_576:.1f} MB)")
        except Exception as e:
            print("   DOWNLOAD_ERR:", repr(e))
            print("   url:", new_url)
            sys.exit(3)

        print("[6] index")
        append_index([CLIP_ID, "trading", "charts", PROMPT, "dark", "15s", "720p",
                      date.today().isoformat(), FILENAME, ""])
        print("DONE:", out)


if __name__ == "__main__":
    main()
