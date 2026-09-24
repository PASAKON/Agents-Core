#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Facebook Business Suite Reels composer — zero-model, one-shot poster
(task-c6bd5ba6, docs/reports/banchi-fb-repost3/REPORT.md).

STANDALONE — no Claude in the loop, zero token cost at runtime, same pattern
as tools/flow_shoot.py: Playwright over CDP against a dedicated Chrome
(profile ~/.fb-automation/chrome-profile, port 9230, signed in as Dorsine
Gobb — see the browser-operator skill). Replaces the manual composer flow
that broke a Reel post twice (docs/reports/banchi-fb-unavailable/REPORT.md,
banchi-fb-repost2/REPORT.md) by editing it after publish — this script NEVER
edits a post once published; a fresh run is the only way to change one.

    .venv/bin/python tools/fb_reel_post.py \\
        --cdp http://127.0.0.1:9230 --asset-id 1319535331240503 \\
        --video ~/Downloads/clip-FINAL.mp4 --cover ~/Downloads/cover.png \\
        --caption-file docs/scripts/banchi-reels-caption.txt [--dry-run]

Composer flow, measured live 2026-09-25 against this exact asset_id (see the
task's scratch exploration, not checked in): the "เพิ่มวิดีโอ" / "อัพโหลดภาพ"
buttons open a NATIVE OS file dialog on a plain click — this script never
lets that happen. Every upload goes through Playwright's
`page.expect_file_chooser()`, which intercepts the dialog at the CDP level
before Chrome ever draws it, then calls `.set_files()` on the returned
FileChooser. This is the Playwright-idiomatic fix for the exact trap the task
brief warns about ("you never click เพิ่มวิดีโอ ... call set_input_files") —
functionally identical (no native dialog ever appears), because the file
input element itself does not exist in the DOM until the button's own click
handler creates it, so there is nothing to `set_input_files` on beforehand.

The composer is a 3-step wizard (สร้าง / แก้ไข / แชร์): step 1 is media +
caption + thumbnail + tags, step 2 is an audio/crop/text editing step (left
untouched — nothing in the task asks for it), step 3 is the final "แชร์"
step with the audience selector and the publish button. Advancing steps by
clicking "ถัดไป" is flaky (observed to silently no-op once in ~12 live
attempts) so `_click_next_until` retries a bounded number of times and
verifies a step-specific text marker actually appeared before trusting the
click. The publish button and the wizard's own "แชร์" breadcrumb chip share
the exact same visible text; they are told apart by tag/role (breadcrumb is
a bare <div>, the real button is `button, [role="button"]`) — see
`_find_publish_button`.

No AI-content-disclosure toggle was found anywhere in this composer during
live exploration (including after expanding "การตั้งค่าการกระจายขั้นสูง"),
so `_handle_ai_label` is best-effort: it searches for one and records exactly
what it finds (or its absence) rather than assuming the task's premise that
one exists. If a real run of this script finds one, record the exact wording
in the report — the search patterns here can be tightened once one is seen.

Everything below the browser class (`captions_match`, `build_parser`) is
pure and unit-tested without a browser (tests/test_fb_reel_post.py). FBReel
itself is exercised live via --dry-run before ever publishing for real.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

MUTE_JS = """
document.querySelectorAll('video,audio').forEach(v => {v.muted = true; v.volume = 0;});
new MutationObserver(() => document.querySelectorAll('video,audio')
  .forEach(v => {v.muted = true; v.volume = 0;}))
  .observe(document.body, {childList: true, subtree: true});
""".strip()

COMPOSER_URL_TMPL = (
    "https://business.facebook.com/latest/reels_composer/"
    "?ref=biz_web_home_create_reel&asset_id={asset_id}"
)

UPLOAD_TIMEOUT_S = 30 * 60  # spec: poll the DOM, timeout 30 min
STEP_ADVANCE_TIMEOUT_S = 20
STEP_ADVANCE_MAX_CLICKS = 3

# AI-content-disclosure candidates — none confirmed live as of 2026-09-25;
# kept broad on purpose, see module docstring.
AI_LABEL_PATTERNS = [
    re.compile(r"AI[^\n]{0,80}", re.I),
    re.compile(r"สร้างขึ้นด้วย\s*AI[^\n]{0,80}"),
    re.compile(r"แก้ไขด้วย\s*AI[^\n]{0,80}"),
    re.compile(r"เนื้อหาที่สร้างด้วย[^\n]{0,80}"),
    re.compile(r"ป้ายกำกับ[^\n]{0,80}"),
]

# The Restricted option's description is a strict superscring of the Public
# one, so an exact match on the Public description is unique on this page.
AUDIENCE_PUBLIC_DESC = "ทุกคนทั้งที่ใช้และไม่ใช้ Facebook"
AUDIENCE_HEADING = "ใครสามารถดูคลิปนี้ได้บ้าง"

CAPTION_BOX_ARIA_LABEL = "เขียนในกล่องโต้ตอบเพื่อเพิ่มข้อความในโพสต์ของคุณ"


def normalize_caption(text: str) -> list[str]:
    """Paragraph-level normalisation: collapse runs of blank lines to one,
    strip leading/trailing blanks. A ProseMirror/contenteditable composer is
    known to double blank lines in innerText (browser-operator skill, task
    0250ccdf) — a byte-for-byte compare false-fails on any multi-paragraph
    caption, so this compares content lines, not raw bytes.
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


class PublishRefused(RuntimeError):
    """Raised when a hard precondition for publishing was not met."""


class FBReelBrowser:
    def __init__(self, cdp_url: str, asset_id: str, log=print):
        self.cdp_url = cdp_url
        self.asset_id = asset_id
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
                self.browser = self._pw.chromium.connect_over_cdp(self.cdp_url, timeout=timeout_ms)
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                self.log(f"connect_over_cdp attempt {i + 1}/{attempts} failed: {e}")
        raise RuntimeError(f"could not connect to {self.cdp_url} after {attempts} attempts: {last_err}")

    def close(self):
        if self._pw is not None:
            self._pw.stop()

    def open_composer(self):
        ctx = self.browser.contexts[0]
        page = ctx.new_page()
        url = COMPOSER_URL_TMPL.format(asset_id=self.asset_id)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        page.evaluate(MUTE_JS)
        self.page = page
        return page

    def confirm_page_name(self) -> str:
        """Best-effort: returns the Page name text shown in the "โพสต์ไปยัง"
        picker, or "" if not found. Never raises — this is a log/report line,
        not a gate.
        """
        try:
            txt = self.page.evaluate(
                """
                () => {
                  const heading = [...document.querySelectorAll('*')]
                    .find(e => e.children.length === 0 && e.textContent.trim() === 'โพสต์ไปยัง');
                  if (!heading) return '';
                  let node = heading.parentElement;
                  for (let i = 0; i < 5 && node; i++) {
                    const t = node.innerText || '';
                    const lines = t.split('\\n').map(s => s.trim()).filter(Boolean);
                    const cand = lines.find(l => l !== 'โพสต์ไปยัง');
                    if (cand) return cand;
                    node = node.parentElement;
                  }
                  return '';
                }
                """
            )
            return txt or ""
        except Exception as e:  # noqa: BLE001
            self.log(f"confirm_page_name: could not read page name: {e}")
            return ""

    def upload_video(self, video_path: str, timeout_s: int = UPLOAD_TIMEOUT_S) -> bool:
        page = self.page
        btn = page.get_by_text("เพิ่มวิดีโอ", exact=True).first
        with page.expect_file_chooser(timeout=15000) as fc_info:
            btn.click()
        fc_info.value.set_files(video_path)

        filename = Path(video_path).name
        deadline = time.time() + timeout_s
        stable_100_reads = 0
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            body = page.evaluate("document.body.innerText")
            idx = body.find(filename)
            snippet = body[idx: idx + 80] if idx >= 0 else ""
            if "100%" in snippet:
                stable_100_reads += 1
                if stable_100_reads >= 2:
                    self.log(f"upload_video: 100% confirmed, snippet={snippet!r}")
                    return True
            else:
                stable_100_reads = 0
        self.log(f"upload_video: TIMED OUT after {timeout_s}s waiting for 100%")
        return False

    def set_caption(self, caption_text: str) -> tuple[bool, str, list[str]]:
        page = self.page
        box = page.locator(f'[aria-label="{CAPTION_BOX_ARIA_LABEL}"]').first
        box.click()
        page.keyboard.insert_text(caption_text)
        page.wait_for_timeout(500)
        readback = box.evaluate("el => el.innerText")
        ok, diff = captions_match(caption_text, readback)
        return ok, readback, diff

    def set_cover(self, cover_path: str) -> bool:
        page = self.page
        tabs = page.get_by_text("อัพโหลดภาพ", exact=True)
        if tabs.count() == 0:
            self.log("set_cover: 'อัพโหลดภาพ' tab not found")
            return False
        tabs.first.click()
        page.wait_for_timeout(800)
        tabs2 = page.get_by_text("อัพโหลดภาพ", exact=True)
        try:
            with page.expect_file_chooser(timeout=10000) as fc:
                tabs2.last.click()
            fc.value.set_files(cover_path)
        except Exception as e:  # noqa: BLE001
            self.log(f"set_cover: file-chooser upload failed: {e}")
            return False
        page.wait_for_timeout(2500)
        body = page.evaluate("document.body.innerText")
        return "เปลี่ยนรูปภาพ" in body  # "Change picture" link only appears once a cover is set

    def _click_next_until(self, marker_text: str, max_clicks: int = STEP_ADVANCE_MAX_CLICKS,
                           per_click_timeout_s: int = STEP_ADVANCE_TIMEOUT_S) -> bool:
        page = self.page
        for attempt in range(max_clicks):
            btn = page.get_by_text("ถัดไป", exact=True).first
            if btn.count() == 0:
                self.log(f"_click_next_until: no 'ถัดไป' button on attempt {attempt + 1}")
                return False
            try:
                btn.click(timeout=5000)
            except Exception as e:  # noqa: BLE001
                self.log(f"_click_next_until: click failed on attempt {attempt + 1}: {e}")
            deadline = time.time() + per_click_timeout_s
            while time.time() < deadline:
                page.wait_for_timeout(1000)
                if marker_text in page.evaluate("document.body.innerText"):
                    return True
            self.log(f"_click_next_until: marker {marker_text!r} not seen after attempt {attempt + 1}, retrying")
        return False

    def advance_to_final_step(self) -> bool:
        if not self._click_next_until("ครอบตัด"):
            self.log("advance_to_final_step: never reached the audio/crop step")
            return False
        if not self._click_next_until(AUDIENCE_HEADING):
            self.log("advance_to_final_step: never reached the final/audience step")
            return False
        return True

    def handle_ai_label(self) -> str:
        """Best-effort: expands advanced distribution settings if present,
        searches for an AI-content-disclosure toggle, turns it on if found.
        Returns a human-readable record of what happened — never raises.
        """
        page = self.page
        adv = page.get_by_text("การตั้งค่าการกระจายขั้นสูง", exact=False).first
        if adv.count() > 0:
            try:
                adv.click()
                page.wait_for_timeout(1000)
            except Exception as e:  # noqa: BLE001
                self.log(f"handle_ai_label: could not expand advanced settings: {e}")

        body = page.evaluate("document.body.innerText")
        hits: list[str] = []
        for pat in AI_LABEL_PATTERNS:
            hits.extend(pat.findall(body))
        if not hits:
            return "no AI-content-disclosure control found in this composer"

        # best-effort: click the nearest toggle/checkbox to the first hit
        toggled = page.evaluate(
            """
            (needle) => {
              const el = [...document.querySelectorAll('*')]
                .find(e => e.children.length === 0 && e.textContent.includes(needle));
              if (!el) return false;
              let node = el;
              for (let i = 0; i < 6 && node; i++) {
                const ctl = node.querySelector && node.querySelector('input[type=checkbox], [role=switch]');
                if (ctl) { ctl.click(); return true; }
                node = node.parentElement;
              }
              return false;
            }
            """,
            hits[0][:40],
        )
        return f"found candidate text {hits[0]!r}; toggle clicked={toggled}"

    def ensure_public_audience(self) -> bool:
        page = self.page
        handle = page.evaluate_handle(
            """
            (descText) => {
              const descs = [...document.querySelectorAll('*')]
                .filter(e => e.children.length === 0 && e.textContent.trim() === descText);
              if (!descs.length) return null;
              let node = descs[0];
              for (let i = 0; i < 6 && node; i++) {
                const radio = node.querySelector && node.querySelector('input[type=radio], [role=radio]');
                if (radio) return radio;
                node = node.parentElement;
              }
              return null;
            }
            """,
            AUDIENCE_PUBLIC_DESC,
        )
        el = handle.as_element()
        if el is None:
            self.log("ensure_public_audience: could not find the Public radio control")
            return False
        el.click()
        return True

    def _find_publish_button(self):
        return self.page.evaluate_handle(
            """
            () => [...document.querySelectorAll('button, [role="button"]')]
              .find(e => e.textContent.trim() === 'แชร์' && e.getBoundingClientRect().width > 50)
            """
        )

    def publish(self) -> bool:
        handle = self._find_publish_button()
        el = handle.as_element()
        if el is None:
            raise PublishRefused("could not locate the real publish ('แชร์') button")
        el.click()
        return True

    def screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=False)


def run(args: argparse.Namespace) -> int:
    caption_text = Path(args.caption_file).expanduser().read_text(encoding="utf-8")
    video_path = str(Path(args.video).expanduser())
    cover_path = str(Path(args.cover).expanduser())

    if not Path(video_path).exists():
        print(f"REFUSED: video not found: {video_path}", file=sys.stderr)
        return 2
    if not Path(cover_path).exists():
        print(f"REFUSED: cover not found: {cover_path}", file=sys.stderr)
        return 2

    fb = FBReelBrowser(args.cdp, args.asset_id)
    try:
        fb.connect()
        fb.open_composer()
        page_name = fb.confirm_page_name()
        print(f"composer opened; Page name shown: {page_name!r}")

        ok = fb.upload_video(video_path)
        if not ok:
            print("REFUSED: upload did not reach a stable 100% before timeout", file=sys.stderr)
            return 3

        cap_ok, readback, diff = fb.set_caption(caption_text)
        print(f"caption readback matches: {cap_ok}")
        if not cap_ok:
            for line in diff:
                print("  " + line, file=sys.stderr)
            print("REFUSED: caption read-back differs from the caption file", file=sys.stderr)
            return 4

        cover_ok = fb.set_cover(cover_path)
        print(f"cover set: {cover_ok}")

        if not fb.advance_to_final_step():
            print("REFUSED: could not reach the final (audience/publish) step", file=sys.stderr)
            return 5

        ai_note = fb.handle_ai_label()
        print(f"AI label: {ai_note}")

        audience_ok = fb.ensure_public_audience()
        print(f"audience set to Public: {audience_ok}")

        shot_path = args.screenshot or "fb_reel_post_dry_run.png"
        fb.screenshot(shot_path)
        print(f"screenshot saved: {shot_path}")

        if args.dry_run:
            print("DRY RUN — stopping before publish, as contracted.")
            return 0

        fb.publish()
        print("PUBLISHED — clicked the real 'แชร์' button exactly once.")
        print("Verify manually in Business Suite → Content before deleting the old post:")
        print("  status must read เผยแพร่แล้ว with no ไม่สำเร็จ / ไม่ได้บันทึกไว้อย่างถูกต้อง")
        return 0
    finally:
        fb.close()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cdp", default="http://127.0.0.1:9230")
    ap.add_argument("--asset-id", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--cover", required=True)
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--screenshot", default=None, help="Path to save the final-step screenshot to.")
    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
