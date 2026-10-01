#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Facebook Business Suite general-post + Story composers for the Page
«ละครสั้นคุณธรรม by ILAG Studio» (task-e4482d34). Reuses tools/fb_reel_post.py
(imported, never copied) for everything the two tools share: Playwright/CDP
connection, the caption box, the comment-identity gate, the duplicate-publish
guard, and the three-state permalink resolver. fb_reel_post.py itself and
tests/test_fb_reel_post.py are untouched by this file.

Modes (see the CTO_ILAG_LakornTheme skill, Rules 5-8, for the daily workflow
this implements):

    photo --image P --caption-file C [--comment-file C1 --comment-file C2]
          [--dry-run] [--screenshot S]
        Business Suite general-post composer: attach photo, set caption,
        Public audience, publish once, verify the permalink, then post the
        comment files in order as the Page (comment 1 pinned, later ones not).

    story --video V [--dry-run] [--screenshot S]
        Business Suite Story composer: attach video, publish once. No
        caption/audience step — Stories have neither (measured, see below).

    comments --permalink URL --comment-file C1 [--comment-file C2]
        Re-run the comment step on an already-published post.

    --page KEY (default "ilag"): looks KEY up in the Page registry
        (config/fb_pages.yaml, --page-registry to point elsewhere) for
        {profile_id, name}. Never a free-text Page name — CEO/CTO addendum
        2026-09-29: "เพจมีเยอะมากและอาจจะไม่มีช่องค้นหา วางระบบให้ดี อย่าให้
        สลับผิดได้" (many Pages, no search box in the identity-switch list —
        a typed name can silently mismatch the real Page).

    --switch-to-page (any mode that comments): if the comment box's own
        identity is wrong, switch to the registry Page by opening
        https://www.facebook.com/<profile_id> and clicking THAT Page's own
        "สลับเลย" (Switch now) button — never the account-menu "ดูโปรไฟล์
        ทั้งหมด" list. Four pre-click checks and two post-click checks all
        must hold, else refuse (exit 7) and click/type nothing — see
        validate_pre_switch/validate_post_switch and "switch-to-page" section
        below. Without --switch-to-page, wrong identity refuses (exit 7) and
        prints the fix. UNVERIFIED LIVE — never run live in this task.

Exit codes — same scheme as fb_reel_post.py:
    0  verified / ok
    2  REFUSED: input file missing, or the publish button could not be
       uniquely located (PublishRefused)
    3  REFUSED: photo/video attach did not confirm before its timeout
    4  REFUSED: caption read-back differs from the caption file
    5  REFUSED: could not set the Public audience radio (photo), or could
       not open the Story composer route (story)
    6  PUBLISHED-UNVERIFIED — never re-publish; rerun `comments` once the
       permalink resolves, or accept the Story as published-but-unconfirmed
    7  REFUSED: comment identity gate (wrong identity, no --switch-to-page,
       or a switch was attempted and the identity is still wrong)
    10 REFUSED: composer identity gate ("โพสต์ไปยัง"/"แชร์ไปยัง" != registry
       name for --page)
    11 REFUSED: duplicate-publish guard (photo only; same 24h window as
       fb_reel_post.py; --allow-repost overrides)
    12 REFUSED: could not connect to Chrome at the CDP port
    13 REFUSED: Facebook login wall detected
    14 REFUSED: unexpected error

## Measured selectors (Chrome :9230, asset_id=1319535331240503, 2026-09-29,
## read-only dry-run exploration — docs/reports/fb-page-post/, never clicked
## Publish/เผยแพร่/แชร์/Share/สลับ/สลับเลย)

General-post composer: `https://business.facebook.com/latest/composer/
?asset_id={asset_id}` — a SINGLE-STEP form (no 3-step wizard like Reels).
Identity heading is "โพสต์ไปยัง" (same zero-width-space quirk as
fb_reel_post.confirm_page_name — reused unchanged, it works as-is here).
Attach trigger: "เพิ่มรูปภาพ/วิดีโอ" (exact text, count=1 before attach;
file-chooser interception confirmed working live — `photo_attach_ok: true`
in measure-findings-2.json). After attach, "ลบรูปภาพ" (Remove photo) appears
— used as the attach-confirmed signal instead of Reels' upload-percentage
text (an image attaches near-instantly, no progress bar was observed).
Caption box: same `CAPTION_BOX_ARIA_LABEL` as fb_reel_post.py, confirmed by
live type+read-back (`caption_readback` matched exactly). Audience heading is
"การตั้งค่าความเป็นส่วนตัว" (Privacy settings) — DIFFERENT wording from
Reels' "ใครสามารถดูคลิปนี้ได้บ้าง" — and the Public radio's own description
text is the FULLER string "ทุกคนทั้งที่ใช้และไม่ใช้ Facebook
จะสามารถเห็นโพสต์ของคุณได้" (Reels' shorter `AUDIENCE_PUBLIC_DESC` prefix
does NOT exact-match here); `public_radio_found: true` confirmed live with
the fuller string. Publish button text is "เผยแพร่" (not Reels' "แชร์") and,
measured live, it is the ONLY DOM node with that exact text
(`publish_button_count: 1`) — so this composer needs none of
`_find_publish_button`'s breadcrumb-avoidance trick.

Story composer: Business Suite Home's own quick-action button
"สร้างสตอรี่" (measured in the buttons list of
`https://business.facebook.com/latest/home?asset_id={asset_id}`) navigates,
on click, to `https://business.facebook.com/latest/story_composer/
?asset_id={asset_id}&ref=biz_web_home_stories&context_ref=HOME` — this is a
REAL app route (client-side navigation, confirmed live). An earlier guess of
a direct `stories_composer` URL (extra trailing "s") is NOT real: it
redirects to Home with `nav_ref=typo_redirect`, the same dead-route
signature fb_reel_post.py's own docstring already documents for a different
guessed URL — so this script always reaches the Story composer by clicking
Home's button, never by guessing the URL. The Story composer's own identity
heading is "แชร์ไปยัง" (not "โพสต์ไปยัง" — a different label,
`confirm_story_page_name` duplicates the zero-width-space fix for this
heading). It reuses the same "เพิ่มรูปภาพ/วิดีโอ" attach trigger. It has NO
caption box and NO audience/privacy picker at all (`contentEditables: []`
measured; Stories are not a "who can see this" surface the way feed posts
are) — so `story` mode skips both steps entirely, by design, not by gap.
Its footer publish button reads "แชร์" (like Reels, not "เผยแพร่" like the
general-post composer) and, measured live on an EMPTY composer, is the only
"แชร์" (exact) button present (distinct from a separate "แชร์เลย" pill near
the top, which is not the footer submit).

## What is UNVERIFIED LIVE (never exercised end-to-end — read before trusting)

- `upload_story_video`: the attach step (click "เพิ่มรูปภาพ/วิดีโอ" inside the
  story composer, file chooser intercepted) and its confirmation WERE measured
  live 2026-10-01 (docs/reports/fb-story-attach/REPORT.md). The page never shows
  the file name or "100%"; the placeholder text goes away ~2.5 s in, mid-upload;
  "กำลังอัพโหลดสื่อ" then "กำลังประมวลผลสื่อ" show until a `<video>` element
  (readyState 4, duration 24.1 s for the 24 s test file) appears at ~30 s. The
  positive marker is that loaded `<video>` (`story_attach_marker`); the
  placeholder and the two status lines can only veto. Not yet re-run end to end
  after the fix, and never run through a real publish.
- `verify_story_published`: best-effort read of the Page's public surface for
  a "story tray" marker. The exact marker text was never measured against a
  real published Story (this task published nothing) — a miss is treated as
  PUBLISHED-UNVERIFIED (exit 6), never FAILED, exactly like
  `resolve_permalink`'s own "absence is not evidence" rule.
- `list_public_video_candidates` (overridden here to scan `/posts/`,
  `/photo.php`, `/photo/` anchors instead of `/videos/`/`/reel/`): the anchor
  patterns are Facebook's general permalink shapes, not measured against a
  real post from this Page (this task published nothing).
- `switch_to_page_identity`: implements the CEO/CTO addendum's (cb63de3a,
  2026-09-29) exact switch procedure — navigate to
  https://www.facebook.com/<profile_id>, then before clicking "สลับเลย"
  require ALL FOUR: URL contains profile_id; first h2 text == the registry
  name (h1 is the generic "จัดการเพจ" heading, not the Page name); exactly
  one "สลับเลย" button; its banner (the button's 4th ancestor <div>) reads
  "สลับไปใช้เพจ <name> เพื่อเริ่มจัดการ" (`validate_pre_switch`). After the
  click, `post_comments_with_switch` re-opens the permalink and requires
  BOTH: cookie i_user == profile_id; the comment box's identity (the already
  parsed name behind its own aria-label "แสดงความคิดเห็นในชื่อ <name>", via
  the reused frp.parse_comment_identity/find_comment_box) == <name>
  (`validate_post_switch`). Any check failing refuses (exit 7) with nothing
  clicked/typed. Documented history this exists
  to fix: EP4's Reel comment was refused (exit 7) because the comment box
  read "Dorsine Gobb" instead of the Page
  (docs/reports/cto-cb63de3a-ep4-post/REPORT.md). Measured live 2026-09-29
  00:3x by the CTO: before the click cookie i_user is absent; after, i_user
  == the clicked Page's own profile_id, and the "สลับเลย" button is gone on
  reload. **Never run live in this task** — `validate_pre_switch` and
  `validate_post_switch` are pure and unit-tested with fixtures instead;
  `switch_to_page_identity` itself exists for the CTO to invoke later, with
  `--switch-to-page`, after CEO/CTO sign-off.

Everything else — the pure decision functions, `FBReelBrowser`,
`do_first_comment`, and the whole permalink/duplicate-guard machinery — is
imported from tools/fb_reel_post.py unchanged; only the DOM-facing methods
this composer's different markup actually requires are overridden on the
`FBPageBrowser` subclass below.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from tools import fb_reel_post as frp

DEFAULT_ASSET_ID = "1319535331240503"
DEFAULT_PAGE_REGISTRY_PATH = "config/fb_pages.yaml"
DEFAULT_PAGE_KEY = "ilag"

PHOTO_COMPOSER_URL_TMPL = "https://business.facebook.com/latest/composer/?asset_id={asset_id}"
STORY_HOME_URL_TMPL = "https://business.facebook.com/latest/home?asset_id={asset_id}"
STORY_CREATE_BUTTON_TEXT = "สร้างสตอรี่"
ATTACH_BUTTON_TEXT = "เพิ่มรูปภาพ/วิดีโอ"
PUBLISH_BUTTON_TEXT_PHOTO = "เผยแพร่"
STORY_PUBLISH_BUTTON_TEXT = "แชร์"
STORY_COMPOSER_URL_MARKER = "story_composer"
PHOTO_REMOVE_CONFIRM_TEXT = "ลบรูปภาพ"
AUDIENCE_PUBLIC_DESC_POST = "ทุกคนทั้งที่ใช้และไม่ใช้ Facebook จะสามารถเห็นโพสต์ของคุณได้"
PHOTO_ATTACH_TIMEOUT_S = 60
# Story attach proof, measured live 2026-10-01 (docs/reports/fb-story-attach/REPORT.md):
# the placeholder vanishes ~2.5 s after set_files while the file is still uploading,
# so its absence proves nothing. The two status lines show during upload/processing.
STORY_PLACEHOLDER_TEXT = "อัพโหลดสื่อเพื่อดูตัวอย่างสตอรี่ของคุณ"
STORY_ATTACH_BUSY_TEXTS = ("กำลังอัพโหลดสื่อ", "กำลังประมวลผลสื่อ")
STORY_ATTACH_STATE_JS = """
() => ({
  body: document.body.innerText,
  videos: [...document.querySelectorAll('video')].map(v => ({readyState: v.readyState, duration: v.duration})),
})
"""


# -- pure decision logic (unit-tested with fixtures; never exercised live) ---

def comment_identity_decision(identity: str | None, expected_page_name: str, switch_to_page: bool) -> dict:
    """Pure. Decides what to do with a comment box's own identity read.
    Returns {"action": "post" | "switch_then_recheck" | "refuse", "reason": str}.
    Never touches a browser — see module docstring's "switch-to-page" note
    for why the actual switch click is never run live in this task.
    """
    if identity == expected_page_name:
        return {"action": "post", "reason": "identity already correct"}
    if not switch_to_page:
        return {
            "action": "refuse",
            "reason": (
                f"comment box reads {identity!r}, expected {expected_page_name!r}. "
                f"Re-run with --switch-to-page to have this tool click the Page's own "
                f"'สลับเลย' (Switch now) button first, or switch identity manually in Chrome."
            ),
        }
    return {
        "action": "switch_then_recheck",
        "reason": f"identity {identity!r} != {expected_page_name!r}, --switch-to-page given",
    }


def story_attach_marker(body: str, videos: list[dict]) -> str | None:
    """Pure. Returns the positive marker proving the Story video is attached AND
    processed, or None. The marker is a <video> element whose metadata loaded
    (readyState >= 1, finite duration > 0): measured live 2026-10-01 it is absent
    at t=0 and during upload/processing (~30 s for a 22 MB / 24 s file) and present
    after. The placeholder text and the two busy status lines are extra conditions
    that can only veto; their absence is never enough on its own."""
    if STORY_PLACEHOLDER_TEXT in body:
        return None
    if any(text in body for text in STORY_ATTACH_BUSY_TEXTS):
        return None
    for v in videos:
        duration, ready = v.get("duration"), v.get("readyState")
        if isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0 \
                and isinstance(ready, int) and ready >= 1:
            return f"video element (readyState={ready}, duration={duration:.1f}s)"
    return None


# -- Page registry (CEO/CTO addendum 2026-09-29): key -> {profile_id, name}. -
# -- "เพจมีเยอะมากและอาจจะไม่มีช่องค้นหา วางระบบให้ดี อย่าให้สลับผิดได้" — ----
# -- tools take --page <key>, never a free-text name. ------------------------

def parse_page_registry(yaml_text: str) -> dict[str, dict[str, str]]:
    """Pure (given text, not a path). Returns {key: {"profile_id": str, "name": str}}."""
    data = yaml.safe_load(yaml_text) or {}
    pages = data.get("pages") or {}
    return {key: {"profile_id": str(row["profile_id"]), "name": row["name"]} for key, row in pages.items()}


def load_page_registry(path: str = DEFAULT_PAGE_REGISTRY_PATH) -> dict[str, dict[str, str]]:
    return parse_page_registry(Path(path).read_text(encoding="utf-8"))


def resolve_page(registry: dict[str, dict[str, str]], key: str) -> dict[str, str]:
    """Pure. Returns {"profile_id": str, "name": str} for key, or raises
    ValueError with the known keys listed — the CLI turns this into a clear
    REFUSED exit 2, never a raw traceback."""
    if key not in registry:
        raise ValueError(f"unknown --page {key!r}; known keys: {sorted(registry.keys())}")
    return registry[key]


# -- identity-switch validation (CEO/CTO addendum 2026-09-29) — pure, --------
# -- unit-tested with fixtures; the live click is never run in this task ----

def validate_pre_switch(
    url: str, first_h2_text: str, switch_button_count: int, banner_text: str,
    profile_id: str, expected_name: str,
) -> dict:
    """Pure. All four checks must hold before clicking 'สลับเลย', else
    refuse — switching only ever happens via https://www.facebook.com/
    <profile_id>, NEVER via the account-menu 'ดูโปรไฟล์ทั้งหมด' list (many
    Pages, no search box — that is where a wrong pick happens). Returns
    {"ok": bool, "reason": str}."""
    if profile_id not in url:
        return {"ok": False, "reason": f"URL does not contain profile_id {profile_id!r}: {url!r}"}
    if first_h2_text != expected_name:
        return {
            "ok": False,
            "reason": f"first h2 is {first_h2_text!r}, expected the registry name {expected_name!r} "
                      f"(h1 is the generic 'จัดการเพจ' heading, not the Page name)",
        }
    if switch_button_count != 1:
        return {"ok": False, "reason": f"expected exactly one 'สลับเลย' button, found {switch_button_count}"}
    expected_banner = f"สลับไปใช้เพจ {expected_name} เพื่อเริ่มจัดการ"
    if banner_text != expected_banner:
        return {"ok": False, "reason": f"banner text is {banner_text!r}, expected {expected_banner!r}"}
    return {"ok": True, "reason": "all pre-switch checks passed"}


def validate_post_switch(
    cookie_i_user: str | None, comment_identity: str | None,
    profile_id: str, expected_name: str,
) -> dict:
    """Pure. Both checks must hold after clicking 'สลับเลย', else refuse and
    type nothing. Measured live 2026-09-29: before the click, cookie i_user
    is absent; after, i_user == the clicked Page's own profile_id, and the
    'สลับเลย' button is gone on reload.

    comment_identity is the NAME already extracted from the comment box's own
    aria-label — i.e. frp.parse_comment_identity(aria_label), the same value
    find_comment_box() returns — not the raw aria-label string. Facebook's
    aria-label has two observed prefix phrasings ("...ในชื่อ"/"...ในนาม",
    see frp.COMMENT_IDENTITY_RE); comparing the already-parsed name sidesteps
    re-deriving that prefix a second time and is equivalent to the addendum's
    "aria-label == 'แสดงความคิดเห็นในชื่อ <name>'" check for either phrasing.
    Returns {"ok": bool, "reason": str}."""
    if cookie_i_user != profile_id:
        return {"ok": False, "reason": f"cookie i_user is {cookie_i_user!r}, expected {profile_id!r}"}
    if comment_identity != expected_name:
        return {
            "ok": False,
            "reason": f"comment box identity is {comment_identity!r}, expected {expected_name!r} "
                      f"(aria-label should read 'แสดงความคิดเห็นในชื่อ {expected_name}')",
        }
    return {"ok": True, "reason": "all post-switch checks passed"}


class FBPageBrowser(frp.FBReelBrowser):
    """Subclasses FBReelBrowser to reuse connect/close/new_tab, the caption
    box, the comment-identity/pin/delete machinery, the activity-feed reader,
    and the composer identity-check pattern. Only the DOM-facing methods this
    composer's different markup requires are overridden — see module
    docstring's "Measured selectors" section for what each one is based on.
    """

    def goto_photo_composer(self):
        self.page.goto(
            PHOTO_COMPOSER_URL_TMPL.format(asset_id=self.asset_id),
            wait_until="domcontentloaded", timeout=60000,
        )
        # Measured 2026-09-29 (pass 1): a click fired right after goto missed
        # the lazily-rendered attach button. Pass 2's 5s wait did not.
        self.page.wait_for_timeout(5000)
        self.page.evaluate(frp.MUTE_JS)
        return self.page

    def goto_story_composer(self, timeout_s: int = 20) -> bool:
        """Clicks Home's own 'สร้างสตอรี่' quick-action — see module
        docstring for why this script never navigates to a guessed Story
        composer URL directly. Returns True once the URL actually carries
        story_composer."""
        self.page.goto(
            STORY_HOME_URL_TMPL.format(asset_id=self.asset_id),
            wait_until="domcontentloaded", timeout=60000,
        )
        self.page.wait_for_timeout(3000)
        self.page.evaluate(frp.MUTE_JS)
        btn = self.page.get_by_text(STORY_CREATE_BUTTON_TEXT, exact=True)
        if btn.count() == 0:
            self.log(f"goto_story_composer: {STORY_CREATE_BUTTON_TEXT!r} button not found on Home")
            return False
        try:
            btn.first.click(timeout=5000)
        except Exception as e:  # noqa: BLE001
            self.log(f"goto_story_composer: click failed: {e}")
            return False
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.page.wait_for_timeout(500)
            if STORY_COMPOSER_URL_MARKER in self.page.url:
                self.page.wait_for_timeout(1500)
                self.page.evaluate(frp.MUTE_JS)
                return True
        self.log(f"goto_story_composer: URL never reached {STORY_COMPOSER_URL_MARKER!r}, stuck at {self.page.url!r}")
        return False

    def confirm_story_page_name(self) -> str:
        """Same zero-width-space fix as FBReelBrowser.confirm_page_name, but
        for the Story composer's own heading, measured live as 'แชร์ไปยัง'
        (a different label from the general composer's 'โพสต์ไปยัง')."""
        try:
            txt = self.page.evaluate(
                """
                () => {
                  const heading = [...document.querySelectorAll('*')]
                    .find(e => e.children.length === 0 && e.textContent.trim() === 'แชร์ไปยัง');
                  if (!heading) return '';
                  let node = heading.parentElement;
                  for (let i = 0; i < 6 && node; i++) {
                    const t = node.innerText || '';
                    const lines = t.split('\\n')
                      .map(s => s.split('\\u200b').join('').trim())
                      .filter(s => s !== '' && s !== 'แชร์ไปยัง');
                    if (lines.length) return lines[0];
                    node = node.parentElement;
                  }
                  return '';
                }
                """
            )
            return txt or ""
        except Exception as e:  # noqa: BLE001
            self.log(f"confirm_story_page_name: could not read page name: {e}")
            return ""

    def upload_photo(self, image_path: str, timeout_s: int = PHOTO_ATTACH_TIMEOUT_S) -> bool:
        page = self.page
        btn = page.get_by_text(ATTACH_BUTTON_TEXT, exact=True).first
        with page.expect_file_chooser(timeout=15000) as fc_info:
            btn.click()
        fc_info.value.set_files(image_path)
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            page.wait_for_timeout(1500)
            body = page.evaluate("document.body.innerText")
            if PHOTO_REMOVE_CONFIRM_TEXT in body:
                self.log(f"upload_photo: {PHOTO_REMOVE_CONFIRM_TEXT!r} control confirms the image attached")
                return True
        self.log(f"upload_photo: TIMED OUT after {timeout_s}s waiting for the attach confirmation")
        return False

    def upload_story_video(self, video_path: str, timeout_s: int = frp.UPLOAD_TIMEOUT_S) -> bool:
        """Attach via the composer's own attach button, then require the positive
        marker from story_attach_marker on 2 consecutive reads. The page never
        shows the file name or a "100%" label, and the placeholder text goes away
        ~2.5 s in, mid-upload — so neither can confirm an attach. Measured live
        2026-10-01: docs/reports/fb-story-attach/REPORT.md."""
        page = self.page
        btn = page.get_by_text(ATTACH_BUTTON_TEXT, exact=True).first
        with page.expect_file_chooser(timeout=15000) as fc_info:
            btn.click()
        fc_info.value.set_files(video_path)
        deadline = time.time() + timeout_s
        stable_reads = 0
        placeholder_gone = False
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            state = page.evaluate(STORY_ATTACH_STATE_JS)
            placeholder_gone = STORY_PLACEHOLDER_TEXT not in state["body"]
            marker = story_attach_marker(state["body"], state["videos"])
            if marker:
                stable_reads += 1
                if stable_reads >= 2:
                    self.log(f"upload_story_video: attach confirmed, marker={marker}")
                    return True
            else:
                stable_reads = 0
        self.log(
            f"upload_story_video: TIMED OUT after {timeout_s}s waiting for a positive attach marker "
            f"(loaded <video> element); placeholder_gone={placeholder_gone}"
        )
        return False

    def ensure_public_audience_post(self) -> bool:
        handle = self.page.evaluate_handle(
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
            AUDIENCE_PUBLIC_DESC_POST,
        )
        el = handle.as_element()
        if el is None:
            self.log("ensure_public_audience_post: could not find the Public radio control")
            return False
        el.click()
        return True

    def _find_publish_button_by_text(self, text: str):
        """Measured live 2026-09-29: unlike Reels' composer, neither this
        composer's 'เผยแพร่' nor the Story composer's 'แชร์' collides with a
        breadcrumb chip — each is the only DOM node with that exact text, so
        a plain exact-text lookup is enough (no _find_publish_button trick)."""
        loc = self.page.get_by_text(text, exact=True)
        if loc.count() != 1:
            self.log(f"_find_publish_button_by_text({text!r}): expected exactly 1 match, found {loc.count()}")
            return None
        return loc.first

    def publish_photo(self) -> bool:
        btn = self._find_publish_button_by_text(PUBLISH_BUTTON_TEXT_PHOTO)
        if btn is None:
            raise frp.PublishRefused(f"could not uniquely locate the real publish ({PUBLISH_BUTTON_TEXT_PHOTO!r}) button")
        btn.click()
        return True

    def publish_story(self) -> bool:
        btn = self._find_publish_button_by_text(STORY_PUBLISH_BUTTON_TEXT)
        if btn is None:
            raise frp.PublishRefused(f"could not uniquely locate the real publish ({STORY_PUBLISH_BUTTON_TEXT!r}) button")
        btn.click()
        return True

    def list_public_video_candidates(self, page_id: str) -> list[tuple[str, str]]:
        """Override for photo POSTS, not videos/reels — same duck-typed name
        frp.resolve_permalink() calls. UNVERIFIED LIVE, see module docstring."""
        self.page.goto(f"https://www.facebook.com/{page_id}", wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(3000)
        self.page.evaluate(frp.MUTE_JS)
        hrefs = self.page.evaluate(
            """
            () => [...document.querySelectorAll(
                'a[href*="/posts/"], a[href*="/photo.php"], a[href*="/photo/"]'
            )].map(a => a.href)
            """
        )
        seen: dict[str, str] = {}
        for href in hrefs:
            m = re.search(r"/posts/(\d+)", href) or re.search(r"fbid=(\d+)", href) or re.search(r"/photo/(\d+)", href)
            if m and m.group(1) not in seen:
                seen[m.group(1)] = href
        return list(seen.items())

    def _read_cookie(self, name: str) -> str | None:
        for c in self.page.context.cookies():
            if c["name"] == name:
                return c["value"]
        return None

    def switch_to_page_identity(self, profile_id: str, expected_page_name: str) -> dict:
        """UNVERIFIED LIVE — NEVER RUN in task-e4482d34, per the brief.
        Implements the CEO/CTO addendum's exact procedure (cb63de3a,
        2026-09-29): switch ONLY by opening https://www.facebook.com/
        <profile_id> and clicking THAT Page's own 'สลับเลย' button — never
        the account-menu 'ดูโปรไฟล์ทั้งหมด' list (many Pages, no search box:
        that is where a wrong pick happens). All four validate_pre_switch
        checks must hold, else refuse and click nothing. Returns
        {"ok": bool, "reason": str}."""
        page = self.page
        page.goto(f"https://www.facebook.com/{profile_id}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        url = page.url
        first_h2 = page.evaluate(
            "() => { const h = document.querySelector('h2'); return h ? h.textContent.trim() : ''; }"
        )
        switch_btn = page.get_by_text("สลับเลย", exact=True)
        btn_count = switch_btn.count()
        banner_text = ""
        if btn_count == 1:
            try:
                banner_text = switch_btn.first.evaluate(
                    """
                    (el) => {
                      let node = el.parentElement, divsSeen = 0, ancestor = null;
                      while (node) {
                        if (node.tagName === 'DIV') {
                          divsSeen++;
                          ancestor = node;
                          if (divsSeen === 4) break;
                        }
                        node = node.parentElement;
                      }
                      return ancestor ? ancestor.textContent.trim() : '';
                    }
                    """
                ) or ""
            except Exception as e:  # noqa: BLE001
                self.log(f"switch_to_page_identity: could not read the banner (4th ancestor div): {e}")
        check = validate_pre_switch(url, first_h2, btn_count, banner_text, profile_id, expected_page_name)
        if not check["ok"]:
            self.log(f"switch_to_page_identity: pre-switch check failed: {check['reason']}")
            return {"ok": False, "reason": check["reason"]}
        try:
            switch_btn.first.click(timeout=5000)
            page.wait_for_timeout(2000)
        except Exception as e:  # noqa: BLE001
            self.log(f"switch_to_page_identity: click failed: {e}")
            return {"ok": False, "reason": f"click failed: {e}"}
        return {"ok": True, "reason": "clicked 'สลับเลย' after all pre-switch checks passed"}


def verify_story_published(fb: "FBPageBrowser", page_id: str) -> tuple[bool, str]:
    """Best-effort, UNVERIFIED LIVE (this task never published a Story — see
    module docstring). found=False is NOT evidence of failure, same rule as
    frp.resolve_permalink — it drives PUBLISHED-UNVERIFIED (exit 6), never
    FAILED."""
    fb.page.goto(f"https://www.facebook.com/{page_id}", wait_until="domcontentloaded", timeout=60000)
    fb.page.wait_for_timeout(3000)
    fb.page.evaluate(frp.MUTE_JS)
    body = fb.get_body_text()
    if "สตอรี่ของคุณ" in body or "Your story" in body:
        return True, "Page's own public surface shows a story-tray marker"
    return False, "no story-tray marker found on the Page's public surface (best-effort, unverified selector)"


def post_followup_comment(fb: "FBPageBrowser", permalink: str, comment_text: str, expected_page_name: str) -> dict:
    """Like frp.do_first_comment but never pins — comment 2+ per the
    CTO_ILAG_LakornTheme workflow ("comment 1 gets pinned"). Reuses the same
    pure helpers do_first_comment uses, minus the pin/author-verify tail."""
    fb.open_permalink(permalink)
    if fb.check_login_wall():
        return {"ok": False, "reason": "login wall", "skipped_duplicate": False}
    fb.expand_see_more()
    body_before = fb.get_body_text()
    if frp.body_contains_text(body_before, comment_text):
        return {"ok": True, "reason": "already posted (idempotent skip)", "skipped_duplicate": True}
    box, identity = fb.find_comment_box()
    if box is None or identity != expected_page_name:
        return {
            "ok": False, "skipped_duplicate": False,
            "reason": f"identity gate failed: found {identity!r}, expected {expected_page_name!r}",
        }
    if not fb.post_comment(box, comment_text):
        return {"ok": False, "skipped_duplicate": False, "reason": "submit failed"}
    body_after = fb.get_body_text()
    if not frp.body_contains_text(body_after, comment_text):
        return {"ok": False, "skipped_duplicate": False, "reason": "comment text not found after submit"}
    return {"ok": True, "skipped_duplicate": False, "reason": "posted"}


def post_comments_with_switch(
    fb: "FBPageBrowser", permalink: str, comment_texts: list[str],
    expected_page_name: str, switch_to_page: bool, profile_id: str | None = None,
) -> dict:
    """Applies the --switch-to-page identity gate ONCE, then posts
    comment_texts in order (comment 1 via frp.do_first_comment, pinned; the
    rest via post_followup_comment, not pinned). Returns
    {"ok": bool, "reason": str, "results": list[dict]}.

    profile_id is required only when a switch actually happens
    (decision == "switch_then_recheck") — switch_to_page_identity navigates
    away to facebook.com/<profile_id>, so this function re-opens the
    permalink afterwards and re-reads the comment box before running
    validate_post_switch (cookie i_user + comment-box aria-label), per the
    CEO/CTO addendum (cb63de3a, 2026-09-29)."""
    fb.open_permalink(permalink)
    if fb.check_login_wall():
        return {"ok": False, "reason": "login wall", "results": []}
    fb.expand_see_more()
    _, identity = fb.find_comment_box()
    decision = comment_identity_decision(identity, expected_page_name, switch_to_page)
    if decision["action"] == "refuse":
        return {"ok": False, "reason": decision["reason"], "results": []}
    if decision["action"] == "switch_then_recheck":
        if not profile_id:
            return {"ok": False, "reason": "switch requested but no profile_id given", "results": []}
        switch_result = fb.switch_to_page_identity(profile_id, expected_page_name)
        if not switch_result["ok"]:
            return {"ok": False, "reason": f"switch refused: {switch_result['reason']}", "results": []}
        fb.open_permalink(permalink)
        if fb.check_login_wall():
            return {"ok": False, "reason": "login wall", "results": []}
        fb.expand_see_more()
        _, identity = fb.find_comment_box()
        cookie_i_user = fb._read_cookie("i_user")
        post_check = validate_post_switch(cookie_i_user, identity, profile_id, expected_page_name)
        if not post_check["ok"]:
            return {"ok": False, "results": [], "reason": f"post-switch check failed: {post_check['reason']}"}

    results: list[dict] = []
    for i, text in enumerate(comment_texts):
        r = frp.do_first_comment(fb, permalink, text, expected_page_name) if i == 0 \
            else post_followup_comment(fb, permalink, text, expected_page_name)
        results.append(r)
        if not r["ok"]:
            return {"ok": False, "reason": r["reason"], "results": results}
    return {"ok": True, "reason": "posted", "results": results}


def _print_permalink_result(result: dict) -> int:
    outcome = result["outcome"]
    if outcome == "verified":
        print(f"VERIFIED {result['url']}")
    elif outcome == "published_unverified":
        print("PUBLISHED-UNVERIFIED")
        print(result["evidence"])
    else:
        print(f"FAILED {result['evidence']}")
    return frp.outcome_to_exit_code(outcome)


def _print_comments_result(permalink: str, result: dict) -> int:
    if result["ok"]:
        pinned_flags = [r.get("pinned", False) for r in result["results"]]
        print(f"COMMENTS {permalink} count={len(result['results'])} pinned={pinned_flags}")
        return 0
    print(f"REFUSED: {result['reason']}", file=sys.stderr)
    return 7


def run_photo(args: argparse.Namespace) -> int:
    page = _resolve_page(args)
    if page is None:
        return 2
    image_path = str(Path(args.image).expanduser())
    if not Path(image_path).exists():
        print(f"REFUSED: image not found: {image_path}", file=sys.stderr)
        return 2
    caption_text = Path(args.caption_file).expanduser().read_text(encoding="utf-8")
    comment_texts = [Path(p).expanduser().read_text(encoding="utf-8") for p in args.comment_file]

    fb = FBPageBrowser(args.cdp, args.asset_id)
    try:
        fb.connect()
        fb.new_tab()

        if not args.allow_repost:
            activity_text = fb.read_activity_feed_text(args.asset_id)
            row = frp.find_activity_row_for_caption(activity_text, caption_text)
            if row and frp.is_recent_duplicate(row, datetime.now()):
                print(
                    "REFUSED: a post with this caption's first line was already published "
                    "within the last 24h:", file=sys.stderr,
                )
                print(row, file=sys.stderr)
                print("Use --allow-repost to publish anyway.", file=sys.stderr)
                return 11

        fb.goto_photo_composer()
        if fb.check_login_wall():
            print("REFUSED: Chrome shows a Facebook login wall.", file=sys.stderr)
            return 13

        page_name = fb.confirm_page_name()
        print(f"composer opened; Page name shown: {page_name!r}")
        if page_name != page["name"]:
            print(f"REFUSED: composer identity gate — expected Page {page['name']!r}, saw {page_name!r}", file=sys.stderr)
            return 10

        if not fb.upload_photo(image_path):
            print("REFUSED: photo attach did not confirm before timeout", file=sys.stderr)
            return 3

        cap_ok, readback, diff = fb.set_caption(caption_text)
        print(f"caption readback matches: {cap_ok}")
        if not cap_ok:
            for line in diff:
                print("  " + line, file=sys.stderr)
            print("REFUSED: caption read-back differs from the caption file", file=sys.stderr)
            return 4

        if not fb.ensure_public_audience_post():
            print("REFUSED: could not set the Public audience radio", file=sys.stderr)
            return 5
        print("audience set to Public: True")

        shot_path = args.screenshot or "fb_page_post_photo_dry_run.png"
        fb.screenshot(shot_path)
        print(f"screenshot saved: {shot_path}")

        if args.dry_run:
            print("DRY RUN — stopping before publish, as contracted.")
            return 0

        fb.publish_photo()
        print(f"PUBLISHED — clicked the real {PUBLISH_BUTTON_TEXT_PHOTO!r} button exactly once.")

        result = frp.resolve_permalink(fb, page["profile_id"], args.asset_id, caption_text, timeout_s=args.permalink_timeout)
        exit_code = _print_permalink_result(result)
        if result["outcome"] != "verified":
            if result["outcome"] == "published_unverified":
                print(
                    "Comments skipped: not VERIFIED yet. Rerun the 'comments' mode with "
                    "--permalink once it resolves.", file=sys.stderr,
                )
            return exit_code

        if comment_texts:
            comment_result = post_comments_with_switch(
                fb, result["url"], comment_texts, page["name"], args.switch_to_page, page["profile_id"],
            )
            return _print_comments_result(result["url"], comment_result)
        return exit_code
    finally:
        fb.close()


def run_story(args: argparse.Namespace) -> int:
    page = _resolve_page(args)
    if page is None:
        return 2
    video_path = str(Path(args.video).expanduser())
    if not Path(video_path).exists():
        print(f"REFUSED: video not found: {video_path}", file=sys.stderr)
        return 2

    fb = FBPageBrowser(args.cdp, args.asset_id)
    try:
        fb.connect()
        fb.new_tab()

        if not fb.goto_story_composer():
            print(
                "REFUSED: could not open the Story composer (Home's "
                f"{STORY_CREATE_BUTTON_TEXT!r} button missing, or navigation never "
                "reached the story_composer route)", file=sys.stderr,
            )
            return 5
        if fb.check_login_wall():
            print("REFUSED: Chrome shows a Facebook login wall.", file=sys.stderr)
            return 13

        page_name = fb.confirm_story_page_name()
        print(f"story composer opened; Page name shown: {page_name!r}")
        if page_name != page["name"]:
            print(f"REFUSED: composer identity gate — expected Page {page['name']!r}, saw {page_name!r}", file=sys.stderr)
            return 10

        if not fb.upload_story_video(video_path):
            print(
                "REFUSED: video attach did not confirm before timeout "
                "(no loaded <video> marker — see upload_story_video's log line)", file=sys.stderr,
            )
            return 3

        shot_path = args.screenshot or "fb_page_post_story_dry_run.png"
        fb.screenshot(shot_path)
        print(f"screenshot saved: {shot_path}")

        if args.dry_run:
            print("DRY RUN — stopping before publish, as contracted.")
            return 0

        fb.publish_story()
        print(f"PUBLISHED — clicked the real {STORY_PUBLISH_BUTTON_TEXT!r} button exactly once.")

        found, evidence = verify_story_published(fb, page["profile_id"])
        if found:
            print(f"VERIFIED {evidence}")
            return 0
        print("PUBLISHED-UNVERIFIED")
        print(evidence)
        return 6
    finally:
        fb.close()


def run_comments(args: argparse.Namespace) -> int:
    page = _resolve_page(args)
    if page is None:
        return 2
    comment_texts = [Path(p).expanduser().read_text(encoding="utf-8") for p in args.comment_file]
    fb = FBPageBrowser(args.cdp, args.asset_id)
    try:
        fb.connect()
        fb.new_tab()
        result = post_comments_with_switch(
            fb, args.permalink, comment_texts, page["name"], args.switch_to_page, page["profile_id"],
        )
        return _print_comments_result(args.permalink, result)
    finally:
        fb.close()


def run(args: argparse.Namespace) -> int:
    if args.mode == "photo":
        return run_photo(args)
    if args.mode == "story":
        return run_story(args)
    if args.mode == "comments":
        return run_comments(args)
    raise AssertionError(f"unknown mode {args.mode!r}")  # argparse subparsers(required=True) guards this


def _add_common_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--cdp", default="http://127.0.0.1:9230")
    sp.add_argument("--asset-id", default=DEFAULT_ASSET_ID)
    sp.add_argument(
        "--page", default=DEFAULT_PAGE_KEY,
        help="Page registry key (config/fb_pages.yaml), never a free-text Page name",
    )
    sp.add_argument("--page-registry", default=DEFAULT_PAGE_REGISTRY_PATH)
    sp.add_argument(
        "--switch-to-page", action="store_true",
        help="if the comment box identity is wrong, switch to the --page Page by "
             "opening facebook.com/<profile_id> and clicking its own 'สลับเลย' "
             "(Switch now) button — UNVERIFIED LIVE, see module docstring; without "
             "this flag, wrong identity refuses (exit 7)",
    )


def _resolve_page(args: argparse.Namespace) -> dict | None:
    """Loads the registry and resolves --page, printing REFUSED (never a raw
    traceback) on a missing file or an unknown key. Returns None on failure —
    callers must treat that as exit 2."""
    try:
        registry = load_page_registry(args.page_registry)
        return resolve_page(registry, args.page)
    except (OSError, ValueError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return None


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)

    p_photo = sub.add_parser("photo")
    _add_common_args(p_photo)
    p_photo.add_argument("--image", required=True)
    p_photo.add_argument("--caption-file", required=True)
    p_photo.add_argument("--comment-file", action="append", default=[])
    p_photo.add_argument("--dry-run", action="store_true")
    p_photo.add_argument("--screenshot", default=None)
    p_photo.add_argument("--allow-repost", action="store_true")
    p_photo.add_argument("--permalink-timeout", type=int, default=frp.PERMALINK_POLL_TIMEOUT_S)

    p_story = sub.add_parser("story")
    _add_common_args(p_story)
    p_story.add_argument("--video", required=True)
    p_story.add_argument("--dry-run", action="store_true")
    p_story.add_argument("--screenshot", default=None)

    p_comments = sub.add_parser("comments")
    _add_common_args(p_comments)
    p_comments.add_argument("--permalink", required=True)
    p_comments.add_argument("--comment-file", action="append", default=[], required=True)

    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    try:
        return run(args)
    except frp.PublishRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — never a raw traceback for a Chrome/CDP problem
        msg = str(e)
        if "context management is not supported" in msg or "could not connect to" in msg or "0 tabs" in msg:
            print(
                f"REFUSED: could not connect to Chrome at the CDP port ({args.cdp}). "
                f"Is it running with a tab open? If 0 tabs: "
                f"curl -X PUT '{args.cdp}/json/new?about:blank'. Detail: {msg}",
                file=sys.stderr,
            )
            return 12
        print(f"REFUSED: unexpected error: {msg}", file=sys.stderr)
        return 14


if __name__ == "__main__":
    sys.exit(main())
