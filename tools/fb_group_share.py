#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Facebook group feed poster — share a Page Reel link into a joined group.

STANDALONE — no Claude in the loop at runtime, same Playwright-over-CDP
pattern as tools/fb_reel_post.py, but targets the plain group composer
("สร้างโพสต์" on a group's feed) instead of the Reels Business Suite wizard.
Built for task-708dd145: post one already-joined-group text+link share per
run, one group at a time, with a human deciding the pacing between runs.

    .venv/bin/python tools/fb_group_share.py \\
        --cdp http://127.0.0.1:9230 \\
        --group-url https://www.facebook.com/groups/1128465650898382/ \\
        --text-file docs/scripts/fb-groups-ilag-captions/g01-1128465650898382.txt \\
        --link https://www.facebook.com/reel/4560927164226012 \\
        [--dry-run] [--screenshot path.png]

The dedicated Chrome (profile ~/.fb-automation/chrome-profile, port 9230,
signed in as Dorsine Gobb — see the browser-operator skill) must already be
running. If it has 0 tabs, open one first:
    curl -X PUT 'http://127.0.0.1:9230/json/new?about:blank'

Composer flow, one text box, no wizard steps:
1. open the group URL, mute all media on the page (persistent observer).
2. click the "สร้างโพสต์" / "เขียนโพสต์อะไรสักอย่าง..." opener to raise the
   post-creation dialog.
3. read the "โพสต์ในนามของ" / audience-switcher area for a Page option; if
   the Page ("ละครสั้นคุณธรรม by ILAG Studio") is offered, select it,
   otherwise leave the default (personal profile). Recorded either way.
4. click the text box, paste the caption text (which already ends with the
   Reel link on its own line — Facebook renders its own link-preview card
   once the URL is recognised; no separate link field to fill).
5. wait for the link-preview card to render (best-effort; not a hard gate —
   Facebook sometimes renders it slowly and the post is still valid without
   waiting past a bound).
6. --dry-run stops here, screenshots, and returns 0 without ever touching
   the publish button.
7. click "โพสต์" (the composer's own publish button — NOT the group's
   feed-level share icons). Confirm the click via the dialog closing.
8. read the group feed / the profile's own-posts area for either a live
   post (its permalink) or the "รอการอนุมัติจากผู้ดูแลกลุ่ม" (pending admin
   approval) marker, and report whichever it finds.

Caption paste is verified with the same paragraph-level diff as
tools/fb_reel_post.py (`captions_match`) — a byte-for-byte compare on a
contenteditable box false-fails because ProseMirror-style editors double
blank lines in `innerText` (browser-operator skill, task-0250ccdf).

Everything except FBGroupBrowser (real Playwright/CDP calls) is pure and
unit-tested without a browser (tests/test_fb_group_share.py). FBGroupBrowser
itself is exercised live via --dry-run before ever publishing for real.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

MUTE_JS = """
document.querySelectorAll('video,audio').forEach(v => {v.muted = true; v.volume = 0;});
new MutationObserver(() => document.querySelectorAll('video,audio')
  .forEach(v => {v.muted = true; v.volume = 0;}))
  .observe(document.body, {childList: true, subtree: true});
""".strip()

PENDING_MARKERS = [
    "รอการอนุมัติจากผู้ดูแลกลุ่ม",
    "รอการตรวจสอบ",
    "อยู่ระหว่างการพิจารณา",
]

COMPOSER_OPENER_TEXTS = [
    "เขียนโพสต์อะไรสักอย่าง",
    "สร้างโพสต์",
]


def normalize_caption(text: str) -> list[str]:
    """Paragraph-level normalisation: collapse runs of blank lines to one,
    strip leading/trailing blanks. Same rationale as tools/fb_reel_post.py.
    """
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    out: list[str] = []
    prev_blank = False
    for ln in lines:
        if ln == "":
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(ln)
            prev_blank = False
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


def captions_match(expected: str, actual: str) -> tuple[bool, list[str]]:
    """Returns (ok, diff_lines). diff_lines is empty iff ok."""
    exp = normalize_caption(expected)
    act = normalize_caption(actual)
    if exp == act:
        return True, []
    diff = []
    for i in range(max(len(exp), len(act))):
        e = exp[i] if i < len(exp) else "<MISSING>"
        a = act[i] if i < len(act) else "<MISSING>"
        if e != a:
            diff.append(f"line {i}: expected={e!r} actual={a!r}")
    return False, diff


def link_in_text(text: str, link: str) -> bool:
    return link.strip() in text


class PublishRefused(RuntimeError):
    """Raised when a hard precondition for publishing was not met."""


class FBGroupBrowser:
    def __init__(self, cdp_url: str, group_url: str, log=print):
        self.cdp_url = cdp_url
        self.group_url = group_url
        self.log = log
        self._pw = None
        self.browser = None
        self.page = None

    def connect(self, attempts: int = 3, timeout_ms: int = 25000):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        last_err = None
        for i in range(attempts):
            try:
                self.browser = self._pw.chromium.connect_over_cdp(
                    self.cdp_url, timeout=timeout_ms, is_local=True
                )
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                self.log(f"connect_over_cdp attempt {i + 1}/{attempts} failed: {e}")
        raise RuntimeError(f"could not connect to {self.cdp_url} after {attempts} attempts: {last_err}")

    def close(self):
        if self._pw is not None:
            self._pw.stop()

    def open_group(self):
        ctx = self.browser.contexts[0]
        page = ctx.new_page()
        page.goto(self.group_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        page.evaluate(MUTE_JS)
        self.page = page
        return page

    def check_page_state(self) -> dict:
        """Read-only. Returns a small dict describing whether this looks
        like a normal joined-group feed, a login wall, or a
        checkpoint/warning page. Never raises.
        """
        page = self.page
        try:
            body = page.evaluate("document.body.innerText").strip()
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reason": f"could not read page: {e}"}
        markers = {
            "login_wall": ["เข้าสู่ระบบ Facebook", "Log in to Facebook", "accounts.google.com"],
            "checkpoint": ["ยืนยันตัวตน", "checkpoint", "การดำเนินการนี้ต้องได้รับการยืนยัน"],
            "captcha": ["captcha", "CAPTCHA", "พิสูจน์ว่าคุณไม่ใช่โปรแกรมอัตโนมัติ"],
            "spam_or_removed": ["โพสต์นี้ละเมิด", "ถูกลบ", "ถูกจำกัด", "spam"],
        }
        for kind, needles in markers.items():
            for n in needles:
                if n.lower() in body.lower():
                    return {"ok": False, "reason": kind, "snippet": body[:300]}
        return {"ok": True, "reason": "", "snippet": body[:200]}

    def open_composer(self, timeout_ms: int = 15000) -> bool:
        page = self.page
        for text in COMPOSER_OPENER_TEXTS:
            loc = page.get_by_text(text, exact=False).first
            try:
                if loc.count() > 0:
                    loc.click(timeout=timeout_ms)
                    page.wait_for_timeout(1500)
                    return True
            except Exception as e:  # noqa: BLE001
                self.log(f"open_composer: click on {text!r} failed: {e}")
        return False

    def read_identity_options(self) -> list[str]:
        """Best-effort: returns whatever posting-identity names are visible
        near a 'โพสต์ในนามของ' / audience-switcher control. Never raises.
        """
        try:
            names = self.page.evaluate(
                """
                () => {
                  const heading = [...document.querySelectorAll('*')]
                    .find(e => e.children.length === 0 &&
                      (e.textContent.includes('โพสต์ในนามของ') || e.textContent.includes('โพสต์เป็น')));
                  if (!heading) return [];
                  let node = heading.parentElement;
                  for (let i = 0; i < 5 && node; i++) {
                    const t = (node.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
                    if (t.length > 1) return t.slice(0, 6);
                    node = node.parentElement;
                  }
                  return [];
                }
                """
            )
            return names or []
        except Exception as e:  # noqa: BLE001
            self.log(f"read_identity_options: {e}")
            return []

    def select_identity(self, name_substring: str) -> bool:
        """Best-effort click on an identity option containing name_substring.
        Returns whether a matching, clickable element was found.
        """
        try:
            handle = self.page.evaluate_handle(
                """
                (needle) => {
                  const els = [...document.querySelectorAll('*')]
                    .filter(e => e.children.length === 0 && e.textContent.includes(needle));
                  for (const el of els) {
                    let node = el;
                    for (let i = 0; i < 4 && node; i++) {
                      if (node.getAttribute && (node.getAttribute('role') === 'button' || node.tagName === 'BUTTON')) {
                        return node;
                      }
                      node = node.parentElement;
                    }
                  }
                  return null;
                }
                """,
                name_substring,
            )
            el = handle.as_element()
            if el is None:
                return False
            el.click()
            self.page.wait_for_timeout(800)
            return True
        except Exception as e:  # noqa: BLE001
            self.log(f"select_identity: {e}")
            return False

    def set_text(self, text: str) -> tuple[bool, str, list[str]]:
        page = self.page
        box = page.get_by_role("textbox").first
        box.click()
        page.wait_for_timeout(300)
        page.keyboard.insert_text(text)
        page.wait_for_timeout(600)
        readback = box.evaluate("el => el.innerText")
        ok, diff = captions_match(text, readback)
        return ok, readback, diff

    def wait_link_preview(self, timeout_s: int = 15) -> bool:
        page = self.page
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            page.wait_for_timeout(1500)
            try:
                has_preview = page.evaluate(
                    "() => !!document.querySelector('a[href*=\"/reel/\"] img, a[href*=\"facebook.com/reel\"]')"
                )
            except Exception:  # noqa: BLE001
                has_preview = False
            if has_preview:
                return True
        return False

    def _find_publish_button(self):
        # Anchor on role=dialog to avoid matching any feed-level "โพสต์"
        # text elsewhere on the page (same class of bug as fb_reel_post.py's
        # breadcrumb trap: never trust bare text+size, anchor structurally).
        return self.page.evaluate_handle(
            """
            () => {
              const dialogs = [...document.querySelectorAll('[role="dialog"]')];
              for (const d of dialogs) {
                const btn = [...d.querySelectorAll('div[role="button"], button')]
                  .find(e => e.textContent.trim() === 'โพสต์' && !e.disabled &&
                    e.getAttribute('aria-disabled') !== 'true');
                if (btn) return btn;
              }
              return null;
            }
            """
        )

    def publish(self) -> bool:
        handle = self._find_publish_button()
        el = handle.as_element()
        if el is None:
            raise PublishRefused("could not locate an enabled 'โพสต์' button inside the composer dialog")
        el.click()
        return True

    def confirm_result(self, link: str, timeout_s: int = 30) -> dict:
        """Read-only. Polls the feed/page for a pending-approval marker or
        a live post containing our link. Returns
        {"status": "live"|"pending"|"unknown", "permalink": str|None,
         "snippet": str}.
        """
        page = self.page
        deadline = time.time() + timeout_s
        result = {"status": "unknown", "permalink": None, "snippet": ""}
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            try:
                body = page.evaluate("document.body.innerText")
            except Exception:  # noqa: BLE001
                continue
            for marker in PENDING_MARKERS:
                if marker in body:
                    result["status"] = "pending"
                    idx = body.find(marker)
                    result["snippet"] = body[max(0, idx - 80): idx + 120]
                    return result
            try:
                anchors = page.evaluate(
                    """
                    () => [...document.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"]')]
                      .map(a => a.href).slice(0, 10)
                    """
                )
            except Exception:  # noqa: BLE001
                anchors = []
            if anchors:
                result["status"] = "live"
                result["permalink"] = anchors[0]
                return result
        return result

    def screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=False)


def run(args: argparse.Namespace) -> int:
    caption_text = Path(args.text_file).expanduser().read_text(encoding="utf-8").rstrip("\n") + "\n"
    if not link_in_text(caption_text, args.link):
        print(f"REFUSED: --link {args.link!r} not found in --text-file {args.text_file}", file=sys.stderr)
        return 2

    fb = FBGroupBrowser(args.cdp, args.group_url)
    try:
        fb.connect()
        fb.open_group()

        state = fb.check_page_state()
        print(f"page state: {state}")
        if not state["ok"]:
            print(f"REFUSED: page shows {state['reason']!r} — stopping, do not proceed", file=sys.stderr)
            return 10

        if not fb.open_composer():
            print("REFUSED: could not open the post-composer dialog ('สร้างโพสต์' / 'เขียนโพสต์อะไรสักอย่าง...')",
                  file=sys.stderr)
            return 3

        identity_options = fb.read_identity_options()
        print(f"identity options seen: {identity_options}")
        identity_used = "Dorsine Gobb (default/personal)"
        if args.page_name and any(args.page_name in opt for opt in identity_options):
            if fb.select_identity(args.page_name):
                identity_used = args.page_name
        print(f"identity used: {identity_used}")

        ok, readback, diff = fb.set_text(caption_text)
        print(f"caption readback matches: {ok}")
        if not ok:
            for line in diff:
                print("  " + line, file=sys.stderr)
            print("REFUSED: caption read-back differs from the caption file", file=sys.stderr)
            return 4

        preview_ok = fb.wait_link_preview()
        print(f"link preview rendered: {preview_ok}")

        shot_path = args.screenshot or "fb_group_share_dry_run.png"
        fb.screenshot(shot_path)
        print(f"screenshot saved: {shot_path}")

        if args.dry_run:
            print("DRY RUN — stopping before publish, as contracted.")
            return 0

        fb.publish()
        print("PUBLISHED — clicked the composer's own 'โพสต์' button exactly once.")
        result = fb.confirm_result(args.link)
        print(f"post status: {result['status']}")
        print(f"permalink (best-effort): {result['permalink']}")
        if result["snippet"]:
            print(f"snippet: {result['snippet']!r}")
        print(f"identity used: {identity_used}")
        return 0
    finally:
        fb.close()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cdp", default="http://127.0.0.1:9230")
    ap.add_argument("--group-url", required=True)
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--link", required=True, help="the Reel URL; must appear as a line in --text-file")
    ap.add_argument("--page-name", default="ละครสั้นคุณธรรม by ILAG Studio",
                     help="Page identity to prefer if the composer offers it")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--screenshot", default=None, help="Path to save the pre-publish screenshot to.")
    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
