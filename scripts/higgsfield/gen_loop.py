#!/usr/bin/env python3
"""Higgsfield B-roll generation loop — STANDALONE (no Claude in the loop, zero token cost at runtime).
Drives the logged-in automation Chrome (port 9222) to generate cinematic Seedance clips, download,
upload to Google Drive, and index. Resumable (skips clips already in INDEX).

Prereqs:
  - Chrome running with debug port:  bash scripts/higgsfield/launch-chrome-debug.sh
  - Logged into higgsfield.ai in that Chrome, on the gen page.
  - claudeflow .env has GOOGLE_OAUTH_* + DRIVE_VIDEO_PARENT_FOLDER_ID.

Usage:
  python scripts/higgsfield/gen_loop.py --csv scripts/higgsfield/prompts/01_trading-finance.csv --limit 5
  python scripts/higgsfield/gen_loop.py --csv <csv> --delay-min 60 --delay-max 240
"""
import argparse
import csv
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── config ──────────────────────────────────────────────────────────────────
CDP = "http://127.0.0.1:9222"
CF_ENV = Path("/Users/gob/Projects/mooniex-claudeflow/.env")
LOCAL_ROOT = Path("/Users/gob/Projects/Agents/output/higgsfield-broll")
INDEX = LOCAL_ROOT / "00_INDEX.csv"
DRIVE_CACHE = LOCAL_ROOT / ".drive_cache.json"
COMPLETION_TIMEOUT_S = 900
POLL_S = 8
CATEGORY_FOLDERS = {"trading": "01_trading-finance"}  # add more categories here


# ── env / drive ─────────────────────────────────────────────────────────────
def load_env():
    env = {}
    with open(CF_ENV) as f:
        for line in f:
            m = re.match(r'^([A-Z_]+)=(.*)$', line.strip())
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


def drive_token(env):
    d = urllib.parse.urlencode({
        'client_id': env['GOOGLE_OAUTH_CLIENT_ID'],
        'client_secret': env['GOOGLE_OAUTH_CLIENT_SECRET'],
        'refresh_token': env['GOOGLE_OAUTH_REFRESH_TOKEN'],
        'grant_type': 'refresh_token',
    }).encode()
    r = urllib.request.urlopen(
        urllib.request.Request('https://oauth2.googleapis.com/token', data=d), timeout=30)
    return json.loads(r.read())['access_token']


def drive_get(token, url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    return json.loads(urllib.request.urlopen(req, timeout=40).read())


def drive_post(token, url, body, ctype='application/json'):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method='POST')
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Content-Type', ctype)
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def drive_folder(token, name, parent, cache):
    key = f"{parent}/{name}"
    if cache.get(key):
        return cache[key]
    q = ("mimeType='application/vnd.google-apps.folder' and name='%s' and '%s' in parents and trashed=false"
         % (name.replace("'", "\\'"), parent))
    url = "https://www.googleapis.com/drive/v3/files?q=" + urllib.parse.quote(q) + "&fields=files(id,name)"
    try:
        res = drive_get(token, url)
        if res.get('files'):
            fid = res['files'][0]['id']
        else:
            fid = drive_post(token, 'https://www.googleapis.com/drive/v3/files?fields=id',
                             {'name': name, 'mimeType': 'application/vnd.google-apps.folder',
                              'parents': [parent]})['id']
    except urllib.error.HTTPError as e:
        print("  drive_folder err:", e.code, e.read()[:150]); raise
    cache[key] = fid
    return fid


def drive_upload(token, local_path, name, parent_id):
    boundary = 'brollbnd' + str(random.randint(1000, 9999))
    meta = json.dumps({'name': name, 'parents': [parent_id]})
    body = (b'--' + boundary.encode() + b'\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
            + meta.encode() + b'\r\n--' + boundary.encode()
            + b'\r\nContent-Type: video/mp4\r\n\r\n' + local_path.read_bytes()
            + b'\r\n--' + boundary.encode() + b'--\r\n')
    req = urllib.request.Request(
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size',
        data=body, method='POST')
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Content-Type', 'multipart/related; boundary=' + boundary)
    r = json.loads(urllib.request.urlopen(req, timeout=240).read())
    return r.get('id'), r.get('size')


# ── page helpers ────────────────────────────────────────────────────────────
def btn_text(page, label):
    try:
        return page.locator(f'button[aria-label="{label}"]').first.inner_text().replace("\n", "/")
    except Exception:
        return ""


def ensure_config(page):
    """Set Duration=8s (Unlimited-eligible cap as of 2026-08-03), Ratio=9:16 (mobile/vertical); verify 720p/High/Unlimited."""
    for _ in range(3):
        page.keyboard.press("Escape"); page.wait_for_timeout(150)

    # Duration -> 8s. NOTE 2026-08-03: Unlimited mode desyncs (falls back to paid credits)
    # above 8s on the current plan tier. Do NOT raise this without re-verifying live —
    # 10s already exits Unlimited and shows a real credit cost on the Generate button.
    try:
        page.locator('button[aria-label="Duration"]').first.click(); page.wait_for_timeout(800)
        dur = page.locator('[role=slider][aria-valuemax="15"]')
        if dur.count() == 0:
            dur = page.locator('[role=slider]').nth(1)
        dur.first.click(timeout=3000); page.wait_for_timeout(200)
        page.keyboard.press("Home"); page.wait_for_timeout(250)
        for _ in range(20):
            if dur.first.evaluate("el=>el.getAttribute('aria-valuenow')") == "8":
                break
            page.keyboard.press("ArrowRight"); page.wait_for_timeout(70)
        page.keyboard.press("Escape"); page.wait_for_timeout(300)
    except Exception as e:
        print("  duration set err:", repr(e))

    # Ratio -> 9:16 (mobile/vertical — Reels/TikTok/Stories format)
    try:
        page.locator('button[aria-label="Ratio"]').first.click(); page.wait_for_timeout(700)
        page.locator('[class*="group/item"]').filter(has_text="9:16").first.click(timeout=3000)
        page.wait_for_timeout(300)
        page.keyboard.press("Escape"); page.wait_for_timeout(250)
    except Exception as e:
        print("  ratio set err:", repr(e))

    # Elements toggle = AUDIO (CEO-confirmed) — turn ON
    try:
        cb = page.locator('input[name="enhancePrompt"]')
        if cb.count() and not cb.evaluate("el=>el.checked"):
            cb.check(force=True); page.wait_for_timeout(300); print("  audio (Elements) -> ON")
    except Exception as e:
        print("  audio toggle err:", repr(e))

    # Unlimited mode: trust GENERATE BUTTON text (switch data-state uses 'on', desyncs from billing).
    # Click switch until Generate button literally says "Unlimited".
    for _attempt in range(3):
        try:
            gen_txt = page.query_selector('button[type=submit]').inner_text()
        except Exception:
            gen_txt = ""
        if "Unlimited" in gen_txt:
            break
        try:
            page.locator('button[role="switch"][aria-label="Unlimited mode"]').first.click()
            page.wait_for_timeout(700)
            print("  toggled Unlimited mode (attempt %d)" % (_attempt + 1))
        except Exception as e:
            print("  unlimited toggle err:", repr(e)); break

    # Audio/sound toggle ON (Seedance native foley/SFX) — broad selector search
    try:
        for sel in ['[role=switch][aria-label*="udio"]', '[role=switch][aria-label*="ound"]',
                    'button[aria-label*="udio"]', 'button[aria-label*="ound"]']:
            loc = page.locator(sel).first
            if loc.count():
                st = loc.evaluate("el=>el.getAttribute('data-state') || el.getAttribute('aria-checked') || ''")
                if st not in ('checked', 'true', 'on'):
                    loc.click(); page.wait_for_timeout(400); print("  audio toggled ON")
                break
    except Exception as e:
        print("  audio toggle err:", repr(e))

    # verify
    cb = page.locator('input[name="enhancePrompt"]')
    audio_on = cb.evaluate("el=>el.checked") if cb.count() else False
    checks = {
        "Duration=8s": "8" in btn_text(page, "Duration"),
        "Ratio=9:16": "9:16" in btn_text(page, "Ratio"),
        "Resolution=1080p": "1080" in btn_text(page, "Resolution"),
        "Bitrate=High": "High" in btn_text(page, "Bitrate"),
        "audio_ON": audio_on,
    }
    gen = page.query_selector('button[type=submit]').inner_text().replace("\n", "/")
    checks["Generate=Unlimited"] = "Unlimited" in gen
    bad = [k for k, v in checks.items() if not v]
    if bad:
        print("  CONFIG FAIL:", bad, "| Generate:", gen)
    return not bad


def type_prompt(page, text):
    box = page.locator('div[role=textbox]').first
    box.click(); page.wait_for_timeout(400)
    page.keyboard.press("Meta+A"); page.keyboard.press("Backspace"); page.wait_for_timeout(200)
    for ch in text:
        page.keyboard.type(ch); time.sleep(random.uniform(0.03, 0.10))


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


def failed_count(page):
    return page.evaluate("""() => {
      let n = 0;
      document.querySelectorAll('*').forEach(el => {
        if ((el.innerText||'').trim() === 'Failed') n++;
      });
      return n;
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


def append_index(row, drive_id):
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    exists = INDEX.exists()
    with open(INDEX, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["clip_id", "category", "subcategory", "prompt", "palette", "duration",
                        "resolution", "gen_date", "filename", "drive_id", "rating"])
        w.writerow(row + [drive_id])


def done_ids():
    if not INDEX.exists():
        return set()
    ids = set()
    with open(INDEX, newline='', encoding='utf-8') as f:
        for r in csv.reader(f):
            if r and r[0] != "clip_id":
                ids.add(r[0])
    return ids


# ── main loop ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--limit', type=int, default=0, help="0 = all")
    ap.add_argument('--delay-min', type=int, default=45)
    ap.add_argument('--delay-max', type=int, default=180)
    args = ap.parse_args()

    rows = []
    with open(args.csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append(r)

    done = done_ids()
    todo = [r for r in rows if r['clip_id'] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"queue: {len(rows)} total, {len(done)} done, {len(todo)} to run")
    if not todo:
        print("nothing to do."); return

    env = load_env()
    token = drive_token(env)
    parent = env['DRIVE_VIDEO_PARENT_FOLDER_ID']
    cache = json.loads(DRIVE_CACHE.read_text()) if DRIVE_CACHE.exists() else {}
    lib_id = drive_folder(token, "Mooniex B-Roll Library", parent, cache)
    print("Drive lib folder:", lib_id)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "higgsfield.ai" in pg.url), None)
        if page is None:
            print("NO_HIGGSFIELD_TAB — open the gen page in the automation Chrome first."); sys.exit(1)
        try:
            page.bring_to_front()
        except Exception:
            pass
        if page.query_selector(".hfnav-auth-login"):
            print("NOT_LOGGED_IN"); sys.exit(1)

        ok_count, fail_count_n = 0, 0
        for i, r in enumerate(todo, 1):
            cid = r['clip_id']
            print(f"\n=== [{i}/{len(todo)}] {cid} ===")
            try:
                if not ensure_config(page):
                    print("  skip: config wrong"); fail_count_n += 1; continue
                type_prompt(page, r['prompt']); time.sleep(random.uniform(0.6, 1.6))
                # commit contenteditable via REAL keyboard Escape (React ignores programmatic blur)
                page.keyboard.press("Escape"); page.wait_for_timeout(400)
                page.locator('button[type=submit]').first.click()
                page.wait_for_timeout(8000)
                if not page.evaluate("()=>/generating|processing|queued|rendering|in progress/i.test(document.body.innerText)"):
                    print("  gen not started — retry click")
                    page.locator('button[type=submit]').first.click()
                    page.wait_for_timeout(8000)
                try: page.locator('button:has-text("History")').first.click(timeout=2000)
                except Exception: pass
                # timestamp-based detection: scroll history to bottom (render lazy videos),
                # watch for a NEW hf_ timestamp newer than the before-gen max.
                def _ts(u):
                    m = re.search(r'/hf_(\d{8}_\d{6})_', u)
                    return m.group(1) if m else ''
                def _hf():
                    try: page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    except Exception: pass
                    page.wait_for_timeout(400)
                    return [u for u in video_urls(page) if 'cloudfront' in u and '/hf_' in u]
                t0_max = max([_ts(u) for u in _hf()] + [''])
                start = time.time(); new_url = None
                while time.time() - start < COMPLETION_TIMEOUT_S:
                    cur = _hf()
                    cur_max = max([_ts(u) for u in cur] + [''])
                    if cur_max and cur_max > t0_max:
                        new_url = [u for u in cur if _ts(u) == cur_max][0]; break
                    el = int(time.time() - start)
                    if el % 30 == 0:
                        print(f"  ...{el}s (hf={len(cur)} max={cur_max})")
                    time.sleep(POLL_S)
                try: page.evaluate("window.scrollTo(0, 0)")
                except Exception: pass
                if not new_url:
                    print("  no result in timeout — skip (slow or failed)"); fail_count_n += 1; continue
                elapsed = int(time.time() - start)
                folder_name = CATEGORY_FOLDERS.get(r['category'], r['category'])
                cat_id = drive_folder(token, folder_name, lib_id, cache)
                DRIVE_CACHE.write_text(json.dumps(cache))
                local_dir = LOCAL_ROOT / folder_name
                local_dir.mkdir(parents=True, exist_ok=True)
                fname = f"{cid}-{r['duration']}-1080p-916.mp4"
                local_path = local_dir / fname
                size = download(new_url, local_path, page)
                did, dsize = drive_upload(token, local_path, fname, cat_id)
                append_index([cid, r['category'], r['subcategory'], r['prompt'], r['palette'],
                              r['duration'], "1080p", date.today().isoformat(), fname], did)
                print(f"  OK {elapsed}s | {size/1_048_576:.1f}MB local | drive:{did} | {fname}")
                ok_count += 1
            except Exception as e:
                print("  CLIP_ERR:", repr(e)); fail_count_n += 1
            DRIVE_CACHE.write_text(json.dumps(cache))
            if i < len(todo):
                d = random.uniform(args.delay_min, args.delay_max)
                print(f"  sleep {d:.0f}s (humanized)...")
                time.sleep(d)

        print(f"\n=== DONE: {ok_count} ok, {fail_count_n} fail ===")


if __name__ == "__main__":
    main()
