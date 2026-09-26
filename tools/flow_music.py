#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The zero-model Google Flow Music runner: instrumental cues from a prompts JSON.

IRON-RULES §53: the ILAG trailer needs 12 music cues; repeating a browser operation that often is a runner's
job, not a model's. Same shape as tools/topview_wan3.py: Playwright over CDP, one adapter class, a resumable
JSON ledger, the result's bytes fetched directly (never from the shared Downloads folder).

Drives the automation Chrome on winbox (CDP 9224, signed in to Google as pass.gob1@gmail.com; Flow Music
signs in with "Continue with Google", no credential typed) with the pwvenv Python. Opens its OWN tab and closes
it at the end; never touches another tab (ChatGPT, TopView and Outlook run in that browser).

    C:/mooniex/pwvenv/Scripts/python.exe tools/flow_music.py PROMPTS.json --out OUTDIR ^
        --max-credits-per-track 20 [--ids A1,A2] [--dry-run] [--length 1:00] [--format wav|m4a]
    ... --recover A1        collect A1's finished songs after the runner stopped waiting; fires nothing

PROMPTS.json is a list of {id, title, prompt, ...}. Output: OUTDIR/<id>-<n>.<ext> (n = 1.. in creation order,
one file per song the Generate click produced) and OUTDIR/ledger.json.

Per prompt (measured live 2026-09-26 on www.flowmusic.app, account tier "Member" via Google AI Ultra):
  1. open the library (/library/my-songs): the page's own GET /__api/clips/auth-user lists the newest 20 songs
     (the "before" set); read the balance off the account menu ("30610 credits");
  2. open a new session with the Compose panel (/session?t=true): Lyrics box + "Instrumental" switch
     (aria "Toggle instrumental mode"), "Sound" box (textarea aria "Sound description", maxlength 3000),
     "Advanced" switch -> Dynamics: BPM (3 digits, Auto), Length (m:ss text box, Auto; the UI clamps it to
     1:00..3:00: "0:30" becomes "1:00"), Seed (Auto), Model ("Lyria 3.5"; the other is "Lyria 3 Pro, Legacy");
     Details: title (maxlength 100) + cover image;
  3. Instrumental ON, Sound = the prompt (read back exactly), Advanced ON, Length = --length (default 1:00,
     the shortest the UI accepts), model read back "Lyria 3.5", title "ILAG <id> <title>";
  4. the Generate button shows NO price (text "Generate", tooltip "Generate Ctrl Enter"); /pricing says the
     Member plan's 30,000 credits are "~6000 songs" (about 5 per song). So the money gate is: the button reads
     exactly "Generate", no dialog/purchase text is up, and the balance is >= --max-credits-per-track; after the
     track the balance is read again and a charge above the cap stops the run before the next prompt;
  5. one click on Generate (the ledger row says "submitted" BEFORE the click, so nothing ever fires twice);
  6. poll the library until every new song whose operation.sound_prompt (or conversation) is ours has
     duration.status "completed", then fetch each song's wav_url / audio_url (public storage.googleapis.com
     object) and write <id>-<n>.<ext>; the UI's own Download > WAV menu is the fallback.

Money (HARD): the runner clicks only the controls named here. It never clicks Buy Credits, Get Credits, Pricing,
Upgrade, Subscribe, Split stems, Get stems, Remix, Publish or anything in a dialog. A dialog or text that says
credits are short or a plan/purchase is needed stops the run with that text in the ledger.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CDP_DEFAULT = "http://127.0.0.1:9224"
BASE = "https://www.flowmusic.app"
COMPOSE_URL = BASE + "/session?t=true"      # "New session" with the Compose panel open
LIBRARY_URL = BASE + "/library/my-songs"
CLIPS_API = "/__api/clips/auth-user"
CREDITS_API = "/__api/billing/credits"
MODEL_LABEL = "Lyria 3.5"
PROMPT_MAX = 3000                            # the Sound box's maxlength
TITLE_MAX = 100                              # the title box's maxlength
RESULT_TIMEOUT_S = 15 * 60
POLL_S = 15

# ── pure helpers (no browser; tests/test_flow_music.py) ───────────────────────


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def load_prompts(path: Path) -> list[dict]:
    items = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("prompts") or items.get("items") or []
    seen = set()
    for it in items:
        if not it.get("id") or not it.get("prompt"):
            raise ValueError(f"every item needs id and prompt: {str(it)[:120]}")
        if it["id"] in seen:
            raise ValueError(f"duplicate id {it['id']}")
        seen.add(it["id"])
        if len(it["prompt"]) > PROMPT_MAX:
            raise ValueError(f"{it['id']}: prompt is {len(it['prompt'])} chars, the Sound box takes {PROMPT_MAX}")
    return items


def parse_credits(text: str) -> float | None:
    """'30610 credits' / '30,610 credits' / 'Credits 30610 available' -> 30610.0."""
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(?:credits|available)", text or "", re.IGNORECASE)
    return float(m.group(1).replace(",", "")) if m else None


def length_seconds(value: str) -> int:
    m = re.fullmatch(r"\s*(\d+):([0-5]\d)\s*", value or "")
    if not m:
        raise ValueError(f"length must be m:ss, got {value!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def check_length(value: str) -> str:
    """The Length box clamps to 1:00..3:00 (measured: '0:30' -> '1:00', '9:59' -> '3:00'); refuse what it would
    silently change, so the ledger never claims a length the UI did not keep."""
    s = length_seconds(value)
    if not 60 <= s <= 180:
        raise ValueError(f"Flow Music accepts 1:00..3:00, got {value!r}")
    return f"{s // 60}:{s % 60:02d}"


def song_title(item: dict) -> str:
    return normalize_ws(f"ILAG {item['id']} {item.get('title') or ''}")[:TITLE_MAX]


def clip_status(clip: dict) -> str:
    """'completed' when the song is playable (duration known and a file URL), 'failed' on any failed field,
    else 'pending'."""
    stats = [v.get("status") for v in clip.values() if isinstance(v, dict) and "status" in v]
    if any(s in ("failed", "error", "errored", "cancelled", "canceled") for s in stats):
        return "failed"
    dur = (clip.get("duration") or {})
    if dur.get("status") == "completed" and (clip.get("wav_url") or clip.get("audio_url")):
        return "completed"
    return "pending"


def clip_seconds(clip: dict) -> float | None:
    try:
        return float((clip.get("duration") or {}).get("value"))
    except (TypeError, ValueError):
        return None


def ours(clip: dict, before_ids: set, prompt: str, session_id: str | None) -> bool:
    """A song belongs to this prompt when it was not in the library before the click and either its
    operation's sound_prompt is our prompt or it sits in the session the click created."""
    if clip.get("id") in before_ids:
        return False
    op = clip.get("operation") or {}
    if session_id and op.get("conversation_id") == session_id:
        return True
    return normalize_ws(op.get("sound_prompt")) == normalize_ws(prompt)


def session_id_from_url(url: str) -> str | None:
    m = re.search(r"/session/([0-9a-f-]{36})", url or "")
    return m.group(1) if m else None


HAZARD_RE = re.compile(
    r"(buy credits|get credits|out of credits|not enough credits|insufficient|no credits|credits? (are|is) (low|short)|"
    r"upgrade (your )?(plan|to)|subscribe|payment|add (a )?card|billing|top.?up|"
    r"log ?in to|sign ?in to continue|violat|content policy|can.t generate|generation failed|something went wrong)",
    re.IGNORECASE)


def classify_hazard(text: str) -> str | None:
    m = HAZARD_RE.search(text or "")
    if not m:
        return None
    return normalize_ws(text[max(0, m.start() - 80):m.end() + 120])


def wav_duration(data: bytes) -> float | None:
    """Seconds from a RIFF/WAVE header: data chunk size / fmt byte rate. None if not a WAV."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    i, byte_rate = 12, None
    while i + 8 <= len(data):
        cid, size = data[i:i + 4], int.from_bytes(data[i + 4:i + 8], "little")
        if cid == b"fmt ":
            byte_rate = int.from_bytes(data[i + 16:i + 20], "little")
        elif cid == b"data":
            if not byte_rate:
                return None
            size = min(size, len(data) - i - 8)
            return size / byte_rate
        i += 8 + size + (size & 1)
    return None


def mp4_duration(data: bytes) -> float | None:
    """Seconds from the mp4/m4a 'mvhd' box; None if it is not an mp4."""
    i = data.find(b"mvhd")
    if i < 0 or len(data) < i + 40:
        return None
    if data[i + 4] == 1:
        scale, dur = int.from_bytes(data[i + 24:i + 28], "big"), int.from_bytes(data[i + 28:i + 36], "big")
    else:
        scale, dur = int.from_bytes(data[i + 16:i + 20], "big"), int.from_bytes(data[i + 20:i + 24], "big")
    return dur / scale if scale else None


def audio_duration(data: bytes, fmt: str) -> float | None:
    return wav_duration(data) if fmt == "wav" else mp4_duration(data)


# ── ledger (atomic, same as topview_wan3) ──────────────────────────────────────

def load_ledger(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_ledger(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


FIRED = ("submitted", "done", "failed-after-submit")


class HazardStop(Exception):
    def __init__(self, kind: str, text: str):
        super().__init__(f"{kind}: {text}")
        self.kind, self.text = kind, text

# ── page scripts ───────────────────────────────────────────────────────────────


STATE_JS = r"""
() => {
  const vis = e => { if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const txt = e => (e ? (e.innerText || '').replace(/\s+/g, ' ').trim() : '');
  const sw = a => { const e = document.querySelector(`button[aria-label="${a}"]`); return e && vis(e) ? e.getAttribute('aria-checked') : null; };
  const label = t => [...document.querySelectorAll('label')].find(l => txt(l) === t);
  const lenIn = (() => { const l = label('Length'); return l ? l.parentElement.querySelector('input') : null; })();
  const bpmIn = (() => { const l = label('BPM'); return l ? l.parentElement.querySelector('input') : null; })();
  const modelBtn = (() => { const l = label('Model') || [...document.querySelectorAll('div,span,p')].find(e => e.childElementCount === 0 && txt(e) === 'Model');
      return l ? l.parentElement.querySelector('button') : null; })();
  const gens = [...document.querySelectorAll('button')].filter(b => vis(b) && /^Generate$/.test(txt(b)));
  const sound = document.querySelector('textarea[aria-label="Sound description"]');
  const title = [...document.querySelectorAll('textarea[maxlength="100"]')].find(vis);
  const dialogs = [...document.querySelectorAll('[role=dialog], [role=alertdialog], [role=alert], [role=status], [data-sonner-toast]')]
      .filter(vis).map(txt).filter(Boolean);
  const menuBtn = document.querySelector('button[aria-label="Settings menu"]');
  return {
    url: location.href,
    signedIn: !!menuBtn,
    loginButton: [...document.querySelectorAll('button')].some(b => vis(b) && /^(Log in|Sign up)$/.test(txt(b))),
    soundVisible: vis(sound), soundValue: sound ? sound.value : null,
    instrumental: sw('Toggle instrumental mode'), advanced: sw('Toggle advanced sound mode'),
    length: lenIn ? lenIn.value : null, lengthPlaceholder: lenIn ? lenIn.getAttribute('placeholder') : null,
    bpm: bpmIn ? bpmIn.value : null, model: txt(modelBtn),
    titleValue: title ? title.value : null,
    genCount: gens.length, genText: gens.length ? txt(gens[0]) : '', genDisabled: gens.length ? gens[0].disabled : null,
    dialogs,
  };
}
"""

LENGTH_INPUT = "xpath=//label[normalize-space(.)='Length']/following-sibling::input"
SOUND_BOX = 'textarea[aria-label="Sound description"]'


class FlowMusicBrowser:
    """Playwright-over-CDP adapter. The only class that touches Chrome; everything it clicks is named here."""

    def __init__(self, cdp_url: str = CDP_DEFAULT, log=print):
        self.cdp_url, self.log = cdp_url, log
        self._pw = self._browser = self.page = None
        self.responses: list = []
        self.api_credits: float | None = None

    # connection ---------------------------------------------------------------
    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        self.page = self._browser.contexts[0].new_page()  # our own tab, closed in close()
        self.page.on("response", lambda r: self.responses.append(r)
                     if "flowmusic.app/__api/" in r.url and r.request.resource_type in ("xhr", "fetch") else None)
        return self.page

    def close(self, keep_tab: bool = False) -> None:
        try:
            if self.page and not keep_tab:
                self.page.close()
        except Exception:
            pass
        for obj, fn in ((self._browser, "close"), (self._pw, "stop")):
            try:
                if obj:
                    getattr(obj, fn)()  # CDP: disconnect only; Chrome and the other tabs stay
            except Exception:
                pass

    def state(self) -> dict:
        return self.page.evaluate(STATE_JS)

    def drain(self) -> list[dict]:
        """Read the bodies of the app's own API answers collected since the last drain (call before any
        navigation): keeps the latest credits_remaining and returns a short log of POSTs."""
        notes = []
        batch, self.responses = self.responses, []
        for r in batch:
            try:
                if CREDITS_API in r.url:
                    self.api_credits = float(r.json()["data"]["credits_remaining"])
                elif r.request.method in ("POST", "PUT"):
                    notes.append({"url": r.url[:160], "status": r.status, "body": (r.text() or "")[:500]})
            except Exception:
                continue
        return notes

    # library + balance ----------------------------------------------------------
    def library_clips(self) -> list[dict]:
        """Open the library; return the clips the page's own GET /__api/clips/auth-user answered (newest 20)."""
        self.drain()
        with self.page.expect_response(lambda r: CLIPS_API in r.url and r.request.method == "GET",
                                       timeout=60_000) as ri:
            self.page.goto(LIBRARY_URL, wait_until="domcontentloaded", timeout=60_000)
        clips = ri.value.json().get("clips") or []
        self.page.wait_for_timeout(2500)
        st = self.state()
        if not st["signedIn"] or st["loginButton"]:
            raise HazardStop("signed_out", "Flow Music shows Log in / Sign up: not signed in")
        return clips

    def read_balance(self) -> tuple[float | None, str]:
        """The number the account menu shows ('30610 credits'); the menu is closed again with Escape."""
        self.page.locator('button[aria-label="Settings menu"]').first.click(timeout=8000)
        text = ""
        for _ in range(10):
            self.page.wait_for_timeout(500)
            items = self.page.locator("[role=menu] [role=menuitem]", has_text=re.compile(r"\d\s*credits"))
            if items.count():
                text = normalize_ws(items.first.inner_text())
                break
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)
        self.drain()
        return parse_credits(text), text

    # compose --------------------------------------------------------------------
    def open_compose(self) -> dict:
        self.drain()
        self.page.goto(COMPOSE_URL, wait_until="domcontentloaded", timeout=60_000)
        for _ in range(30):
            st = self.state()
            if st["soundVisible"]:
                break
            if st["loginButton"]:
                raise HazardStop("signed_out", "Flow Music shows Log in / Sign up: not signed in")
            self.page.wait_for_timeout(1000)
        else:
            tog = self.page.locator('button[aria-label="Toggle compose panel"], button[aria-label="Open compose panel"]')
            if tog.count():
                tog.first.click(timeout=5000)
                self.page.wait_for_timeout(2000)
        for sect in ("Lyrics", "Sound", "Details"):
            exp = self.page.locator(f'button[aria-label="Expand {sect} section"]')
            if exp.count() and exp.first.is_visible():
                exp.first.click(timeout=5000)
                self.page.wait_for_timeout(700)
        st = self.state()
        if not st["soundVisible"]:
            raise RuntimeError(f"the Compose panel's Sound box did not appear ({st['url']})")
        return st

    def set_switch(self, aria: str, want: bool) -> None:
        sw = self.page.locator(f'button[role=switch][aria-label="{aria}"]').first
        if (sw.get_attribute("aria-checked") == "true") != want:
            sw.click(timeout=5000)
            self.page.wait_for_timeout(800)
        got = sw.get_attribute("aria-checked") == "true"
        if got != want:
            raise RuntimeError(f"switch {aria!r} reads {got}, wanted {want}")

    def put_sound(self, prompt: str) -> None:
        box = self.page.locator(SOUND_BOX).first
        for _ in range(2):
            box.click(timeout=5000)
            box.fill(prompt, timeout=10_000)  # a React <textarea>: fill() sets the value and fires input
            self.page.wait_for_timeout(800)
            if box.input_value() == prompt:
                return
        raise RuntimeError(f"Sound box read-back does not match ({len(box.input_value())} chars vs {len(prompt)})")

    def set_length(self, value: str) -> str:
        inp = self.page.locator(LENGTH_INPUT).first
        for _ in range(2):
            inp.click(timeout=5000)
            self.page.keyboard.press("Control+a")
            self.page.keyboard.press("Backspace")
            self.page.keyboard.type(value, delay=60)
            self.page.keyboard.press("Tab")  # the box normalises (and clamps) on blur
            self.page.wait_for_timeout(700)
            if inp.input_value() == value:
                return value
        raise RuntimeError(f"Length reads {inp.input_value()!r}, wanted {value!r}")

    def put_title(self, title: str) -> str | None:
        box = self.page.locator('textarea[maxlength="100"]')
        vis = [i for i in range(box.count()) if box.nth(i).is_visible()]
        if not vis:
            return None
        el = box.nth(vis[0])
        el.click(timeout=5000)
        el.fill(title, timeout=5000)
        self.page.wait_for_timeout(500)
        return el.input_value()

    def click_generate(self) -> None:
        """One click on the one visible button whose whole text is 'Generate'."""
        btn = self.page.locator("button:visible", has_text=re.compile(r"^\s*Generate\s*$"))
        if btn.count() != 1:
            raise RuntimeError(f"{btn.count()} visible Generate buttons; not clicked")
        if btn.first.is_disabled():
            raise RuntimeError("Generate is disabled; not clicked")
        btn.first.click(timeout=8000)

    # files ------------------------------------------------------------------------
    def fetch(self, url: str) -> bytes:
        resp = self.page.request.get(url, timeout=180_000)
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url[:120]}")
        return resp.body()

    def ui_download(self, clip_id: str, fmt: str, out_path: Path) -> None:
        """Fallback: the library row's More options > Download > WAV/M4A, caught as a download event.
        The format item is clicked with a DOM click: Playwright's pointer click on the submenu item timed out
        (the submenu closes on the pointer's way there), the DOM click selects it (measured 2026-09-26)."""
        self.page.keyboard.press("Escape")
        row_more = self.page.locator(
            f"xpath=//a[@href='/song/{clip_id}']/ancestor::*[.//button[starts-with(@aria-label,'More options for')]][1]"
            "//button[starts-with(@aria-label,'More options for')]").first
        row_more.click(timeout=8000)
        self.page.wait_for_timeout(1000)
        self.page.locator("[role=menu] [role=menuitem]", has_text=re.compile(r"^\s*Download\s*$")).first.click(timeout=5000)
        self.page.wait_for_timeout(1200)
        item = self.page.locator("[role=menu] [role=menuitem]", has_text=re.compile(rf"^\s*{fmt.upper()}\s*$")).last
        with self.page.expect_download(timeout=120_000) as dinfo:
            item.evaluate("e => e.click()")
        dinfo.value.save_as(str(out_path))
        self.page.keyboard.press("Escape")


# ── orchestration ──────────────────────────────────────────────────────────────

def prepare(browser: FlowMusicBrowser, item: dict, length: str, set_title: bool) -> dict:
    """Everything up to (not including) the Generate click. Returns what was read."""
    browser.open_compose()
    browser.set_switch("Toggle instrumental mode", True)
    browser.put_sound(item["prompt"])
    browser.set_switch("Toggle advanced sound mode", True)
    browser.set_length(length)
    title = browser.put_title(song_title(item)) if set_title else None
    st = browser.state()
    if st["model"] != MODEL_LABEL:
        raise RuntimeError(f"model reads {st['model']!r}, wanted {MODEL_LABEL!r}")
    if st["instrumental"] != "true" or st["advanced"] != "true" or st["length"] != length:
        raise RuntimeError(f"settings drifted: instrumental={st['instrumental']} advanced={st['advanced']} "
                           f"length={st['length']!r}")
    if st["soundValue"] != item["prompt"]:
        raise RuntimeError("the Sound box changed after it was filled")
    return {"compose_url": st["url"], "instrumental": True, "length": st["length"], "bpm": st["bpm"] or "Auto",
            "model": st["model"], "title_set": title, "gen_text": st["genText"], "gen_count": st["genCount"],
            "gen_disabled": st["genDisabled"], "dialogs": st["dialogs"], "prompt_chars": len(item["prompt"])}


def gate(st: dict, balance: float | None, cap: float) -> None:
    """The money gate before the click. Flow Music shows no price on Generate, so the cap is enforced on the
    balance before (enough for one track at the cap) and on the charge after each track (run())."""
    if st["genCount"] != 1 or st["genText"] != "Generate":
        raise HazardStop("button", f"expected one button reading exactly 'Generate', saw {st['genCount']} "
                                   f"reading {st['genText']!r}")
    if st["genDisabled"]:
        raise HazardStop("disabled", "Generate is disabled")
    for d in st["dialogs"]:
        hz = classify_hazard(d)
        if hz:
            raise HazardStop("dialog", hz)
    if balance is None:
        raise HazardStop("balance", "could not read the credit balance")
    if balance < cap:
        raise HazardStop("balance", f"balance {balance} < --max-credits-per-track {cap}")


def wait_for_songs(browser: FlowMusicBrowser, item: dict, before_ids: set, session_id: str | None,
                   timeout_s: int, row: dict) -> list[dict]:
    """Poll the library until the new songs for this prompt are all completed and their count held still for
    one extra poll (a second variation may land after the first). Returns them oldest first."""
    start, last, stable = time.time(), None, 0
    while time.time() - start < timeout_s:
        clips = browser.library_clips()
        mine = [c for c in clips if ours(c, before_ids, item["prompt"], session_id)]
        stats = [clip_status(c) for c in mine]
        note = f"{len(mine)} song(s): {stats}"
        if note != last:
            browser.log(f"  [{int(time.time() - start)}s] {note}")
            last, stable = note, 0
        else:
            stable += 1
        if any(s == "failed" for s in stats):
            row["failed_clips"] = [c.get("id") for c, s in zip(mine, stats) if s == "failed"]
        if mine and all(s != "pending" for s in stats) and stable >= 1:
            done = [c for c, s in zip(mine, stats) if s == "completed"]
            if not done:
                raise RuntimeError(f"every new song failed: {row.get('failed_clips')}")
            return sorted(done, key=lambda c: c.get("created_at") or "")
        hz = classify_hazard(" ".join(browser.state()["dialogs"]))
        if hz:
            raise HazardStop("dialog", hz)
        time.sleep(POLL_S)
    raise TimeoutError(f"songs not completed after {timeout_s}s (last: {last})")


def save_song(browser: FlowMusicBrowser, clip: dict, fmt: str, out_path: Path) -> dict:
    url = clip.get("wav_url") if fmt == "wav" else clip.get("audio_url")
    via, data = "file_url", None
    try:
        if not url:
            raise RuntimeError(f"no {fmt} URL on the clip")
        data = browser.fetch(url)
        if audio_duration(data, fmt) is None:
            raise RuntimeError(f"{url[:100]} is not a {fmt} file ({data[:12]!r})")
    except Exception as e:
        browser.log(f"  direct fetch failed ({e!r}); using the UI's Download > {fmt.upper()}")
        via = f"ui-download ({e!r})"[:200]
        browser.library_clips()
        tmp = out_path.with_suffix(out_path.suffix + ".part")
        browser.ui_download(clip["id"], fmt, tmp)
        data = tmp.read_bytes()
        tmp.unlink()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, out_path)
    return {"file": str(out_path), "clip_id": clip["id"], "title": clip.get("title"), "bytes": len(data),
            "md5": hashlib.md5(data).hexdigest(), "seconds_header": round(audio_duration(data, fmt) or 0, 3),
            "seconds_api": clip_seconds(clip), "url": url, "via": via}


def collect(browser: FlowMusicBrowser, item: dict, songs: list[dict], out_dir: Path, fmt: str) -> list[dict]:
    files = []
    for n, clip in enumerate(songs, 1):
        out_path = out_dir / f"{item['id']}-{n}.{fmt}"
        files.append(save_song(browser, clip, fmt, out_path))
        browser.log(f"  saved {out_path.name} {files[-1]['seconds_header']}s {files[-1]['bytes']} bytes")
    return files


def run_item(browser: FlowMusicBrowser, item: dict, args, ledger: dict, ledger_path: Path) -> dict:
    key = item["id"]
    lkey = f"{key}:dry-run" if args.dry_run else key  # a dry run never overwrites a fired row
    row = dict(ledger.get(lkey) or {}, id=key, title=item.get("title"))

    def save(status: str, **kw) -> dict:
        row.update(kw, status=status, time=now_iso())
        ledger[lkey] = row
        save_ledger(ledger_path, ledger)
        return row

    if row.get("status") in FIRED and not args.dry_run:
        return save(row["status"], note=f"already {row['status']}; not fired again (use --recover {key})")
    out_dir = Path(args.out)
    if not args.dry_run and list(out_dir.glob(f"{key}-*.{args.format}")):
        return save("failed", note=f"{key}-*.{args.format} already in {out_dir}; refusing to overwrite")

    try:
        before = browser.library_clips()
        balance, balance_text = browser.read_balance()
        info = prepare(browser, item, args.length, not args.no_title)
    except HazardStop as h:
        return save("stopped", hazard_kind=h.kind, note=h.text)
    except Exception as e:
        return save("failed", note=f"prepare: {e!r}"[:500])
    before_ids = {c.get("id") for c in before}
    row.update(info, balance_before=balance, balance_text=balance_text, api_credits_before=browser.api_credits,
               cost_shown=None, cost_note="Flow Music shows no price on Generate (measured 2026-09-26)")
    browser.log(f"{key}: instrumental, {info['length']}, {info['model']}, title {info['title_set']!r}, "
                f"button {info['gen_text']!r}, balance {balance_text!r}, prompt {info['prompt_chars']} chars")
    if args.dry_run:
        return save("dry-run", note="everything but the Generate click")

    st = browser.state()
    try:
        gate(st, balance, args.max_credits_per_track)
    except HazardStop as h:
        return save("stopped", hazard_kind=h.kind, note=h.text)

    t0 = time.time()
    save("submitted", fired_at=now_iso(), before_ids=sorted(before_ids),
         note="Generate clicked once; never click it again for this id")
    try:
        browser.click_generate()
    except Exception as e:
        return save("failed-after-submit", note=f"Generate click raised {e!r}; check the library, then --recover")
    session_id = None
    for _ in range(30):  # the click's POST and the session URL arrive within seconds; hazards too
        browser.page.wait_for_timeout(1000)
        st = browser.state()
        session_id = session_id or session_id_from_url(st["url"])
        hz = classify_hazard(" ".join(st["dialogs"]))
        if hz:
            return save("failed-after-submit", hazard_kind="dialog", note=hz, session_url=st["url"])
        if session_id and time.time() - t0 > 8:
            break
    row.update(session_url=browser.page.url, session_id=session_id, network=browser.drain()[:6])
    try:
        songs = wait_for_songs(browser, item, before_ids, session_id, args.timeout_s, row)
        row["generation_s"] = round(time.time() - t0)
        files = collect(browser, item, songs, out_dir, args.format)
    except HazardStop as h:
        return save("failed-after-submit", hazard_kind=h.kind, note=h.text, generation_s=round(time.time() - t0))
    except Exception as e:
        return save("failed-after-submit", note=f"{e!r}"[:500], generation_s=round(time.time() - t0))
    browser.library_clips()
    after, after_text = browser.read_balance()
    charged = round(balance - after, 3) if balance is not None and after is not None else None
    return save("done", files=files, songs=len(files), balance_after=after, charged=charged,
                per_song=round(charged / len(files), 3) if charged is not None and files else None,
                api_credits_after=browser.api_credits)


def recover(browser: FlowMusicBrowser, item: dict, args, ledger: dict, ledger_path: Path) -> dict:
    """Collect the songs of an id that was fired but not collected. Opens the library, fires nothing."""
    key = item["id"]
    row = ledger.get(key) or {}
    if row.get("status") == "done":
        return dict(row, note="already done")
    if row.get("status") not in FIRED:
        return {"id": key, "status": "failed", "note": "this id was never fired; nothing to recover"}
    before_ids = set(row.get("before_ids") or [])
    songs = wait_for_songs(browser, item, before_ids, row.get("session_id"), args.timeout_s, row)
    files = collect(browser, item, songs, Path(args.out), args.format)
    browser.library_clips()
    after, _ = browser.read_balance()
    bal = row.get("balance_before")
    charged = round(bal - after, 3) if bal is not None and after is not None else None
    row.update(files=files, songs=len(files), balance_after=after, charged=charged, status="done", time=now_iso(),
               note="recovered")
    ledger[key] = row
    save_ledger(ledger_path, ledger)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompts", help="JSON list of {id, title, prompt, ...}")
    ap.add_argument("--out", required=True, help="dir for <id>-<n>.<ext> and ledger.json")
    ap.add_argument("--ids", help="comma-separated ids to run, in this order (default: all, file order)")
    ap.add_argument("--max-credits-per-track", type=float, required=True,
                    help="stop the run when one track charged more than this (the UI shows no price before)")
    ap.add_argument("--dry-run", action="store_true", help="fill and read everything; no Generate click")
    ap.add_argument("--length", default="1:00", help="m:ss, 1:00..3:00 (default 1:00, the shortest accepted)")
    ap.add_argument("--format", choices=["wav", "m4a"], default="wav")
    ap.add_argument("--no-title", action="store_true", help="leave the song title to Flow Music")
    ap.add_argument("--recover", metavar="ID", help="collect ID's finished songs; fires nothing")
    ap.add_argument("--cdp-url", default=CDP_DEFAULT)
    ap.add_argument("--timeout-s", type=int, default=RESULT_TIMEOUT_S)
    ap.add_argument("--keep-tab", action="store_true", help="leave the runner's tab open (debugging)")
    args = ap.parse_args(argv)
    args.length = check_length(args.length)

    items = load_prompts(Path(args.prompts))
    by_id = {it["id"]: it for it in items}
    if args.ids:
        wanted = [s.strip() for s in args.ids.split(",") if s.strip()]
        unknown = [w for w in wanted if w not in by_id]
        if unknown:
            ap.error(f"unknown ids {unknown}")
        items = [by_id[w] for w in wanted]
    if args.recover and args.recover not in by_id:
        ap.error(f"unknown id {args.recover}")

    ledger_path = Path(args.out) / "ledger.json"
    ledger = load_ledger(ledger_path)
    browser = FlowMusicBrowser(args.cdp_url)
    browser.attach()
    rc = 0
    try:
        if args.recover:
            row = recover(browser, by_id[args.recover], args, ledger, ledger_path)
            print(json.dumps(row, indent=1, ensure_ascii=False)[:4000])
            return 0 if row.get("status") == "done" else 1
        for it in items:
            row = run_item(browser, it, args, ledger, ledger_path)
            print(json.dumps({k: v for k, v in row.items() if k not in ("network", "before_ids")},
                             indent=1, ensure_ascii=False)[:4000])
            if row["status"] not in ("done", "dry-run"):
                print(f"STOP at {it['id']}: {row['status']} — {row.get('note')}")
                rc = 1
                break
            if row["status"] == "done" and row.get("charged") is not None \
                    and row["charged"] > args.max_credits_per_track:
                print(f"STOP after {it['id']}: charged {row['charged']} > --max-credits-per-track "
                      f"{args.max_credits_per_track}")
                rc = 1
                break
    finally:
        browser.close(keep_tab=args.keep_tab)
    return rc


if __name__ == "__main__":
    sys.exit(main())
