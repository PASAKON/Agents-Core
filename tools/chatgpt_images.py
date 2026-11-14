#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The zero-model ChatGPT image runner — docs/ops/briefs/chatgpt-image-runner.md.

IRON-RULES §53: an operation repeated more than 3 times gets a runner, not an
operator. This replaces a human/model driving chatgpt.com by hand for every
ILAG trailer plate (see docs/reports/ilag-trailer-chatgpt-*-20260924/) with a
standalone script — zero token cost at runtime, same pattern as
tools/flow_shoot.py (Playwright over CDP, one adapter class, resumable
JSON ledger).

Drives the dedicated ChatGPT Chrome on winbox (CDP port 9224, profile
C:\\Users\\UsEr\\.chatgpt-automation\\chrome-profile, launched via
C:\\mooniex\\gpt-chrome.cmd) with the pwvenv Python (C:\\mooniex\\pwvenv —
never the Cookie Run venv). Selectors are the ones measured live in
docs/reports/ilag-trailer-chatgpt-characters-20260924/REPLAY.md.

    C:\\mooniex\\pwvenv\\Scripts\\python.exe tools\\chatgpt_images.py ^
        --brief docs\\ops\\briefs\\ilag-trailer-chatgpt-round3-village.md ^
        --out C:\\mooniex\\ilag-trailer\\plates [--dry-run] [--one <name>]

    ... or --json <path.json> instead of --brief, for a plain
    [{"name": ..., "prompt": ..., "attach": <optional path>}, ...] list.

Per image: navigate to https://chatgpt.com/ (always opens a fresh chat in
this account, no explicit "New chat" click needed — REPLAY.md), optionally
attach a reference image, paste the prompt via a synthetic paste event,
submit, poll for completion, then fetch the generated image's bytes
**straight from the page** (page.request against the <img>'s own src) —
never from the Downloads folder, which is shared with other workers and has
already handed one task someone else's file (task-f34224d9). Unlike the
`computer`-tool/MCP harness REPLAY.md was measured against, a same-origin
Playwright `page.request.get()` is not subject to that harness's
cookie/query-string URL redaction, so the signed oaiusercontent.com URL can
be read and fetched directly.

Markdown brief format (see docs/ops/briefs/ilag-trailer-chatgpt-round3-village.md):
a `## Image N: <name>` heading per image (the image's file name is the
heading's first whitespace-delimited token — the rest is free-text
description), an optional `ATTACH: <path>` line anywhere in that image's
block (not exercised by any brief seen so far — the JSON format is the
tested way to pass a reference), then the prompt verbatim between
`PROMPT START` / `PROMPT END` lines.

Follow-up in the SAME chat (CEO 2026-09-24: "รองรับการ Regenerate ซ้ำใน Chat
เดิม … สั่งให้เขา Edit ภาพตาม Prompt ได้โดยไม่ต้องแนบภาพ ถ้าใน Tab นั้นมีภาพอยู่
แล้ว"): an image with `continue: <earlier name>` (JSON key, or a `CONTINUE:
<name>` line in a markdown block) opens that image's chat from the ledger and
sends only the text — ChatGPT edits the picture already in the thread. The
previous image's src is excluded while waiting, so the old picture is never
taken for the new one, and the MD5 guard refuses an unchanged copy. Chains
work (b continues a, c continues b). Ad hoc, without a brief file:

    .venv/bin/python tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 \\
        --out <dir> --name logo-a2 --continue logo-a --prompt "make the red stroke thinner"

Send is confirmed by the user-turn count rising, not the URL changing — in an
existing chat the URL stays put, and a blind second click would land on the
same button after it has turned into Stop and cancel the generation.

Any of {logged out, usage limit, paywall, a turn that ends with no image —
refusal, clarifying question, or anything else this zero-model runner
cannot judge} **stops the whole run cleanly** (brief's own list) — the
ledger row for the image in progress records what was seen, the run
returns exit code 5 for usage limits, 6 for human checks, or 1 for other
failures, and re-running the same command later picks up from
the first name whose ledger status is not yet "done". A single image's own
technical hiccup (attach failed, paste didn't verify, timeout, a duplicate
MD5) fails only that image (ledger status "failed") and the run continues
to the next name — those are not money/policy hazards, just something to
retry once the cause is fixed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib import lease as leases

# Windows defaults stdout to cp1252, and this runner prints text that came
# from somewhere else — ChatGPT's own reply, a hazard excerpt off the live
# page. windows/pc_lease.py hit exactly this (a lease label with one
# non-ASCII char crashed its whole status check); reconfigure instead of
# risking a crash on the one line meant to explain what happened.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CDP_DEFAULT = "http://127.0.0.1:9224"
COMPLETION_TIMEOUT_S = 6 * 60
POLL_S = 5
FOREGROUND_S = 3
POST_SEND_GRACE_S = 45  # a reply counts as a refusal only after this long ...
REFUSAL_STABLE_POLLS = 6  # ... AND with the same non-empty text, no image, no stop button for 6 polls (30 s).
# 8 s with no stop button was read as a refusal while the image was still being made
# (logo-a-ledger, 2026-09-24): image generation does not always show a stop button.

# Verbatim from REPLAY.md / BROWSER_OPERATOR_Protocol_Playbook SKILL.md's HARD mute rule — a
# worker (and this runner) has no ears, and re-run after every navigation.
MUTE_JS = """
(() => {
  const mute = el => { el.muted = true; el.volume = 0; };
  const all = () => document.querySelectorAll('video,audio');
  all().forEach(mute);
  document.addEventListener('play', e => mute(e.target), true);
  new MutationObserver(() => all().forEach(mute))
    .observe(document.documentElement, { childList: true, subtree: true });
})()
""".strip()

COMPOSER_SEL = '#prompt-textarea, div[contenteditable="true"]'
# 2026-09-26: the Thai UI's send button lost both the id and the data-testid; what is left is
# aria-label "ส่ง" (the runner failed 4 of 4 with "send did not register" until this was added).
SEND_SEL = ('button#composer-submit-button, button[data-testid="send-button"], '
            'button[aria-label="ส่ง"], button[aria-label="Send prompt"]')
# 2026-11-11: the Thai Plus UI's attach button has no data-testid; its label is "เพิ่มไฟล์และอื่นๆ".
ATTACH_SEL = ('button[data-testid="composer-plus-btn"], '
              'button[aria-label="Attach files" i], button[aria-label="แนบไฟล์"], '
              'button[aria-label="เพิ่มไฟล์และอื่นๆ"], button[aria-label="Add files and more" i]')

PASTE_JS = """
(text) => {
  const el = document.querySelector('#prompt-textarea, div[contenteditable="true"]');
  if (!el) return false;
  el.focus();
  const dt = new DataTransfer();
  dt.setData('text/plain', text);
  el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  return true;
}
""".strip()

READ_PARAGRAPHS_JS = """
() => {
  const el = document.querySelector('#prompt-textarea, div[contenteditable="true"]');
  if (!el) return [];
  // innerText, not textContent: a pasted single newline lands as a <br> inside
  // the <p>, and textContent drops it, gluing the two lines together; every
  // multi-line prompt then "fails" the paste check by one char per line break
  // (task-964eddeb: 11 breaks, want-got = 11 on all 10 items).
  const ps = [...el.querySelectorAll('p')];
  return ps.length ? ps.map(p => p.innerText) : [el.innerText || ''];
}
""".strip()

POLL_JS = """
() => {
  const stopBtn = document.querySelector('button[data-testid="stop-button"], button[aria-label*="หยุด"], button[aria-label*="Stop" i]');
  // 2026-09-26 UI: no section[data-turn] and no [data-message-author-role] at all; turns are
  // only visible as the screen-reader headings "คุณพูดว่า:" / "ChatGPT พูดว่า:", and a picture
  // sits in [data-testid="generated-image-gallery"] with a blob: src.
  const bodyLines = (document.body.innerText || '').split('\\n').map(s => s.trim());
  const userHeads = bodyLines.filter(s => s === 'คุณพูดว่า:' || s === 'You said:').length;
  const botHeads = bodyLines.filter(s => s === 'ChatGPT พูดว่า:' || s === 'ChatGPT said:').length;
  const composer = document.querySelector('#prompt-textarea, div[contenteditable="true"]');
  // A turn is section[data-turn]; an IMAGE reply has no [data-message-author-role]
  // inside it at all (measured 2026-09-24 on a Thai-UI Plus account), so the
  // role selector alone reads a finished picture as "no reply".
  const turns = [...document.querySelectorAll('[data-turn="assistant"]')];
  const messages = turns.length ? turns : [...document.querySelectorAll('[data-message-author-role="assistant"]')];
  const userTurnEls = document.querySelectorAll('[data-turn="user"]');
  const lastMsg = messages.length ? messages[messages.length - 1] : null;
  const lastAssistant = lastMsg ? lastMsg.innerText : '';
  // Only the newest assistant turn: an attached reference image sits in the
  // user turn above it and must never be taken for the result.
  let imgs = lastMsg ? [...lastMsg.querySelectorAll('img[src*="oaiusercontent"], img[src*="estuary"], img[alt*="Generated" i], img[alt*="สร้าง" i]')] : [];
  if (!imgs.length) {
    const galleries = document.querySelectorAll('[data-testid="generated-image-gallery"]');
    const g = galleries.length ? galleries[galleries.length - 1] : null;
    imgs = g ? [...g.querySelectorAll('img')] : [];
  }
  const img = imgs.length ? imgs.reduce((a, b) => (b.naturalWidth > a.naturalWidth ? b : a)) : null;
  return {
    stillGenerating: !!stopBtn,
    assistantTurns: messages.length || botHeads,
    userTurns: userTurnEls.length || document.querySelectorAll('[data-message-author-role="user"]').length || userHeads,
    imgPresent: !!img,
    imgLoaded: img ? (img.complete && img.naturalWidth > 0) : false,
    naturalW: img ? img.naturalWidth : null,
    naturalH: img ? img.naturalHeight : null,
    imgSrc: img ? (img.currentSrc || img.src) : null,
    composerPresent: !!composer,
    bodySnippet: (document.body.innerText || '').slice(0, 4000),
    lastAssistantText: (lastAssistant || '').slice(0, 2000),
  };
}
""".strip()


# ── hazard classification — pure, no browser, this is what tests exercise ──

SIGNED_OUT_RE = re.compile(r"\blog\s?in\b", re.IGNORECASE)
USAGE_LIMIT_RE = re.compile(
    r"(you.?ve (reached|hit)|usage cap|message limit|rate limit|"
    r"try again (later|in)|too many requests|คุณใช้โควต้าสร้างรูปภาพหมดแล้ว|"
    r"ถึงลิมิตของแพ็กเกจ\s*Free|รอสร้างเพิ่มเวลา)", re.IGNORECASE)
HUMAN_CHECK_RE = re.compile(r"Just a moment|รอสักครู่|Verify you are human", re.IGNORECASE)
PAYWALL_RE = re.compile(
    r"(upgrade to (plus|go|pro|team)|get chatgpt plus|subscribe to continue|"
    r"unlock with plus|plus plan|pro plan)", re.IGNORECASE)


def classify_hazard(body_text: str, composer_present: bool) -> tuple[str, str] | None:
    """(kind, excerpt) for a logged-out/usage-limit/paywall page state, else None.

    Refusal is NOT covered here — it has no fixed wording; it is instead the
    terminal "generation ended with no image" state, handled by the caller
    with the assistant's own turn text (whatever it actually said)."""
    text = body_text or ""
    if HUMAN_CHECK_RE.search(text):
        return ("human_check", text[:1000])
    if not composer_present:
        m = SIGNED_OUT_RE.search(text)
        if m:
            return ("signed_out", text[max(0, m.start() - 40):m.end() + 40].strip())
    m = USAGE_LIMIT_RE.search(text)
    if m:
        reset = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)?", text, re.I)
        excerpt = text[max(0, m.start() - 40):m.end() + 1000].strip()
        return ("usage_limit", excerpt + (f" · reset {reset.group()}" if reset else ""))
    m = PAYWALL_RE.search(text)
    if m:
        return ("paywall", text[max(0, m.start() - 40):m.end() + 80].strip())
    return None


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ── brief parsing — pure, no browser ────────────────────────────────────────

_HEADING_RE = re.compile(r"^##\s*Image\s+\d+\s*:\s*(.+?)\s*$", re.MULTILINE)
_ATTACH_RE = re.compile(r"^ATTACH:\s*(.+?)\s*$", re.MULTILINE)
_PROMPT_RE = re.compile(r"PROMPT START\s*\n(.*?)\nPROMPT END", re.DOTALL)
_CONTINUE_RE = re.compile(r"^CONTINUE:\s*(\S+)\s*$", re.MULTILINE)


def _check_unique_names(images: list[dict]) -> None:
    seen: set[str] = set()
    for im in images:
        if im["name"] in seen:
            raise ValueError(f"duplicate image name in brief: {im['name']!r}")
        seen.add(im["name"])


def parse_markdown_brief(text: str) -> list[dict]:
    headings = list(_HEADING_RE.finditer(text))
    if not headings:
        raise ValueError("no '## Image N: <name>' headings found in brief")
    images = []
    for i, hm in enumerate(headings):
        name = hm.group(1).split()[0]
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block = text[hm.end():end]
        attach_m = _ATTACH_RE.search(block)
        continue_m = _CONTINUE_RE.search(block)
        prompt_m = _PROMPT_RE.search(block)
        if not prompt_m:
            raise ValueError(f"image {name!r}: no PROMPT START/END block found")
        images.append({
            "name": name,
            "prompt": prompt_m.group(1).strip(),
            "attach": attach_m.group(1) if attach_m else None,
            **({"continue": continue_m.group(1)} if continue_m else {}),
        })
    _check_unique_names(images)
    return images


def parse_json_brief(text: str) -> list[dict]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("JSON brief must be a list of {name, prompt, attach?}")
    images = []
    for i, item in enumerate(data):
        if "name" not in item or "prompt" not in item:
            raise ValueError(f"item {i}: needs both 'name' and 'prompt'")
        images.append({
            "name": item["name"],
            "prompt": item["prompt"],
            "attach": item.get("attach"),
            **({"continue": item["continue"]} if item.get("continue") else {}),
        })
    _check_unique_names(images)
    return images


def load_images(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return parse_json_brief(text)
    return parse_markdown_brief(text)


# ── ledger — plain JSON, atomic write (temp + rename, same as flow_ledger) ──

def load_ledger(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


_LEDGER_LOCK = threading.RLock()


def save_ledger(path: Path, rows: dict) -> None:
    with _LEDGER_LOCK:
        _save_ledger(path, rows)


def _save_ledger(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── MD5 no-duplicate guard ───────────────────────────────────────────────────

def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def existing_md5s(out_dir: Path) -> dict[str, Path]:
    """md5 -> path, for every *.png already in out_dir (fresh scan every
    call, not just what's in the ledger — another worker's file dropped
    into this same directory must dedupe too, task-f34224d9)."""
    result: dict[str, Path] = {}
    if out_dir.exists():
        for f in out_dir.glob("*.png"):
            try:
                result[md5_bytes(f.read_bytes())] = f
            except OSError:
                continue
    return result


# ── the only class that touches a browser ───────────────────────────────────

class ChatGPTBrowser:
    """Playwright-over-CDP adapter, same shape as tools/flow_shoot.py's
    FlowBrowser. Swap for a stub with the same method names to test
    orchestration without Chrome. Adapter regression tests use mocked pages;
    no tests connect to a live browser."""

    def __init__(self, cdp_url: str = CDP_DEFAULT):
        self.cdp_url = cdp_url
        self._pw = None
        self._browser = None
        self.page = None
        self._owned_pages = []
        self._missing_attach_since = None
        self._startup_reloaded = False

    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        page = ctx.new_page()
        self._owned_pages.append(page)
        try:
            page.bring_to_front()
        except Exception:
            pass
        self.page = page
        return page

    def new_tab(self):
        tab = ChatGPTBrowser(self.cdp_url)
        tab.page = self.page.context.new_page()
        self._owned_pages.append(tab.page)
        return tab

    def bring_to_front(self):
        self.page.bring_to_front()

    def attach_available(self):
        return bool(self.page.locator(ATTACH_SEL).count()
                    or self.page.locator('input[type="file"]').count())

    def refresh_plan_once(self):
        if not self._startup_reloaded:
            self.page.reload(wait_until="domcontentloaded", timeout=30_000)
            self._startup_reloaded = True
            self._missing_attach_since = None

    def hazard(self):
        hazard = classify_hazard(self.page.title() + "\n" + self.body_text(),
                                 self.composer_present())
        if hazard:
            return hazard
        if self.attach_available():
            self._missing_attach_since = None
        elif self._missing_attach_since is None:
            self._missing_attach_since = time.monotonic()
        elif time.monotonic() - self._missing_attach_since > 20:
            return ("human_check", "relay needed: attach button missing for >20 s")
        return None

    def delete_library_files(self) -> int:
        """Delete only this conversation's Library files; credentials stay in-page."""
        match = re.fullmatch(r"https://chatgpt\.com/c/([A-Za-z0-9-]+)(?:[?#].*)?", self.page.url)
        if not match:
            raise RuntimeError("chat cleanup failed: no current conversation id")
        try:
            deleted = self.page.evaluate("""async (id) => {
                try {
                    if (!id) return -1;
                    const session = await fetch('/api/auth/session');
                    if (!session.ok) return -1;
                    const {accessToken} = await session.json();
                    if (!accessToken) return -1;
                    const headers = {'Content-Type': 'application/json', Authorization: 'Bearer ' + accessToken};
                    const response = await fetch('/backend-api/files/library/nodes?entry_surface=library&include_hidden_files=false&include_files=true&include_saved_entities=true&defer_sharing_badges=true&include_sites=false&include_folder_counts=false&include_onedrive=false&hydrate_folder_thumbnails=false', {headers});
                    if (!response.ok) return -1;
                    const data = await response.json();
                    if (!Array.isArray(data.items)) return -1;
                    const files = data.items.filter(n => n.kind === 'file' && n.origination_thread_id === id)
                        .map(n => ({library_file_id: n.id, file_id: n.file_id,
                                    parent_directory_id: n.parent_directory_id, file_name: n.name}));
                    if (!files.length) return 0;
                    const deletion = await fetch('/backend-api/files/library/files/delete-batch', {
                        method: 'POST', headers, body: JSON.stringify({files})
                    });
                    return deletion.ok ? files.length : -1;
                } catch (_) { return -1; }
            }""", match.group(1))
        except Exception:
            raise RuntimeError("chat cleanup failed: library request failed") from None
        if type(deleted) is not int or deleted < 0:
            raise RuntimeError("chat cleanup failed: library rejected request")
        return deleted

    def delete_chat(self):
        # The header selector is no longer present. Use the authorized backend
        # fallback; keep the session token entirely inside the page context.
        match = re.fullmatch(r"https://chatgpt\.com/c/([A-Za-z0-9-]+)(?:[?#].*)?", self.page.url)
        if not match:
            raise RuntimeError("chat cleanup failed: no current conversation id")
        try:
            ok = self.page.evaluate("""async (id) => {
                try {
                    const session = await fetch('/api/auth/session');
                    if (!session.ok) return false;
                    const {accessToken} = await session.json();
                    if (!accessToken) return false;
                    const response = await fetch('/backend-api/conversation/' + encodeURIComponent(id), {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + accessToken},
                        body: JSON.stringify({is_visible: false})
                    });
                    return response.ok;
                } catch (_) { return false; }
            }""", match.group(1))
        except Exception:
            raise RuntimeError("chat cleanup failed: backend request failed") from None
        if ok is not True:
            raise RuntimeError("chat cleanup failed: backend rejected request")

    def close(self) -> None:
        for page in self._owned_pages:
            try:
                page.close()
            except Exception:
                pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def mute_all_media(self) -> None:
        self.page.evaluate(MUTE_JS)

    def open_chat(self, url: str) -> None:
        """Re-open an earlier chat so a text-only prompt edits the picture in it."""
        if self.page.url.split("?")[0] != url.split("?")[0]:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        self.refresh_plan_once()
        self.mute_all_media()
        # the thread paints after load — take the baseline only once its image is there
        for _ in range(40):
            if self.page.evaluate(POLL_JS)["imgLoaded"]:
                break
            self.page.wait_for_timeout(500)

    def baseline(self) -> dict:
        """What is on the page before sending: the newest image and the turn counts."""
        state = self.page.evaluate(POLL_JS)
        return {"src": state["imgSrc"], "assistant_turns": state["assistantTurns"],
                "user_turns": state["userTurns"]}

    def new_chat(self) -> None:
        self.page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=30_000)
        self.refresh_plan_once()
        self.mute_all_media()
        try:  # a paste into a composer that is not mounted yet lands nowhere, or half
            self.page.locator(COMPOSER_SEL).first.wait_for(state="visible", timeout=15_000)
        except Exception:
            pass  # process_one's composer_present() check reports it
        self.page.wait_for_timeout(1200)

    def clear_composer(self) -> None:
        self.page.evaluate("""() => {
          const el = document.querySelector('#prompt-textarea, div[contenteditable="true"]');
          if (!el) return;
          el.focus();
          document.execCommand('selectAll', false, null);
          document.execCommand('delete', false, null);
        }""")
        self.page.wait_for_timeout(300)

    def composer_present(self) -> bool:
        return self.page.locator(COMPOSER_SEL).count() > 0

    def body_text(self) -> str:
        return self.page.evaluate("() => document.body.innerText || ''")

    def attach_reference(self, path: Path) -> None:
        """UNVERIFIED against the live DOM — no logged-in session was
        available while this was written (2026-09-24). Tries the file input
        directly first (works even if it is hidden behind a '+' menu, per
        ordinary Playwright practice); falls back to opening the attach
        button if no input is found yet."""
        page = self.page
        file_input = page.locator('input[type="file"]')
        if file_input.count() == 0:
            page.locator(
                'button[aria-label="Attach files" i], button[aria-label="แนบไฟล์"], '
                'button[data-testid="composer-plus-btn"]'
            ).first.click(timeout=5000)
            page.wait_for_timeout(300)
            file_input = page.locator('input[type="file"]')
        if file_input.count() == 0:
            raise RuntimeError("no <input type=file> found to attach the reference image")
        file_input.first.set_input_files(str(path))
        page.wait_for_timeout(1500)

    def paste_prompt(self, text: str) -> None:
        # The first paste of a run landed NOTHING twice (logo-b, 2026-09-24: "got 0
        # chars") while later ones worked: the editor is painted before it listens.
        # Retry only when the box is still empty — a partial paste is left for
        # process_one to clear and redo, so text never doubles here.
        for _ in range(3):
            ok = self.page.evaluate(PASTE_JS, text)
            if not ok:
                raise RuntimeError("paste failed: composer not found")
            self.page.wait_for_timeout(400)
            if normalize_ws(self.read_composer_text()):
                return
            self.page.wait_for_timeout(1500)
            try:
                self.page.locator(COMPOSER_SEL).first.click(timeout=3000)
            except Exception:
                pass
        self.page.keyboard.insert_text(text)

    def read_composer_text(self) -> str:
        paragraphs = self.page.evaluate(READ_PARAGRAPHS_JS)
        return "\n\n".join(paragraphs)

    def send(self) -> None:
        page = self.page
        before_url = page.url
        before_turns = page.evaluate(POLL_JS)["userTurns"]
        try:
            page.locator(SEND_SEL).first.click(timeout=5000)
        except Exception:
            pass
        if self._wait_sent(before_url, before_turns, timeout_s=4):
            return
        # REPLAY.md: a ref/pixel click can silently not register; a direct JS
        # click on the real DOM element is what worked there. Never when a stop
        # button is showing: the send button has become Stop, and the first
        # click DID send — in an existing chat the URL never changes.
        if page.locator('button[data-testid="stop-button"]').count() == 0:
            page.evaluate(
                "() => { const b = document.querySelector("
                f"'{SEND_SEL}'"
                "); if (b) b.click(); }")
        if not self._wait_sent(before_url, before_turns, timeout_s=6):
            raise RuntimeError("send did not register: no new user turn, no URL change")

    def _wait_sent(self, before_url: str, before_turns: int, timeout_s: float) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            state = self.page.evaluate(POLL_JS)
            if (self.page.url != before_url or state["userTurns"] > before_turns
                    or state["stillGenerating"]):
                return True
            time.sleep(0.3)
        return False

    def wait_for_result(self, timeout_s: int = COMPLETION_TIMEOUT_S,
                        exclude_src: str | None = None, min_assistant_turns: int = 0) -> dict:
        work = self.poll_result(timeout_s, exclude_src, min_assistant_turns)
        while True:
            try:
                next(work)
            except StopIteration as done:
                return done.value
            time.sleep(POLL_S)

    def poll_result(self, timeout_s=COMPLETION_TIMEOUT_S,
                    exclude_src=None, min_assistant_turns=0, submitted_at=None):
        """exclude_src / min_assistant_turns: in a continued chat the previous
        reply, with its finished image, is the newest turn until the new one
        appears — it must never be taken for the result."""
        start = time.monotonic() if submitted_at is None else submitted_at
        last_src, stable = None, 0
        last_text, text_stable = None, 0
        final_scans = 0
        while True:
            self.bring_to_front()
            self.page.wait_for_timeout(FOREGROUND_S * 1000)
            hazard = self.hazard()
            if hazard:
                return {"status": "hazard", "hazard_kind": hazard[0], "text": hazard[1]}
            expired = time.monotonic() - start >= timeout_s
            # Always scan the full rendered DOM after foregrounding, even at
            # the deadline. Two final scans retain the stable-image safeguard.
            if expired:
                final_scans += 1
            state = self.page.evaluate(POLL_JS)
            if state["assistantTurns"] < min_assistant_turns or (
                    exclude_src and state["imgSrc"] == exclude_src):
                if final_scans >= 2:
                    return {"status": "timeout"}
                yield None
                continue
            hazard = classify_hazard(state["bodySnippet"], state["composerPresent"])
            if hazard:
                kind, excerpt = hazard
                return {"status": "hazard", "hazard_kind": kind, "text": excerpt}
            # ChatGPT paints a blurred preview that sharpens in place, so a
            # loaded <img> is not a finished one: wait until generation has
            # stopped and the same src has held for two polls in a row.
            if state["imgLoaded"] and not state["stillGenerating"]:
                stable = stable + 1 if state["imgSrc"] == last_src else 1
                last_src = state["imgSrc"]
                if stable >= 2:
                    return {"status": "done", "src": state["imgSrc"],
                            "width": state["naturalW"], "height": state["naturalH"]}
            else:
                last_src, stable = None, 0
            elapsed = time.monotonic() - start
            text = (state["lastAssistantText"] or "").strip()
            if not state["stillGenerating"] and not state["imgPresent"] and text:
                text_stable = text_stable + 1 if text == last_text else 1
                last_text = text
                if text_stable >= REFUSAL_STABLE_POLLS and elapsed > POST_SEND_GRACE_S:
                    return {"status": "refusal", "text": text}
            else:
                last_text, text_stable = None, 0
            if final_scans >= 2:
                return {"status": "timeout"}
            yield None

    def fetch_image_bytes(self, url: str) -> bytes:
        if url.startswith("blob:"):
            # a blob: URL only exists inside the page; read it there (2026-09-26 UI)
            import base64
            b64 = self.page.evaluate(
                "async (u) => { const r = await fetch(u); const b = new Uint8Array(await r.arrayBuffer());"
                " let s = ''; for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));"
                " return btoa(s); }", url)
            return base64.b64decode(b64)
        resp = self.page.request.get(url)
        if resp.status != 200:
            raise RuntimeError(f"image fetch failed: HTTP {resp.status} for {url}")
        return resp.body()


# ── orchestration ────────────────────────────────────────────────────────────

def process_one(browser: ChatGPTBrowser, image: dict, out_dir: Path,
                 ledger_path: Path, ledger: dict, timeout_s: int) -> dict:
    work = process_steps(browser, image, out_dir, ledger_path, ledger, timeout_s)
    while True:
        try:
            next(work)
        except StopIteration as done:
            return done.value
        time.sleep(POLL_S)


def process_steps(browser, image, out_dir, ledger_path, ledger, timeout_s):
    name = image["name"]
    out_path = out_dir / f"{name}.png"

    def _fail(status: str, note: str, **extra) -> dict:
        row = {"name": name, "status": status, "note": note, "time": now_iso(), **extra}
        ledger[name] = row
        save_ledger(ledger_path, ledger)
        return row

    if out_path.exists():
        return _fail("failed", f"{out_path} already exists — refusing to overwrite")

    parent = image.get("continue")
    resume_url = image.get("chat_url")
    if parent:
        prow = ledger.get(parent) or {}
        if prow.get("status") != "done" or "/c/" not in (prow.get("chat_url") or ""):
            return _fail("failed", f"cannot continue {parent!r}: no finished ledger row with a chat_url")
        resume_url = prow["chat_url"]

    _fail("running", "preparing", **({"chat_url": resume_url} if resume_url else {}))
    if resume_url:
        browser.open_chat(resume_url)
        before = browser.baseline()
        wait_kw = {"exclude_src": before["src"], "min_assistant_turns": before["assistant_turns"] + 1}
    else:
        browser.new_chat()
        wait_kw = {}

    if hasattr(browser, "hazard"):
        ready_start = time.monotonic()
        while True:
            hazard = browser.hazard()
            if hazard:
                return _fail("stopped", hazard[1], hazard_kind=hazard[0])
            if browser.composer_present() and browser.attach_available():
                break
            if time.monotonic() - ready_start > 20:
                return _fail("stopped", "relay needed: composer/attach unavailable for >20 s",
                             hazard_kind="human_check")
            yield None

    if image.get("attach"):
        try:
            browser.attach_reference(Path(image["attach"]))
        except Exception as e:
            return _fail("failed", f"attach failed: {e!r}")

    if not browser.composer_present():
        body = browser.body_text()
        hazard = classify_hazard(body, False) or ("signed_out", "composer not present")
        return _fail("stopped", hazard[1], hazard_kind=hazard[0])

    try:
        browser.paste_prompt(image["prompt"])
        got = browser.read_composer_text()
        if normalize_ws(got) != normalize_ws(image["prompt"]):
            # clear first: a second paste APPENDS, so the retry could never match
            # (logo-b-cracked-gold, 2026-09-24)
            browser.clear_composer()
            browser.paste_prompt(image["prompt"])
            got = browser.read_composer_text()
        if normalize_ws(got) != normalize_ws(image["prompt"]):
            raise RuntimeError(
                f"composer text does not match the prompt after 2 paste attempts "
                f"(got {len(normalize_ws(got))} chars, want {len(normalize_ws(image['prompt']))}: "
                f"{normalize_ws(got)[:60]!r})")
        submitted = time.monotonic()
        browser.send()
    except Exception as e:
        return _fail("failed", f"send failed: {e!r}")

    _fail("running", "submitted", chat_url=browser.page.url)
    # Suspend immediately after submission; the scheduler fills other tabs first.
    yield None
    if hasattr(browser, "poll_result"):
        result = yield from browser.poll_result(
            timeout_s=timeout_s, submitted_at=submitted, **wait_kw)
    else:
        result = browser.wait_for_result(timeout_s=timeout_s, **wait_kw)
    # read the URL only now: a new chat gets its /c/<id> address a moment after
    # the user turn appears, and a follow-up needs that address, not chatgpt.com/
    chat_url = browser.page.url

    if result["status"] == "hazard":
        return _fail("stopped", result["text"], hazard_kind=result["hazard_kind"], chat_url=chat_url)
    if result["status"] == "refusal":
        return _fail("stopped", result["text"], hazard_kind="refusal", chat_url=chat_url)
    if result["status"] == "timeout":
        return _fail("failed", f"timed out after {timeout_s}s waiting for the image", chat_url=chat_url)

    try:
        data = browser.fetch_image_bytes(result["src"])
    except Exception as e:
        return _fail("failed", f"fetch failed: {e!r}", chat_url=chat_url)

    md5 = md5_bytes(data)
    dupes = existing_md5s(out_dir)
    if md5 in dupes:
        return _fail("failed",
                      f"MD5 {md5} matches existing file {dupes[md5].name} — refusing duplicate",
                      chat_url=chat_url, md5=md5)

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".png.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, out_path)

    row = {
        "name": name, "status": "done", "chat_url": chat_url, "md5": md5,
        "bytes": len(data), "width": result.get("width"), "height": result.get("height"),
        "time": now_iso(), "note": "", "deleted_from_chatgpt": 0,
    }
    if parent or resume_url:
        row["continued_from"] = parent or resume_url
    ledger[name] = row
    save_ledger(ledger_path, ledger)
    return row


def recover_one(browser: ChatGPTBrowser, name: str, out_dir: Path,
                ledger_path: Path, ledger: dict) -> dict:
    """Take a picture that finished AFTER the runner gave up (timeout, early
    refusal): reopen the ledger row's chat and save its newest image. Sends nothing."""
    row = ledger.get(name) or {}
    url = row.get("chat_url") or ""
    out_path = out_dir / f"{name}.png"
    if "/c/" not in url:
        return {"name": name, "status": "failed", "note": "no chat_url in the ledger to recover from"}
    if row.get("status") == "done" or out_path.exists():
        return {"name": name, "status": "failed", "note": "already done / file exists — nothing to recover"}
    browser.open_chat(url)
    src = browser.baseline()["src"]
    if not src:
        return {"name": name, "status": "failed", "note": "no finished image in that chat"}
    data = browser.fetch_image_bytes(src)
    md5 = md5_bytes(data)
    dupes = existing_md5s(out_dir)
    if md5 in dupes:
        return {"name": name, "status": "failed", "note": f"MD5 matches {dupes[md5].name}"}
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    new = {**row, "name": name, "status": "done", "md5": md5, "bytes": len(data),
           "time": now_iso(), "note": f"recovered after '{row.get('status')}': {row.get('note', '')}"[:300]}
    ledger[name] = new
    save_ledger(ledger_path, ledger)
    return new


def run_scheduler(tabs, todo, out_dir, ledger_path, ledger, timeout_s, keep_in_chatgpt=False, guard=None):
    """Cooperative round-robin: Playwright stays on its owning thread."""
    pending = list(todo)
    busy = {}
    owners = {}
    completed = []

    def record_failure(image, note, status="failed", **extra):
        row = {"name": image["name"], "status": status, "note": note,
               "time": now_iso(), **extra}
        ledger[image["name"]] = row
        save_ledger(ledger_path, ledger)
        return row

    def advance(tab):
        if guard:
            guard.assert_valid()
        image, work = busy[tab]
        try:
            tab.bring_to_front()
            next(work)
            return None
        except StopIteration as done:
            row = done.value
        except Exception as exc:
            hazard = None
            try:
                if hasattr(tab, "hazard"):
                    hazard = tab.hazard()
            except Exception:
                pass
            if hazard:
                row = record_failure(image, hazard[1], "stopped", hazard_kind=hazard[0])
            else:
                row = record_failure(image, str(exc))
        del busy[tab]
        completed.append(row)
        print(f"{image['name']}: {row['status']} {row.get('note', '')}")
        return row

    def stop(row):
        kind = row.get("hazard_kind")
        if kind == "human_check":
            print("relay needed")
        for tab, (image, work) in list(busy.items()):
            completed.append(record_failure(image, "batch stopped: " + row.get("note", ""),
                                            "stopped", hazard_kind=kind, chat_url=tab.page.url))
            work.close()
        busy.clear()
        return {"usage_limit": 5, "human_check": 6}.get(kind, 1)

    while pending or busy:
        # A tab stays reserved while any pending descendant needs its chat.
        for tab in tabs:
            if tab in busy:
                continue
            chosen = None
            for image in pending:
                parent = image.get("continue")
                if parent:
                    if ledger.get(parent, {}).get("status") != "done":
                        continue
                    owner = owners.get(parent)
                    if owner is None:
                        url = ledger.get(parent, {}).get("chat_url")
                        owner = next((owners[n] for n in owners
                                      if url and ledger.get(n, {}).get("chat_url") == url), None)
                    if owner is not None and owner is not tab:
                        continue
                reserved = any(owners.get(im.get("continue")) is tab for im in pending)
                if reserved and owners.get(parent) is not tab:
                    continue
                chosen = image
                break
            if chosen is None:
                continue
            pending.remove(chosen)
            owners[chosen["name"]] = tab
            busy[tab] = (chosen, process_steps(tab, chosen, out_dir, ledger_path, ledger, timeout_s))
            row = advance(tab)
            if row and row["status"] == "stopped":
                return stop(row), completed

        for tab in list(busy):
            row = advance(tab)
            if row and row["status"] == "stopped":
                return stop(row), completed
            if row and row["status"] == "done":
                if not keep_in_chatgpt and not any(owners.get(im.get("continue")) is tab for im in pending):
                    try:
                        row["deleted_from_chatgpt"] = tab.delete_library_files()
                        tab.delete_chat()
                    except Exception as exc:
                        print(f"chat cleanup failed: {exc}")
                    save_ledger(ledger_path, ledger)
        if busy:
            time.sleep(POLL_S)
        elif pending:
            # Continue dependencies may be forward references; only fail when
            # no remaining item can make progress (failed/missing parent/cycle).
            if not any(not im.get("continue") or ledger.get(im["continue"], {}).get("status") == "done"
                       for im in pending):
                for image in pending:
                    completed.append(record_failure(image, "cannot continue: parent failed, missing, or cyclic"))
                pending.clear()
    return (1 if any(row["status"] != "done" for row in completed) else 0), completed


def cooling_deadline(text: str, now=None):
    """Interpret provider reset text in the browser host's local timezone.

    Explicit ISO offsets are preserved; unrecognised/past times use +2h.
    """
    now = now or datetime.now().astimezone()
    iso = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})", text)
    if iso:
        try:
            value = datetime.fromisoformat(iso.group().replace("Z", "+00:00"))
            if value > now:
                return value.timestamp()
        except ValueError:
            pass
    relative = re.search(r"(?:in|after)\s+(\d+)\s*(hours?|hrs?|minutes?|mins?)", text, re.I)
    if relative:
        seconds = int(relative[1]) * (3600 if relative[2].lower().startswith("h") else 60)
        if seconds:
            return now.timestamp() + seconds
    clock = re.search(r"(?<![\dT])\b(\d{1,2}):(\d{2})\s*(AM|PM)?", text, re.I)
    if clock and not iso:
        hour, minute = int(clock[1]), int(clock[2])
        if clock[3] and 1 <= hour <= 12:
            hour = hour % 12 + (12 if clock[3].upper() == "PM" else 0)
        if hour < 24 and minute < 60:
            value = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if value <= now or "tomorrow" in text.lower():
                value += timedelta(days=1)
            return value.timestamp()
    return now.timestamp() + 7200


def lease_resource(args):
    endpoint = urlparse(args.cdp_url)
    host = getattr(args, "lease_host", None) or endpoint.hostname
    if host in {"localhost", "127.0.0.1", "::1"}:
        host = os.environ.get("ORG_HOST")
    if not host or not re.fullmatch(r"[a-z0-9]{1,24}", host):
        raise ValueError("pass --lease-host with the canonical host for this CDP endpoint")
    port = endpoint.port or (443 if endpoint.scheme == "https" else 80)
    return f"chatgpt:{host}:{port}"


def cmd_run(args) -> int:
    if not os.environ.get("LEASE_DB_URL"):
        print("lease: off (LEASE_DB_URL unset)")
        return _cmd_run(args)
    if getattr(args, "dry_run", False):
        return _cmd_run(args)
    try:
        name = lease_resource(args)
        # Rate grants do not serialize active holders. Reserve the home mutex
        # atomically too, without nested acquisition or partially spent credits.
        with leases.lease_many([name, name.replace("chatgpt:", "home:", 1)],
                               purpose="ChatGPT image run", wait_s=getattr(args, "wait_s", 600)) as guard:
            return _cmd_run(args, guard=guard, resource=name)
    except (leases.LeaseError, ValueError) as exc:
        print(f"lease: {exc}", file=sys.stderr)
        return 1


def _cmd_run(args, guard=None, resource=None) -> int:
    started = time.monotonic()
    if getattr(args, "recover", None):
        out_dir = Path(args.out)
        ledger_path = out_dir / "ledger.json"
        ledger = load_ledger(ledger_path)
        browser = ChatGPTBrowser(cdp_url=args.cdp_url)
        try:
            if guard:
                guard.assert_valid()
            browser.attach()
            row = recover_one(browser, args.recover, out_dir, ledger_path, ledger)
        finally:
            browser.close()
        print(f"{args.recover}: {row['status']} {row.get('note', '')}")
        return 0 if row["status"] == "done" else 1

    if getattr(args, "prompt", None):
        if not getattr(args, "name", None):
            print("--prompt needs --name (the output file is <name>.png)")
            return 2
        src = "the command line"
        images = [{"name": args.name, "prompt": args.prompt, "attach": args.attach,
                   "continue": args.continue_from, "chat_url": args.chat_url}]
    else:
        src = Path(args.brief) if args.brief else Path(args.json)
        images = load_images(src)

    if args.one:
        images = [im for im in images if im["name"] == args.one]
        if not images:
            print(f"no image named {args.one!r} in {src}")
            return 2

    out_dir = Path(args.out)
    ledger_path = out_dir / "ledger.json"
    ledger = load_ledger(ledger_path)

    if args.dry_run:
        print(f"dry-run: {len(images)} image(s) from {src}")
        for im in images:
            first_line = im["prompt"].splitlines()[0][:100]
            attach = f" attach={im['attach']}" if im.get("attach") else ""
            attach += f" continue={im['continue']}" if im.get("continue") else ""
            done = ledger.get(im["name"], {}).get("status") == "done"
            tag = " [already done]" if done else ""
            print(f"  - {im['name']}{attach}: {first_line}...{tag}")
        return 0

    todo = [im for im in images if ledger.get(im["name"], {}).get("status") != "done"]
    if not todo:
        print("nothing to do — every requested image already has a 'done' ledger row")
        print(f"done 0 · failed 0 · skipped {len(images)} · elapsed 0s")
        return 0

    browser = ChatGPTBrowser(cdp_url=args.cdp_url)
    completed = []
    code = 1
    try:
        if guard:
            guard.assert_valid()
        browser.attach()
        tabs = [browser] + [browser.new_tab() for _ in range(getattr(args, "parallel", 1) - 1)]
        options = {"guard": guard} if guard else {}
        code, completed = run_scheduler(tabs, todo, out_dir, ledger_path, ledger, args.timeout_s,
                                        keep_in_chatgpt=getattr(args, "keep_in_chatgpt", False), **options)
        if code == 5 and guard:
            text = " ".join(row.get("note", "") for row in completed if row.get("hazard_kind") == "usage_limit")
            guard.service.report_cooling(guard.request_id, guard.actor, guard.tokens,
                                         resource, cooling_deadline(text))
    except Exception as exc:
        print(f"runner failed: {exc}")
    finally:
        browser.close()
    done = sum(row["status"] == "done" for row in completed)
    failed = len(completed) - done
    skipped = len(images) - len(completed)
    print(f"done {done} · failed {failed} · skipped {skipped} · elapsed {time.monotonic() - started:.0f}s")
    return code


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--brief", help="brief markdown with PROMPT START/END blocks")
    src.add_argument("--json", help="JSON file: a list of {name, prompt, attach?, continue?}")
    src.add_argument("--prompt", help="one image straight from the command line (needs --name)")
    src.add_argument("--recover", metavar="NAME",
                     help="save the finished image from NAME's chat (the runner gave up too early); sends nothing")
    ap.add_argument("--name", help="with --prompt: output name")
    ap.add_argument("--continue", dest="continue_from",
                     help="with --prompt: edit in the chat of this earlier ledger name, text only")
    ap.add_argument("--chat-url", help="with --prompt: edit in this chat URL, text only")
    ap.add_argument("--attach", help="with --prompt: reference image to attach")
    ap.add_argument("--out", required=True,
                     help="output dir for <name>.png and ledger.json")
    ap.add_argument("--one", help="only process this one image name")
    ap.add_argument("--dry-run", action="store_true",
                     help="parse the brief and print what would run; no browser touched")
    ap.add_argument("--keep-in-chatgpt", action="store_true",
                    help="keep Library files and chats after saving images locally")
    ap.add_argument("--cdp-url", default=CDP_DEFAULT,
                     help=f"default {CDP_DEFAULT} — the dedicated ChatGPT Chrome")
    ap.add_argument("--lease-host", help="canonical host (required for loopback CDP unless ORG_HOST is set)")
    ap.add_argument("--wait-s", type=float, default=600, help="lease wait budget in seconds (default 600)")
    ap.add_argument("--timeout-s", type=int, default=COMPLETION_TIMEOUT_S,
                     help="per-image generation timeout in seconds (default 360)")
    ap.add_argument("--parallel", type=int, choices=range(1, 5), default=1,
                    help="number of in-flight chats in the same browser context (1..4)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
