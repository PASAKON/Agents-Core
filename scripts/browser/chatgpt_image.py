#!/usr/bin/env python3
"""ChatGPT image-generation driver — Playwright over CDP, reusable for any future image job
(not tied to this task's characters/title — the prompt and reference files are caller-supplied).

Prereqs:
  - A Chrome with a debug port open, signed into chatgpt.com on a Plus (or higher) account.
    On the Mac automation Chrome this is CDP 127.0.0.1:9223, profile ~/.flow-automation/chrome-profile;
    relaunch with `bash scripts/flow/launch-chrome-debug.sh` if the port is down.
  - Playwright for Python installed (`pip install playwright && playwright install chromium`) —
    NOT installed in this task's environment, so this script was written and its selectors were
    verified by hand through a live claude-in-chrome session (task-d206afca, 2026-09-24), but the
    script itself has never been run end-to-end. See REPORT.md "Replay Script" for exactly which
    parts are live-verified vs untested.

Usage:
  python3 scripts/browser/chatgpt_image.py --cdp http://127.0.0.1:9223 \
    --files ref1.png ref2.png --prompt-file prompt.txt --out out_dir --n 1

Behavior:
  - Opens ONE NEW chat per image (a fresh chat per request avoids the stale-reference-binding
    class of bug documented in the browser-operator skill for reused tabs/threads, and matches
    what was actually done live this task — each of the 3 posters used its own new chat).
  - Attaches --files, pastes --prompt-file's contents, submits, waits for the image to finish,
    downloads the full-size PNG into --out as image-<n>-<timestamp>.png.
  - --n repeats the same prompt+files N times, sleeping >=60s between requests (measured
    generation time live: ~60-150s per image at "High" quality, so this floor rarely idles).
  - NEVER logs in. If the account looks signed out, or off the Plus tier, it prints
    NOT_SIGNED_IN / NOT_PLUS and exits 1 without touching the composer.
"""
import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

CDP_DEFAULT = "http://127.0.0.1:9223"
MIN_DELAY_S = 60
GEN_TIMEOUT_S = 240

# Mute-on-load snippet (browser-operator SKILL.md, HARD rule, CEO 2026-09-19) — paste on every
# page load so nothing on the page can play audio into the room. LIVE-VERIFIED this task.
MUTE_JS = """
(() => {
  const mute = el => { el.muted = true; el.volume = 0; };
  const all = () => document.querySelectorAll('video,audio');
  all().forEach(mute);
  document.addEventListener('play', e => mute(e.target), true);
  new MutationObserver(() => all().forEach(mute)).observe(document.documentElement, { childList: true, subtree: true });
})()
""".strip()

# Verification table (task-d206afca, 2026-09-24, live claude-in-chrome session against a real
# ChatGPT Plus account) — same convention as scripts/higgsfield/gen_loop.py's own table.
# | selector / behavior                                    | verified | notes |
# |----------------------------------------------------------|----------|-------|
# | #prompt-textarea (composer, both new-chat and edit-image)| LIVE     | contenteditable, ProseMirror-style |
# | input[type=file] (hidden) — set_input_files              | LIVE     | 6 files, 3.5MB total, one call |
# | img[alt*="ภาพที่สร้างขึ้น"] (Thai locale "generated image") | LIVE     | locale-dependent — see IMG_SELECTOR below for the locale-agnostic fallback used instead |
# | img[src*="backend-api/estuary/content"]                  | LIVE     | src populated once the render is server-side done; naturalWidth stays 0 until the browser has actually decoded it |
# | #composer-submit-button aria-label toggles "ส่งคำสั่ง"/"หยุดตอบ" | LIVE | locale-dependent (Send/Stop responding) — same caveat |
# | download control (top-right icon in the image lightbox)  | LIVE but selector UNVERIFIED | clicked by fixed pixel coordinate in the live session, not by a stable selector — see download_image() below |
# | typing long mixed Thai/English text char-by-key           | LIVE — FAILS | CDP-level per-keystroke typing silently dropped characters on long strings; page.keyboard.insert_text() (single DOM-level insert, no per-key events) is used instead below and was NOT itself live-tested in Playwright, only inferred from the failure mode observed via the computer-use tool |
IMG_SELECTOR = 'img[src*="backend-api/estuary/content"], img[alt*="ภาพที่สร้างขึ้น"], img[alt*="generated image" i]'


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def mute(page) -> None:
    page.evaluate(MUTE_JS)


def check_signed_in_plus(page) -> None:
    """Never logs in. Exits 1 with a clear message if signed out or not Plus."""
    page.wait_for_timeout(1500)
    signed_out = page.evaluate(
        "() => /เข้าสู่ระบบ|log ?in|sign ?in/i.test(document.body.innerText.slice(0,500))"
        " && !document.querySelector('#prompt-textarea')"
    )
    if signed_out:
        log("NOT_SIGNED_IN — sign the target Chrome profile into chatgpt.com by hand, then re-run.")
        sys.exit(1)
    has_plus = page.evaluate("() => /\\bplus\\b/i.test(document.body.innerText.slice(0,600))")
    if not has_plus:
        log("NOT_PLUS (or could not confirm Plus tier from the sidebar) — "
            "check the account manually before spending image quota.")
        sys.exit(1)


def attach_files(page, files: list[str]) -> None:
    inp = page.locator('input[type=file]').first
    inp.set_input_files(files)
    page.wait_for_timeout(800)


def type_prompt(page, text: str) -> None:
    box = page.locator('#prompt-textarea').first
    box.click()
    page.keyboard.press("Meta+A")
    page.keyboard.press("Backspace")
    page.wait_for_timeout(200)
    # insert_text() dispatches a single DOM input event instead of one keydown/keyup pair per
    # character — the per-character path (page.keyboard.type / the computer-use tool's "type"
    # action) measurably dropped characters on long mixed Thai/English strings in this task's
    # live session (see verification table above). Not itself re-verified inside Playwright.
    page.keyboard.insert_text(text)
    page.wait_for_timeout(200)


def submit(page) -> None:
    btn = page.locator('#composer-submit-button').first
    btn.click()


def wait_for_image(page, baseline_count: int, timeout_s: int = GEN_TIMEOUT_S):
    """Poll for a NEW generated-image <img> beyond baseline_count, then wait for the browser to
    finish decoding it (naturalWidth > 0). Returns the Locator for the newest one."""
    start = time.time()
    while time.time() - start < timeout_s:
        imgs = page.locator(IMG_SELECTOR)
        n = imgs.count()
        if n > baseline_count:
            last = imgs.nth(n - 1)
            if last.evaluate("el => el.complete && el.naturalWidth > 0"):
                return last
        time.sleep(4)
    raise TimeoutError(f"no completed image after {timeout_s}s")


def download_image(page, img_locator, out_path: Path) -> None:
    """Opens the full-size lightbox and downloads the PNG.

    UNVERIFIED SELECTOR (see verification table): the live session clicked a bare icon button at
    a fixed pixel position in the lightbox header, not a stable aria-label or data-testid — none
    was found. Tries a text/role-based lookup first (locale-agnostic where possible); if that
    fails, the caller should treat this as a manual step and file a blocker rather than guess
    at coordinates, since a fixed-pixel click is exactly the kind of thing that breaks silently
    on the next ChatGPT UI change.
    """
    img_locator.click()
    page.wait_for_timeout(800)
    dl_btn = page.get_by_role(
        "button", name=re.compile(r"ดาวน์โหลด|download", re.I)
    ).first
    with page.expect_download(timeout=60_000) as dl_info:
        dl_btn.click()
    download = dl_info.value
    download.save_as(str(out_path))
    # close the lightbox back to the chat
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)


def run_one(page, files: list[str], prompt: str, out_dir: Path, idx: int) -> Path:
    page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
    mute(page)
    check_signed_in_plus(page)
    attach_files(page, files)
    baseline = page.locator(IMG_SELECTOR).count()
    type_prompt(page, prompt)
    submit(page)
    log(f"[{idx}] submitted, waiting for image...")
    img = wait_for_image(page, baseline)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"image-{idx}-{ts}.png"
    download_image(page, img, out_path)
    log(f"[{idx}] saved {out_path}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cdp", default=CDP_DEFAULT)
    ap.add_argument("--files", nargs="+", required=True, help="Reference image paths to attach.")
    ap.add_argument("--prompt-file", required=True, help="Path to a text file with the full prompt.")
    ap.add_argument("--out", required=True, help="Output directory for downloaded PNGs.")
    ap.add_argument("--n", type=int, default=1, help="How many times to repeat this request.")
    args = ap.parse_args()

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [str(Path(f).expanduser()) for f in args.files]
    for f in files:
        if not Path(f).is_file():
            log(f"REFUSED: file not found: {f}")
            sys.exit(1)

    from playwright.sync_api import sync_playwright  # lazy import — same convention as
    # scripts/higgsfield/gen_loop.py: keeps this module importable/testable without
    # Playwright installed (it is not installed in this task's environment).

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()

        ok, failed = 0, 0
        for i in range(1, args.n + 1):
            try:
                run_one(page, files, prompt, out_dir, i)
                ok += 1
            except Exception as e:
                log(f"[{i}] FAILED: {e!r}")
                failed += 1
            if i < args.n:
                log(f"sleeping {MIN_DELAY_S}s before the next request (human pace)...")
                time.sleep(MIN_DELAY_S)

        log(f"DONE: {ok} ok, {failed} failed")


if __name__ == "__main__":
    main()
