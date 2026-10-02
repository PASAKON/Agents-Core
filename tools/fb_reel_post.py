#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Facebook Business Suite Reels composer — zero-model, one-shot poster
(task-c6bd5ba6, docs/reports/banchi-fb-repost3/REPORT.md; permalink+comment
work task-cfdc75a8, docs/ops/briefs/fb-reel-permalink-first-comment.md).

STANDALONE — no Claude in the loop, zero token cost at runtime, same pattern
as tools/flow_shoot.py: Playwright over CDP against a dedicated Chrome
(profile ~/.fb-automation/chrome-profile, port 9230, signed in as Dorsine
Gobb — see the BROWSER_OPERATOR_Protocol_Playbook skill). Replaces the manual composer flow
that broke a Reel post twice (docs/reports/banchi-fb-unavailable/REPORT.md,
banchi-fb-repost2/REPORT.md) by editing it after publish — this script NEVER
edits a post once published; a fresh run is the only way to change one.

Full publish:
    .venv/bin/python tools/fb_reel_post.py \\
        --cdp http://127.0.0.1:9230 --asset-id 1319535331240503 \\
        --video ~/Downloads/clip-FINAL.mp4 --cover ~/Downloads/cover.png \\
        --caption-file docs/scripts/banchi-reels-caption.txt [--dry-run] \\
        [--first-comment-file docs/scripts/first-comment.txt]

Resolve a permalink on its own (no re-post):
    .venv/bin/python tools/fb_reel_post.py \\
        --resolve-permalink --caption-file docs/scripts/taachang-reels-caption.txt

Comment + pin on an already-published post:
    .venv/bin/python tools/fb_reel_post.py \\
        --comment-only --permalink <public URL> --first-comment-file docs/scripts/first-comment.txt

Delete a marked test post:
    .venv/bin/python tools/fb_reel_post.py --delete-test-post <public URL>

## Part A — three-state permalink resolution (CTO-FEEDBACK.md, 2026-09-26)

Not finding a link is not proof the post failed. `resolve_permalink()` prints
exactly one of:

  VERIFIED <url>          exit 0  a public candidate's own logged-out HTML
                                   (curl -A facebookexternalhit) carries the
                                   caption's first line in its description meta
  PUBLISHED-UNVERIFIED    exit 6  publish happened, nothing has verified yet —
                                   never printed as a failure; rerun --comment-only
                                   once it resolves
  FAILED <evidence>       exit 8  positive evidence only: a Business Suite row
                                   reading ไม่สำเร็จ / ไม่ได้บันทึกไว้อย่างถูกต้อง,
                                   or no row and no public candidate after 30 min

It polls every PERMALINK_POLL_INTERVAL_S for up to PERMALINK_POLL_TIMEOUT_S.
The logged-out check is a real, separate network fetch (subprocess `curl`),
not the signed-in Chrome DOM — see `fetch_permalink_html`/`verify_permalink_content`.
Measured 2026-09-26 (docs/reports/task-cfdc75a8/REPORT.md): film 2's real
permalink carries NO `og:description` at all — the caption lives in a plain
`<meta name="description" content="...">` tag, numeric-entity-encoded Thai
(`&#xe22;` etc.) — so `extract_page_description` checks both. Film 1's dead
reel (1104791208680559, killed by an edit on 2026-09-24) carries neither tag
and a bare "Facebook" `<title>`, which is what a FAILED/unverified page looks
like from the outside.

Business Suite's `content_management/reels?asset_id=` list (used by an
earlier version of this docstring) was observed 2026-09-26 to redirect to
Business Suite Home with `nav_ref=typo_redirect` — it is no longer a route
that resolves, so `read_activity_feed_text` reads Home instead, which still
carries each post's own caption + a Thai timestamp ("26 ก.ย. 2026, 12:07") in
its activity feed. That timestamp format is what `parse_thai_datetime` /
`is_recent_duplicate` parse for the double-publish guard.

## Part B — first comment as the Page, then pin

`--first-comment-file` (chained after a successful VERIFIED) or
`--comment-only` (standalone, on an already-known permalink) post one comment
as the Page and pin it. HARD gate before submitting: the comment box's own
`aria-label` must read "แสดงความคิดเห็นในชื่อ <Page name>" (measured live,
2026-09-26 — `parse_comment_identity`); no such box, or a name that doesn't
match `--page-name`, refuses without ever clicking submit (exit 7). After
submitting, the comment is read back from the DOM by locating a container
that holds both the comment's own first line and the Page's name
(`find_comment_block`); if that container's text does not carry the Page
name, the comment is deleted immediately and the run still exits 7. Posting
an identical comment already on the post is skipped (idempotent), and it is
pinned if not already pinned. `is_duplicate_comment` / `body_contains_text`
are the pure pieces of that check.

## Guards added 2026-09-26 (CTO-FEEDBACK-2.md leak audit — see REPORT.md's
## risk table for the measured/not-tested status of each one)

- **Composer Page-name gate is now hard** (`confirm_page_name`, was
  best-effort/log-only): a mismatch refuses before any upload, exit 10.
- **Double-publish guard**: refuses if the Business Suite activity feed shows
  a post whose caption's first line matches, published in the last 24h
  (`--allow-repost` overrides), exit 11.
- **`set_cover`'s bool now gates the run** — previously logged and continued
  regardless; a cover that failed to attach now refuses, exit 2.
- **Chrome down / 0 tabs / logged out never raises a raw traceback.**
  `main()` catches connect failures (exit 12) and a detected login wall
  (`looks_like_login_wall`, exit 13) with a clear message instead.
- **`--delete-test-post <url>`**: deletes ONLY a post whose LIVE public
  caption (re-read immediately before the click, never cached) carries a
  `[TEST-xxxxxxxx]` marker (`extract_test_marker`/`has_test_marker`); without
  one it refuses, exit 9. This is the guard against ever deleting a real film.

## Thai UI text this script depends on (for the "UI in English" risk —
## report which of these actually rendered Thai on the day you ran this)

composer: "เพิ่มวิดีโอ", "อัพโหลดภาพ", "ถัดไป", "ครอบตัด", "แชร์", "ย้อนกลับ",
"การตั้งค่าการกระจายขั้นสูง", "ใครสามารถดูคลิปนี้ได้บ้าง", "ทุกคนทั้งที่ใช้และไม่ใช้ Facebook",
CAPTION_BOX_ARIA_LABEL. comment/pin: "ดูเพิ่มเติม", "โพสต์ความคิดเห็น",
"ปักหมุดความคิดเห็น"/"ปักหมุด", "ลบ", the `COMMENT_IDENTITY_RE` prefix
"แสดงความคิดเห็นใน(ชื่อ|นาม)". delete: "ตัวเลือกเพิ่มเติมสำหรับวิดีโอ", "ลบวิดีโอ"/"ลบ".
duplicate-publish: `FAILURE_MARKERS`, `THAI_MONTHS` abbreviations.

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

Everything below the browser class (`captions_match`, `verify_permalink_content`,
`classify_permalink_state`, `parse_comment_identity`, `is_duplicate_comment`,
`build_parser`, ...) is pure and unit-tested without a browser
(tests/test_fb_reel_post.py). FBReelBrowser itself is exercised live via
--dry-run / --resolve-permalink / --comment-only before ever publishing for
real, and its DOM-dependent methods are not unit-tested — see the module
docstring's "Thai UI text" list for what they depend on.
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
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

# «ละครสั้นคุณธรรม by ILAG Studio» — the only Page this tool posts as today.
DEFAULT_PAGE_ID = "61594116376333"
DEFAULT_PAGE_NAME = "ละครสั้นคุณธรรม by ILAG Studio"

PERMALINK_POLL_INTERVAL_S = 120
PERMALINK_POLL_TIMEOUT_S = 30 * 60
DUPLICATE_PUBLISH_WINDOW_H = 24

# Positive evidence only — presence of neither is NOT evidence of failure.
FAILURE_MARKERS = ("ไม่สำเร็จ", "ไม่ได้บันทึกไว้อย่างถูกต้อง")

LOGIN_WALL_MARKERS = (
    "เข้าสู่ระบบ Facebook",
    "ลืมรหัสผ่านหรือไม่",
    "log into Facebook",
    "You must log in to continue",
)

COMMENT_IDENTITY_RE = re.compile(r"^แสดงความคิดเห็นใน(?:ชื่อ|นาม)\s*(.+)$")
TEST_MARKER_RE = re.compile(r"\[TEST-([0-9a-fA-F]{8})\]")

# BUG FOUND LIVE 2026-09-29 (EP4 first-comment run, CEO/CTO addendum to
# task-e4482d34): the comment posted fine as the Page, but Facebook's own
# innerText collapses a long comment to "<prefix>... ดูเพิ่มเติม" — so the
# post-submit body_contains_text check reported "comment text not found
# after submit" and the comment was never pinned. A re-run's idempotency
# check (also body_contains_text) has the same blind spot: it would not
# recognize the collapsed comment as already posted and could post it TWICE.
SEE_MORE_MARKER = "ดูเพิ่มเติม"

THAI_MONTHS = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}
_THAI_DATE_RE = re.compile(
    r"(\d{1,2})\s+(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)"
    r"\s+(\d{4}),\s*(\d{1,2}):(\d{2})"
)

OUTCOME_EXIT_CODES = {
    "verified": 0,
    "published_unverified": 6,
    "failed": 8,
}

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
    known to double blank lines in innerText (BROWSER_OPERATOR_Protocol_Playbook skill, task
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


def _collapse_tolerant_line_match(expected_line: str, body_line: str) -> bool:
    """Pure. True if body_line looks like Facebook's own collapsed rendering
    of expected_line: body_line carries the SEE_MORE_MARKER and the text
    before that marker is a left-truncation of expected_line (Facebook only
    ever truncates from the right, never rewrites or reorders text before the
    cut). Deliberately does NOT match on plain equality — a bare first-line
    match with no collapse marker is not evidence of anything (a caller's own
    exact/contiguous check already covers that case), and treating it as one
    was a real regression caught by test_body_contains_text_false_wrong_order."""
    if SEE_MORE_MARKER not in body_line:
        return False
    prefix = body_line.split(SEE_MORE_MARKER, 1)[0].rstrip(" .…")
    return bool(prefix) and expected_line.startswith(prefix)


def body_contains_text(body_text: str, expected_text: str) -> bool:
    """Pure. True iff every non-blank normalized line of expected_text appears
    as a contiguous, in-order run within body_text's own non-blank lines.
    Used to spot an already-posted comment (or, more loosely, any block of
    text) inside a page's full innerText without needing a DOM handle.

    FIX 2026-09-29 (see SEE_MORE_MARKER note above): if the strict multi-line
    match fails, falls back to matching just the expected text's first
    non-blank line against a body line that carries Facebook's own
    "ดูเพิ่มเติม" collapse marker — a collapsed excerpt is always a
    left-truncation of the real text, so that is sufficient evidence the
    comment is actually there, just rendered collapsed.
    """
    exp_lines = [ln for ln in normalize_caption(expected_text) if ln != ""]
    if not exp_lines:
        return False
    body_lines = [ln.strip() for ln in body_text.replace("\r\n", "\n").split("\n") if ln.strip() != ""]
    n = len(exp_lines)
    for i in range(len(body_lines) - n + 1):
        if body_lines[i:i + n] == exp_lines:
            return True
    # Collapsed rendering: Facebook cuts a long comment at whatever line crosses its length
    # limit, so the marker can sit on line 2 or 3 with the earlier lines intact. Match an
    # exact in-order run of expected lines that ends on a collapsed excerpt of the next one.
    # (2026-10-02, EP2 of film 5: the cut fell on line 2, the first-line-only check missed
    # the posted comment and a --comment-only rerun posted it a second time.)
    for i in range(len(body_lines)):
        for k, exp in enumerate(exp_lines):
            if i + k >= len(body_lines):
                break
            line = body_lines[i + k]
            if _collapse_tolerant_line_match(exp, line):
                return True
            if line != exp:
                break
    return False


def _meta_content(html_text: str, attr_name: str, attr_value: str) -> str | None:
    """Pure. Extracts a <meta> tag's content=, tolerating either attribute order."""
    esc = re.escape(attr_value)
    pat1 = re.compile(
        rf'<meta\s+[^>]*{attr_name}=["\']{esc}["\'][^>]*content=["\']([^"\']*)["\']', re.I
    )
    pat2 = re.compile(
        rf'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*{attr_name}=["\']{esc}["\']', re.I
    )
    for pat in (pat1, pat2):
        m = pat.search(html_text)
        if m:
            return html.unescape(m.group(1))
    return None


def extract_page_description(html_text: str) -> str:
    """Pure. Prefers `og:description`; falls back to the plain
    `<meta name="description">` tag, which is what a real facebookexternalhit
    fetch of a Reel permalink actually carries — measured 2026-09-26, see
    REPORT.md: film 2's permalink has no og:description at all, only
    name="description" with numeric-entity-encoded Thai.
    """
    return (
        _meta_content(html_text, "property", "og:description")
        or _meta_content(html_text, "name", "description")
        or ""
    )


def verify_permalink_content(html_text: str, expected_caption: str) -> bool:
    """Pure. True iff the expected caption's first line appears in the page's
    own description meta — the logged-out, signed-in-Chrome-independent check
    CTO-FEEDBACK.md requires. A dead/unavailable Reel carries no description
    meta at all (measured on film 1's dead reel 1104791208680559), so this
    reliably returns False for it.
    """
    lines = normalize_caption(expected_caption)
    if not lines:
        return False
    first_line = " ".join(lines[0].split())
    if not first_line:
        return False
    desc = " ".join(extract_page_description(html_text).split())
    return first_line in desc


def is_failure_evidence(row_text: str) -> bool:
    """Pure. True iff row_text carries positive evidence of a failed publish."""
    return any(marker in row_text for marker in FAILURE_MARKERS)


def classify_permalink_state(
    matched_url: str | None,
    row_text: str,
    seen_any_candidate: bool,
    timed_out: bool,
) -> tuple[str, str]:
    """Pure decision for one poll round (or the final round at timeout).
    Returns (outcome, evidence). outcome is one of:
      "verified"              matched_url passed the logged-out content check
      "failed"                positive evidence of failure (row text, or
                               nothing seen at all after timeout)
      "published_unverified"  timed out with something seen, never verified
      "pending"                keep polling (only valid while not timed_out)
    """
    if matched_url:
        return "verified", matched_url
    if is_failure_evidence(row_text):
        return "failed", row_text
    if timed_out:
        if not seen_any_candidate and not row_text:
            return "failed", "no Business Suite row and no public candidate after 30 min"
        return (
            "published_unverified",
            row_text or "a candidate video was seen but its content check never matched",
        )
    return "pending", ""


def outcome_to_exit_code(outcome: str) -> int:
    """Pure mapping from a resolve_permalink outcome to the process exit code."""
    return OUTCOME_EXIT_CODES[outcome]


def find_activity_row_for_caption(body_text: str, caption_text: str) -> str:
    """Pure. Returns a small window of the Business Suite activity feed's own
    innerText around the row whose text contains the caption's first line, or
    "" if no such row is present.
    """
    lines_expected = normalize_caption(caption_text)
    if not lines_expected:
        return ""
    first_line = lines_expected[0].strip()
    if not first_line:
        return ""
    lines = body_text.split("\n")
    for i, ln in enumerate(lines):
        if first_line in ln:
            return "\n".join(lines[i: i + 6])
    return ""


def parse_thai_datetime(text: str) -> datetime | None:
    """Pure. Parses the Business Suite activity feed's own timestamp format,
    e.g. '26 ก.ย. 2026, 12:07'. Returns None if no such timestamp is present.
    """
    m = _THAI_DATE_RE.search(text)
    if not m:
        return None
    day, mon_abbr, year, hh, mm = m.groups()
    month = THAI_MONTHS.get(mon_abbr)
    if month is None:
        return None
    try:
        return datetime(int(year), month, int(day), int(hh), int(mm))
    except ValueError:
        return None


def is_recent_duplicate(row_text: str, now: datetime, within_hours: int = DUPLICATE_PUBLISH_WINDOW_H) -> bool:
    """Pure. True iff row_text carries a Business Suite timestamp within the
    last `within_hours` hours of `now` (an hour of future skew is tolerated).
    """
    dt = parse_thai_datetime(row_text)
    if dt is None:
        return False
    delta = now - dt
    return timedelta(hours=-1) <= delta <= timedelta(hours=within_hours)


def parse_comment_identity(aria_label: str) -> str | None:
    """Pure. Extracts the identity name from the comment box's own aria-label,
    e.g. 'แสดงความคิดเห็นในชื่อ ละครสั้นคุณธรรม by ILAG Studio' -> the Page name.
    Returns None if the label doesn't match either observed phrasing.
    """
    m = COMMENT_IDENTITY_RE.match((aria_label or "").strip())
    return m.group(1).strip() if m else None


def is_duplicate_comment(expected_text: str, existing_texts: list[str]) -> bool:
    """Pure. True iff one of existing_texts already normalizes to expected_text
    — the idempotency check the brief requires before posting the first
    comment. FIX 2026-09-29 (see SEE_MORE_MARKER note above): also true if an
    existing text carries a line that is a collapsed ("...ดูเพิ่มเติม")
    rendering of expected_text's first line — same blind spot as
    body_contains_text, fixed the same way, so a re-run never double-posts a
    comment Facebook is currently displaying collapsed.
    """
    exp = normalize_caption(expected_text)
    if any(normalize_caption(t) == exp for t in existing_texts):
        return True
    exp_lines = [ln for ln in exp if ln != ""]
    if not exp_lines:
        return False
    first_line = exp_lines[0]
    for t in existing_texts:
        for ln in t.replace("\r\n", "\n").split("\n"):
            ln = ln.strip()
            if ln and _collapse_tolerant_line_match(first_line, ln):
                return True
    return False


def extract_test_marker(text: str) -> str | None:
    """Pure. Returns the 8 hex chars of a '[TEST-xxxxxxxx]' marker in text, or None."""
    m = TEST_MARKER_RE.search(text or "")
    return m.group(1) if m else None


def has_test_marker(text: str) -> bool:
    return extract_test_marker(text) is not None


def looks_like_login_wall(body_text: str) -> bool:
    """Pure, best-effort. True iff body_text carries a Facebook login-wall marker."""
    return any(marker in body_text for marker in LOGIN_WALL_MARKERS)


def fetch_permalink_html(url: str, timeout: int = 20) -> str:
    """Not pure — a real, logged-out network fetch (facebookexternalhit UA),
    independent of the signed-in Chrome. See module docstring."""
    result = subprocess.run(
        ["curl", "-sL", "-A", "facebookexternalhit/1.1", url],
        capture_output=True, timeout=timeout, text=True, check=False,
    )
    return result.stdout or ""


def resolve_permalink(
    fb: "FBReelBrowser",
    page_id: str,
    asset_id: str | None,
    caption_text: str,
    fetch_html=None,
    now=time.time,
    sleep=time.sleep,
    poll_interval_s: int = PERMALINK_POLL_INTERVAL_S,
    timeout_s: int = PERMALINK_POLL_TIMEOUT_S,
) -> dict:
    """Polls the Page's public /videos tab (+ Business Suite's activity feed,
    if asset_id is given) until a candidate's logged-out HTML verifies, a
    failure marker appears, or timeout_s elapses. Returns
    {"outcome": "verified"|"published_unverified"|"failed", "url": str|None,
     "evidence": str}.
    """
    fetch_html = fetch_html or fetch_permalink_html
    deadline = now() + timeout_s
    last_row = ""
    last_candidate = None
    while True:
        candidates = fb.list_public_video_candidates(page_id)
        matched_url = None
        for _vid, url in candidates:
            try:
                html_text = fetch_html(url)
            except Exception as e:  # noqa: BLE001
                fb.log(f"resolve_permalink: fetch failed for {url}: {e}")
                html_text = ""
            if verify_permalink_content(html_text, caption_text):
                matched_url = url
                break
            last_candidate = last_candidate or url
        if asset_id:
            activity_text = fb.read_activity_feed_text(asset_id)
            row = find_activity_row_for_caption(activity_text, caption_text)
            if row:
                last_row = row
        timed_out = now() >= deadline
        outcome, evidence = classify_permalink_state(
            matched_url, last_row, bool(candidates) or bool(last_row), timed_out
        )
        if outcome != "pending":
            return {"outcome": outcome, "url": matched_url or last_candidate, "evidence": evidence}
        sleep(poll_interval_s)


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
                # is_local=True: the CDP Chrome and this script run on the
                # same Mac. Without it Playwright assumes a remote browser
                # and refuses any file upload over 50MB (measured live,
                # task-c6bd5ba6: "Cannot transfer files larger than 50Mb to
                # a browser not co-located with the server") — the 845MB
                # banchi video needs this.
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

    def new_tab(self):
        if not self.browser.contexts:
            raise RuntimeError(
                f"no browser context — Chrome likely has 0 tabs; run: "
                f"curl -X PUT '{self.cdp_url}/json/new?about:blank'"
            )
        ctx = self.browser.contexts[0]
        self.page = ctx.new_page()
        return self.page

    def goto_composer(self):
        url = COMPOSER_URL_TMPL.format(asset_id=self.asset_id)
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(4000)
        self.page.evaluate(MUTE_JS)
        return self.page

    def open_composer(self):
        self.new_tab()
        return self.goto_composer()

    def open_permalink(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(3000)
        self.page.evaluate(MUTE_JS)
        return self.page

    def get_body_text(self) -> str:
        return self.page.evaluate("document.body.innerText")

    def check_login_wall(self) -> bool:
        return looks_like_login_wall(self.get_body_text())

    def list_public_video_candidates(self, page_id: str) -> list[tuple[str, str]]:
        """Read-only. Returns [(id, permalink_url), ...] for every distinct
        reel/video id linked from the Page's own public /videos tab, in
        document order (measured 2026-09-26: this tab lists both live posts
        and their `/reel/<id>/` anchors even for the admin's own logged-in
        session, so no separate public-vs-admin path is needed here).
        """
        self.page.goto(f"https://www.facebook.com/{page_id}/videos", wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(3000)
        self.page.evaluate(MUTE_JS)
        hrefs = self.page.evaluate(
            """
            () => [...document.querySelectorAll('a[href*="/videos/"], a[href*="/reel/"]')]
              .map(a => a.href)
            """
        )
        seen: dict[str, str] = {}
        for href in hrefs:
            m = re.search(r"/(?:videos|reel)/(\d+)", href)
            if m and m.group(1) not in seen:
                seen[m.group(1)] = f"https://www.facebook.com/{page_id}/videos/{m.group(1)}/"
        return list(seen.items())

    def read_activity_feed_text(self, asset_id: str) -> str:
        """Read-only. Business Suite's own activity/highlights feed for
        asset_id. The `content_management/reels?asset_id=` list route was
        measured 2026-09-26 to redirect to Home with nav_ref=typo_redirect,
        so this reads Home instead — it still carries each post's caption and
        a Thai timestamp.
        """
        self.page.goto(
            f"https://business.facebook.com/latest/?asset_id={asset_id}",
            wait_until="domcontentloaded", timeout=60000,
        )
        self.page.wait_for_timeout(4000)
        self.page.evaluate(MUTE_JS)
        return self.get_body_text()

    def confirm_page_name(self) -> str:
        """Best-effort read: returns the Page name text shown in the
        "โพสต์ไปยัง" picker, or "" if not found. The caller is what turns this
        into a hard gate (CTO-FEEDBACK-2.md) — this method itself never raises.

        BUG FOUND LIVE 2026-09-26 (task-cfdc75a8, first test-post run): the
        composer renders the "โพสต์ไปยัง" label TWICE (an outer section
        heading, then a second inner label right above the actual picker),
        each followed by a U+200B zero-width space text node before the real
        Page name. Filtering only the exact string 'โพสต์ไปยัง' left that
        zero-width space as the first surviving "line", so this returned
        '\\u200b' instead of the Page name and the hard gate refused a
        perfectly good composer. Fix: strip U+200B from every line before
        checking for emptiness, so the blank line is dropped along with both
        headings and the real name (measured: 'ละครสั้นคุณธรรม by ILAG Studio')
        is what's left.
        """
        try:
            txt = self.page.evaluate(
                """
                () => {
                  const heading = [...document.querySelectorAll('*')]
                    .find(e => e.children.length === 0 && e.textContent.trim() === 'โพสต์ไปยัง');
                  if (!heading) return '';
                  let node = heading.parentElement;
                  for (let i = 0; i < 6 && node; i++) {
                    const t = node.innerText || '';
                    const lines = t.split('\\n')
                      .map(s => s.split('\\u200b').join('').trim())
                      .filter(s => s !== '' && s !== 'โพสต์ไปยัง');
                    if (lines.length) return lines[0];
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

    def _hide_sticky_terms_notice(self) -> None:
        # Since 2026-10-02 Business Suite pins a "เรากำลังปรับปรุงข้อกำหนด…" terms notice
        # (position:sticky, no close button) over the top of the composer; the cover
        # buttons scroll under it and every click is intercepted. Hide it on screen only.
        self.page.evaluate("""() => {
            for (const d of document.querySelectorAll('div')) {
                if (!(d.innerText || '').startsWith('เรากำลังปรับปรุงข้อกำหนด')) continue;
                let el = d;
                while (el && getComputedStyle(el).position !== 'sticky') el = el.parentElement;
                if (el) el.style.display = 'none';
            }
        }""")

    def set_cover(self, cover_path: str) -> bool:
        page = self.page
        self._hide_sticky_terms_notice()
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
        # BUG FOUND LIVE 2026-09-25 (task-c6bd5ba6): a plain
        # "button/[role=button] with exact text แชร์ and width > 50" also
        # matches the wizard's own "แชร์" BREADCRUMB step-tab at the top of
        # the page (it renders as a real <button>, ~100px wide) — and that
        # element comes FIRST in document order, so `.find()` picked it
        # every time. Clicking it while already on that step is a no-op:
        # the real publish click never fired, twice, with no error and no
        # visible change, which is exactly the failure mode that makes this
        # worth a comment. Anchor on the "ย้อนกลับ" (Back) button instead —
        # it exists only once, in the footer, always as a sibling of the
        # real publish button — rather than trusting text+size alone.
        return self.page.evaluate_handle(
            """
            () => {
              const backBtns = [...document.querySelectorAll('button, [role="button"]')]
                .filter(e => e.textContent.trim() === 'ย้อนกลับ');
              for (const back of backBtns) {
                let container = back.parentElement;
                for (let i = 0; i < 4 && container; i++) {
                  const share = [...container.querySelectorAll('button, [role="button"]')]
                    .find(e => e.textContent.trim() === 'แชร์');
                  if (share) return share;
                  container = container.parentElement;
                }
              }
              return null;
            }
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

    # -- Part B: comment + pin -------------------------------------------------

    def expand_see_more(self):
        more = self.page.get_by_text("ดูเพิ่มเติม", exact=False)
        if more.count() > 0:
            try:
                more.first.click(timeout=3000)
                self.page.wait_for_timeout(1000)
            except Exception as e:  # noqa: BLE001
                self.log(f"expand_see_more: click failed: {e}")

    def find_comment_box(self):
        """Returns (locator, identity_name) for the first contenteditable
        comment box whose aria-label matches the "commenting as <name>"
        pattern, or (None, None) if none is found."""
        boxes = self.page.locator('[contenteditable="true"]')
        for i in range(boxes.count()):
            box = boxes.nth(i)
            identity = parse_comment_identity(box.get_attribute("aria-label") or "")
            if identity:
                return box, identity
        return None, None

    def post_comment(self, box, text: str) -> bool:
        box.click()
        self.page.keyboard.insert_text(text)
        self.page.wait_for_timeout(500)
        submit = self.page.locator('[aria-label="โพสต์ความคิดเห็น"]').first
        if submit.count() == 0:
            self.log("post_comment: submit button not found")
            return False
        try:
            submit.click(timeout=5000)
        except Exception as e:  # noqa: BLE001
            self.log(f"post_comment: submit click failed: {e}")
            return False
        self.page.wait_for_timeout(2500)
        return True

    def find_comment_block(self, expected_text: str):
        """Read-only. Locates a DOM node that holds the comment's first line
        and (per its own aria-label controls) looks like a whole comment row —
        returns an ElementHandle, or None. The caller checks whether the
        expected Page name is inside its own .innerText."""
        exp_lines = normalize_caption(expected_text)
        first_line = exp_lines[0] if exp_lines else ""
        if not first_line:
            return None
        handle = self.page.evaluate_handle(
            """
            (firstLine) => {
              const all = [...document.querySelectorAll('*')];
              const leaves = all.filter(e => e.children.length === 0 && e.textContent.includes(firstLine));
              for (const leaf of leaves) {
                let node = leaf;
                for (let i = 0; i < 6 && node; i++) {
                  if (node.querySelector && node.querySelector('[aria-label]')) {
                    return node;
                  }
                  node = node.parentElement;
                }
              }
              return null;
            }
            """,
            first_line,
        )
        return handle.as_element()

    def read_comment_container_text(self, container) -> str:
        return container.evaluate("el => el.innerText")

    def comment_is_pinned(self, container) -> bool:
        """Best-effort, not fully verified live — see REPORT.md."""
        try:
            text = container.evaluate(
                "el => (el.closest('[role=\"article\"]') || el.parentElement || el).innerText"
            )
        except Exception:  # noqa: BLE001
            text = ""
        return "ปักหมุดไว้" in text or "Pinned" in text

    def find_more_options_in(self, container):
        # BUG FOUND LIVE 2026-09-26 (task-cfdc75a8): on a comment posted by
        # the Page itself, the per-comment menu button is labelled
        # "แก้ไข หรือ ลบนี้" (Edit or delete this), not a generic
        # "...เพิ่มเติม" (more options) — that label is only used on OTHER
        # people's comments. Also search from the whole comment article
        # (container.closest('[role="article"]')), not just `container`
        # itself — find_comment_block can return an inner wrapper that does
        # not include this button, which sits near the author line.
        return container.evaluate_handle(
            """
            (node) => {
              const root = (node.closest && node.closest('[role="article"]')) || node;
              return [...root.querySelectorAll('[aria-label]')]
                .find(e => /เพิ่มเติม|แก้ไข.*ลบ/.test(e.getAttribute('aria-label') || ''));
            }
            """
        )

    def click_menu_item(self, text_variants: list[str]) -> bool:
        for text in text_variants:
            loc = self.page.get_by_text(text, exact=False)
            if loc.count() > 0:
                try:
                    loc.first.click(timeout=4000)
                    self.page.wait_for_timeout(1200)
                    return True
                except Exception as e:  # noqa: BLE001
                    self.log(f"click_menu_item({text!r}) failed: {e}")
        return False

    def confirm_dialog_if_present(self, confirm_texts: list[str]) -> None:
        self.page.wait_for_timeout(600)
        dialog = self.page.locator('[role="dialog"]')
        if dialog.count() == 0:
            return
        for text in confirm_texts:
            btn = dialog.last.get_by_text(text, exact=True)
            if btn.count() > 0:
                try:
                    btn.first.click(timeout=4000)
                    self.page.wait_for_timeout(1000)
                    return
                except Exception as e:  # noqa: BLE001
                    self.log(f"confirm_dialog_if_present({text!r}) failed: {e}")

    def pin_comment(self, container) -> bool:
        # LIVE FINDING 2026-09-26 (task-cfdc75a8, test post cycle): exhaustively
        # enumerated every clickable control in the comment's [role="article"]
        # (5 total: identity badge, this menu button, like, react, reply — no
        # 6th hidden control) and every menu item this button opens for a
        # Page-authored comment ("แก้ไข...", "ลบ" — exactly 2, no pin). Also
        # scanned every aria-label on the film 2 permalink page (0 comments
        # there) and on Business Suite's home surface: zero matches for
        # /ปักหมุด/ anywhere. Facebook's Reels comment UI does not currently
        # expose a pin control for the Page's own comment — this is a real
        # platform limitation, not a lookup bug. This method still tries the
        # real click path (in case Facebook adds it back / for a differently
        # shaped comment), and always closes the menu it opened so a failed
        # attempt never leaves stray UI state behind.
        more = self.find_more_options_in(container)
        el = more.as_element()
        if el is None:
            self.log("pin_comment: no 'more options' control found on the comment")
            return False
        try:
            # Facebook's sticky top banner can sit over the comment's menu button; a pin is
            # optional (see above), so a blocked click must not fail a run whose comment
            # already posted (2026-10-02: exit 14 after a successful post).
            el.click(timeout=5000)
        except Exception as e:  # noqa: BLE001
            self.log(f"pin_comment: menu button click failed ({str(e).splitlines()[0]}) — not pinned")
            return False
        self.page.wait_for_timeout(800)
        pinned = self.click_menu_item(["ปักหมุดความคิดเห็น", "ปักหมุด"])
        if not pinned:
            self.log("pin_comment: no pin item in this comment's menu (Edit/Delete only) — closing menu")
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(300)
        return pinned

    def delete_comment(self, container) -> bool:
        more = self.find_more_options_in(container)
        el = more.as_element()
        if el is None:
            self.log("delete_comment: no 'more options' control found on the comment")
            return False
        el.click()
        self.page.wait_for_timeout(800)
        return self.click_menu_item(["ลบ"])

    def delete_video_post(self) -> bool:
        """Deletes the currently-open post via its own 'more options' menu.
        Caller must have already re-read the live caption and confirmed the
        [TEST-xxxxxxxx] marker — see run_delete_test_post."""
        more = self.page.locator('[aria-label="ตัวเลือกเพิ่มเติมสำหรับวิดีโอ"]').first
        if more.count() == 0:
            self.log("delete_video_post: video-level more-options control not found")
            return False
        more.click()
        self.page.wait_for_timeout(1000)
        return self.click_menu_item(["ลบวิดีโอ", "ลบ"])


def do_first_comment(fb: "FBReelBrowser", permalink: str, comment_text: str, expected_page_name: str) -> dict:
    """Returns {"ok": bool, "pinned": bool, "reason": str, "skipped_duplicate": bool}."""
    fb.open_permalink(permalink)
    if fb.check_login_wall():
        return {"ok": False, "pinned": False, "reason": "login wall", "skipped_duplicate": False}
    fb.expand_see_more()

    body_before = fb.get_body_text()
    if body_contains_text(body_before, comment_text):
        container = fb.find_comment_block(comment_text)
        pinned = False
        if container is not None:
            pinned = fb.comment_is_pinned(container)
            if not pinned:
                pinned = fb.pin_comment(container)
        return {"ok": True, "pinned": pinned, "reason": "already posted (idempotent skip)", "skipped_duplicate": True}

    box, identity = fb.find_comment_box()
    if box is None or identity != expected_page_name:
        return {
            "ok": False, "pinned": False, "skipped_duplicate": False,
            "reason": f"identity gate failed: found {identity!r}, expected {expected_page_name!r}",
        }

    if not fb.post_comment(box, comment_text):
        return {"ok": False, "pinned": False, "reason": "submit failed", "skipped_duplicate": False}

    body_after = fb.get_body_text()
    if not body_contains_text(body_after, comment_text):
        return {"ok": False, "pinned": False, "reason": "comment text not found after submit", "skipped_duplicate": False}

    # BUG FOUND LIVE 2026-09-26 (task-cfdc75a8, test post cycle): the comment's
    # "more options" aria-label control (what find_comment_block anchors on)
    # is not yet in the DOM immediately after submit — a live recon of the
    # SAME comment ~1 minute later found it fine. A single lookup right after
    # posting is a race; retry for a few seconds before giving up.
    container = None
    for _attempt in range(4):
        container = fb.find_comment_block(comment_text)
        if container is not None:
            break
        fb.page.wait_for_timeout(1500)
    if container is None:
        return {
            "ok": False, "pinned": False, "skipped_duplicate": False,
            "reason": "posted, but could not locate the comment DOM node to verify author — needs manual check",
        }

    container_text = fb.read_comment_container_text(container)
    if expected_page_name not in container_text:
        fb.delete_comment(container)
        fb.confirm_dialog_if_present(["ลบ", "Delete"])
        return {
            "ok": False, "pinned": False, "skipped_duplicate": False,
            "reason": f"author was not the Page after submit (container: {container_text[:120]!r}) — deleted",
        }

    pinned = fb.pin_comment(container)
    return {"ok": True, "pinned": pinned, "reason": "posted", "skipped_duplicate": False}


def _print_permalink_result(result: dict) -> int:
    outcome = result["outcome"]
    if outcome == "verified":
        print(f"VERIFIED {result['url']}")
    elif outcome == "published_unverified":
        print("PUBLISHED-UNVERIFIED")
        print(result["evidence"])
    else:
        print(f"FAILED {result['evidence']}")
    return outcome_to_exit_code(outcome)


def _print_comment_result(permalink: str, result: dict) -> int:
    if result["ok"]:
        print(f"COMMENT {permalink} pinned={str(result['pinned']).lower()}")
        return 0
    print(f"REFUSED: {result['reason']}", file=sys.stderr)
    return 7


def run_resolve_permalink_cli(args: argparse.Namespace) -> int:
    caption_text = Path(args.caption_file).expanduser().read_text(encoding="utf-8")
    fb = FBReelBrowser(args.cdp, args.asset_id or "")
    try:
        fb.connect()
        fb.new_tab()
        result = resolve_permalink(fb, args.page_id, args.asset_id, caption_text, timeout_s=args.permalink_timeout)
        return _print_permalink_result(result)
    finally:
        fb.close()


def run_comment_only(args: argparse.Namespace) -> int:
    comment_text = Path(args.first_comment_file).expanduser().read_text(encoding="utf-8")
    fb = FBReelBrowser(args.cdp, args.asset_id or "")
    try:
        fb.connect()
        fb.new_tab()
        result = do_first_comment(fb, args.permalink, comment_text, args.page_name)
        return _print_comment_result(args.permalink, result)
    finally:
        fb.close()


def run_delete_test_post(args: argparse.Namespace) -> int:
    fb = FBReelBrowser(args.cdp, args.asset_id or "")
    try:
        fb.connect()
        fb.new_tab()
        fb.open_permalink(args.delete_test_post)
        if fb.check_login_wall():
            print("REFUSED: Chrome shows a Facebook login wall.", file=sys.stderr)
            return 13
        fb.expand_see_more()
        body = fb.get_body_text()
        marker = extract_test_marker(body)
        if marker is None:
            print(
                "REFUSED: no [TEST-xxxxxxxx] marker found in this post's LIVE caption — refusing to delete.",
                file=sys.stderr,
            )
            return 9
        print(f"delete-test-post: marker confirmed [TEST-{marker}] on {args.delete_test_post}")
        ok = fb.delete_video_post()
        fb.confirm_dialog_if_present(["ลบ", "Delete"])
        print(f"delete clicked: {ok}")
        return 0 if ok else 1
    finally:
        fb.close()


def run_publish(args: argparse.Namespace) -> int:
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
        fb.new_tab()

        if not args.allow_repost:
            activity_text = fb.read_activity_feed_text(args.asset_id)
            row = find_activity_row_for_caption(activity_text, caption_text)
            if row and is_recent_duplicate(row, datetime.now()):
                print(
                    "REFUSED: a post with this caption's first line was already published "
                    "within the last 24h:", file=sys.stderr,
                )
                print(row, file=sys.stderr)
                print("Use --allow-repost to publish anyway.", file=sys.stderr)
                return 11

        fb.goto_composer()
        if fb.check_login_wall():
            print("REFUSED: Chrome shows a Facebook login wall.", file=sys.stderr)
            return 13

        page_name = fb.confirm_page_name()
        print(f"composer opened; Page name shown: {page_name!r}")
        if page_name != args.page_name:
            print(
                f"REFUSED: composer identity gate — expected Page {args.page_name!r}, saw {page_name!r}",
                file=sys.stderr,
            )
            return 10

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
        if not cover_ok:
            print("REFUSED: cover image did not get set", file=sys.stderr)
            return 2

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

        result = resolve_permalink(fb, args.page_id, args.asset_id, caption_text, timeout_s=args.permalink_timeout)
        exit_code = _print_permalink_result(result)
        if result["outcome"] != "verified":
            if result["outcome"] == "published_unverified":
                print(
                    "Part B (comment) skipped: not VERIFIED yet. Rerun with --comment-only "
                    "once it resolves.", file=sys.stderr,
                )
            return exit_code

        if args.first_comment_file:
            comment_text = Path(args.first_comment_file).expanduser().read_text(encoding="utf-8")
            comment_result = do_first_comment(fb, result["url"], comment_text, args.page_name)
            return _print_comment_result(result["url"], comment_result)
        return exit_code
    finally:
        fb.close()


def run(args: argparse.Namespace) -> int:
    if args.delete_test_post:
        return run_delete_test_post(args)
    if args.comment_only:
        return run_comment_only(args)
    if args.resolve_permalink:
        return run_resolve_permalink_cli(args)
    return run_publish(args)


class _FBArgumentParser(argparse.ArgumentParser):
    """Enforces mode-dependent required arguments — required=True at the
    per-argument level cannot express "required only in default publish
    mode", since --resolve-permalink and --comment-only each use a different
    subset of the same flags (see docs/ops/briefs/fb-reel-permalink-first-comment.md)."""

    def parse_args(self, args=None, namespace=None):
        ns = super().parse_args(args, namespace)
        modes = [ns.resolve_permalink, ns.comment_only, bool(ns.delete_test_post)]
        if sum(1 for m in modes if m) > 1:
            self.error("--resolve-permalink, --comment-only and --delete-test-post are mutually exclusive")

        if ns.delete_test_post:
            pass
        elif ns.comment_only:
            missing = [n for n, v in (("--permalink", ns.permalink), ("--first-comment-file", ns.first_comment_file)) if not v]
            if missing:
                self.error(f"--comment-only requires: {', '.join(missing)}")
        elif ns.resolve_permalink:
            if not ns.caption_file:
                self.error("--resolve-permalink requires --caption-file")
        else:
            missing = [n for n, v in (
                ("--asset-id", ns.asset_id), ("--video", ns.video),
                ("--cover", ns.cover), ("--caption-file", ns.caption_file),
            ) if not v]
            if missing:
                self.error(f"the following arguments are required: {', '.join(missing)}")
        return ns


def build_parser() -> argparse.ArgumentParser:
    ap = _FBArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cdp", default="http://127.0.0.1:9230")
    ap.add_argument("--asset-id", help="Business Suite composer asset id (publish mode; also used for the duplicate/activity-feed checks)")
    ap.add_argument("--page-id", default=DEFAULT_PAGE_ID, help="public facebook.com page id, for permalink resolution")
    ap.add_argument("--page-name", default=DEFAULT_PAGE_NAME, help="expected Page identity, for the composer + comment gates")
    ap.add_argument("--video")
    ap.add_argument("--cover")
    ap.add_argument("--caption-file")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--screenshot", default=None, help="Path to save the final-step screenshot to.")
    ap.add_argument("--allow-repost", action="store_true", help="skip the 24h duplicate-publish guard")
    ap.add_argument("--resolve-permalink", action="store_true")
    ap.add_argument("--comment-only", action="store_true")
    ap.add_argument("--permalink", help="an already-published post's public URL")
    ap.add_argument("--first-comment-file", help="path to the comment text to post as the Page, then pin")
    ap.add_argument("--permalink-timeout", type=int, default=PERMALINK_POLL_TIMEOUT_S)
    ap.add_argument("--delete-test-post", default=None, help="permalink of a [TEST-xxxxxxxx]-marked post to delete")
    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    try:
        return run(args)
    except PublishRefused as e:
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
