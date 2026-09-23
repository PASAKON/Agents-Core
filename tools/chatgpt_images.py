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

Any of {logged out, usage limit, paywall, a turn that ends with no image —
refusal, clarifying question, or anything else this zero-model runner
cannot judge} **stops the whole run cleanly** (brief's own list) — the
ledger row for the image in progress records what was seen, the run
returns exit code 1, and re-running the same command later picks up from
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
from datetime import datetime, timezone
from pathlib import Path

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
POST_SEND_GRACE_S = 8  # give ChatGPT time to start streaming before "no image, no stop button" counts as a refusal

# Verbatim from REPLAY.md / browser-operator SKILL.md's HARD mute rule — a
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
SEND_SEL = 'button#composer-submit-button, button[data-testid="send-button"]'

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
  const ps = [...el.querySelectorAll('p')];
  return ps.length ? ps.map(p => p.textContent) : [el.textContent || ''];
}
""".strip()

POLL_JS = """
() => {
  const stopBtn = document.querySelector('button[data-testid="stop-button"]');
  const composer = document.querySelector('#prompt-textarea, div[contenteditable="true"]');
  const messages = [...document.querySelectorAll('[data-message-author-role="assistant"]')];
  const lastMsg = messages.length ? messages[messages.length - 1] : null;
  const lastAssistant = lastMsg ? lastMsg.innerText : '';
  // Only the newest assistant turn: an attached reference image sits in the
  // user turn above it and must never be taken for the result.
  const imgs = lastMsg ? [...lastMsg.querySelectorAll('img[src*="oaiusercontent"], img[alt*="Generated" i], img[alt*="สร้าง" i]')] : [];
  const img = imgs.length ? imgs.reduce((a, b) => (b.naturalWidth > a.naturalWidth ? b : a)) : null;
  return {
    stillGenerating: !!stopBtn,
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
    r"try again (later|in)|too many requests)", re.IGNORECASE)
PAYWALL_RE = re.compile(
    r"(upgrade to (plus|go|pro|team)|get chatgpt plus|subscribe to continue|"
    r"unlock with plus|plus plan|pro plan)", re.IGNORECASE)


def classify_hazard(body_text: str, composer_present: bool) -> tuple[str, str] | None:
    """(kind, excerpt) for a logged-out/usage-limit/paywall page state, else None.

    Refusal is NOT covered here — it has no fixed wording; it is instead the
    terminal "generation ended with no image" state, handled by the caller
    with the assistant's own turn text (whatever it actually said)."""
    text = body_text or ""
    if not composer_present:
        m = SIGNED_OUT_RE.search(text)
        if m:
            return ("signed_out", text[max(0, m.start() - 40):m.end() + 40].strip())
    m = USAGE_LIMIT_RE.search(text)
    if m:
        return ("usage_limit", text[max(0, m.start() - 40):m.end() + 80].strip())
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
        prompt_m = _PROMPT_RE.search(block)
        if not prompt_m:
            raise ValueError(f"image {name!r}: no PROMPT START/END block found")
        images.append({
            "name": name,
            "prompt": prompt_m.group(1).strip(),
            "attach": attach_m.group(1) if attach_m else None,
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


def save_ledger(path: Path, rows: dict) -> None:
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
    orchestration without Chrome — nothing here is exercised by the unit
    tests; see tests/test_chatgpt_images.py's docstring."""

    def __init__(self, cdp_url: str = CDP_DEFAULT):
        self.cdp_url = cdp_url
        self._pw = None
        self._browser = None
        self.page = None

    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        self.page = page
        return page

    def close(self) -> None:
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

    def new_chat(self) -> None:
        self.page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=30_000)
        self.mute_all_media()
        self.page.wait_for_timeout(500)

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
        ok = self.page.evaluate(PASTE_JS, text)
        if not ok:
            raise RuntimeError("paste failed: composer not found")

    def read_composer_text(self) -> str:
        paragraphs = self.page.evaluate(READ_PARAGRAPHS_JS)
        return "\n\n".join(paragraphs)

    def send(self) -> None:
        page = self.page
        before_url = page.url
        try:
            page.locator(SEND_SEL).first.click(timeout=5000)
        except Exception:
            pass
        if not self._wait_url_changed(before_url, timeout_s=4):
            # REPLAY.md: a ref/pixel click can silently not register; a
            # direct JS click on the real DOM element is what worked there.
            page.evaluate(
                "() => { const b = document.querySelector("
                f"'{SEND_SEL}'"
                "); if (b) b.click(); }")
            self._wait_url_changed(before_url, timeout_s=4)

    def _wait_url_changed(self, before: str, timeout_s: float) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self.page.url != before:
                return True
            time.sleep(0.3)
        return False

    def wait_for_result(self, timeout_s: int = COMPLETION_TIMEOUT_S) -> dict:
        start = time.time()
        last_src, stable = None, 0
        while time.time() - start < timeout_s:
            state = self.page.evaluate(POLL_JS)
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
            elapsed = time.time() - start
            if (not state["stillGenerating"] and not state["imgPresent"]
                    and elapsed > POST_SEND_GRACE_S):
                return {"status": "refusal",
                         "text": state["lastAssistantText"] or "(no assistant text found)"}
            time.sleep(POLL_S)
        return {"status": "timeout"}

    def fetch_image_bytes(self, url: str) -> bytes:
        resp = self.page.request.get(url)
        if resp.status != 200:
            raise RuntimeError(f"image fetch failed: HTTP {resp.status} for {url}")
        return resp.body()


# ── orchestration ────────────────────────────────────────────────────────────

def process_one(browser: ChatGPTBrowser, image: dict, out_dir: Path,
                 ledger_path: Path, ledger: dict, timeout_s: int) -> dict:
    name = image["name"]
    out_path = out_dir / f"{name}.png"

    def _fail(status: str, note: str, **extra) -> dict:
        row = {"name": name, "status": status, "note": note, "time": now_iso(), **extra}
        ledger[name] = row
        save_ledger(ledger_path, ledger)
        return row

    if out_path.exists():
        return _fail("failed", f"{out_path} already exists — refusing to overwrite")

    browser.new_chat()

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
            browser.paste_prompt(image["prompt"])
            got = browser.read_composer_text()
        if normalize_ws(got) != normalize_ws(image["prompt"]):
            raise RuntimeError("composer text does not match the prompt after 2 paste attempts")
        browser.send()
    except Exception as e:
        return _fail("failed", f"send failed: {e!r}")

    chat_url = browser.page.url
    result = browser.wait_for_result(timeout_s=timeout_s)

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
        "time": now_iso(), "note": "",
    }
    ledger[name] = row
    save_ledger(ledger_path, ledger)
    return row


def cmd_run(args) -> int:
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
            done = ledger.get(im["name"], {}).get("status") == "done"
            tag = " [already done]" if done else ""
            print(f"  - {im['name']}{attach}: {first_line}...{tag}")
        return 0

    todo = [im for im in images if ledger.get(im["name"], {}).get("status") != "done"]
    if not todo:
        print("nothing to do — every requested image already has a 'done' ledger row")
        return 0

    browser = ChatGPTBrowser(cdp_url=args.cdp_url)
    browser.attach()
    try:
        for image in todo:
            row = process_one(browser, image, out_dir, ledger_path, ledger, args.timeout_s)
            if row["status"] == "stopped":
                print(f"STOPPED at {image['name']!r}: {row.get('hazard_kind')} — {row.get('note')}")
                print("Fix the underlying condition (log in / wait out the usage limit / "
                      "review the refusal) and re-run the same command — finished images "
                      "are skipped automatically.")
                return 1
            extra = f" — {row.get('note')}" if row.get("note") else ""
            print(f"{image['name']}: {row['status']}{extra}")
    finally:
        browser.close()

    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--brief", help="brief markdown with PROMPT START/END blocks")
    src.add_argument("--json", help="JSON file: a list of {name, prompt, attach?}")
    ap.add_argument("--out", required=True,
                     help="output dir for <name>.png and ledger.json")
    ap.add_argument("--one", help="only process this one image name")
    ap.add_argument("--dry-run", action="store_true",
                     help="parse the brief and print what would run; no browser touched")
    ap.add_argument("--cdp-url", default=CDP_DEFAULT,
                     help=f"default {CDP_DEFAULT} — the dedicated ChatGPT Chrome")
    ap.add_argument("--timeout-s", type=int, default=COMPLETION_TIMEOUT_S,
                     help="per-image generation timeout in seconds (default 360)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
