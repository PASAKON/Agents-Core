#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The zero-model TopView Wan 3.0 runner — docs/ops/briefs/topview-wan3-runner.md.

IRON-RULES §53: the ILAG trailer needs about 19 Wan 3.0 generations on TopView; repeating a browser
operation that often is a runner's job, not a model's. Same shape as tools/chatgpt_images.py: Playwright
over CDP, one adapter class, a resumable JSON ledger, the result's bytes fetched from the page (never from
the shared Downloads folder).

Drives the automation Chrome on winbox (CDP 9224, profile C:\\Users\\UsEr\\.chatgpt-automation\\chrome-profile,
TopView signed in as pass.gob1@gmail.com via Google) with the pwvenv Python. Opens its OWN tab and closes it
at the end; never touches another tab (ChatGPT runs in that browser).

    C:\\mooniex\\pwvenv\\Scripts\\python.exe tools\\topview_wan3.py ^
        C:\\mooniex\\ilag-runner\\wan3\\n01-rehearsal.wan3.json [more.wan3.json ...] ^
        --out C:\\mooniex\\ilag-runner\\wan3\\out [--resolution 480p|720p|1080p] ^
        --max-credits 3 [--dry-run [--probe-costs]] [--recover KEY]

A job file is what docs/prompts/ilag-topview/wan3_prompt.py writes: {key, title, seconds, images, prompt,
chars}. `images` are Drive paths; each is found by BASENAME in --refs (default: <job dir>/refs), uploaded in
that order, so upload N is Image N. The ledger key is the job file's stem without ".wan3" (n01-rehearsal),
so a rehearsal never collides with the real shot.

Per job (measured live 2026-09-26, see the skill CTO_Wan3.0_TopView Field notes):
  1. open GENERATOR_URL (the Wan 3.0 card on topview.ai/home; it redirects to /board/<id>), check signed in,
     model "Wan 3.0" (not "Wan 3.0 Prime"), tab "Omni Reference";
  2. remove any leftover reference, upload the images through the multiple <input type=file>;
     each upload appears as [data-input-asset] "Image1", "Image2"... AND drops its chip into the prompt;
  3. clear the prompt box (tiptap/ProseMirror), paste the prompt as plain text with every "@Image 1" rewritten
     to "@Image1": the box turns "@Image1" (and "<<<Image1>>>") into a mentionChip itself; "@Image 1" with a
     space stays plain text. Read back chip by chip and refuse on any mismatch;
  4. aspect 16:9, duration = the job's seconds (2-30 s offered), resolution (--resolution, default the lowest
     offered), Generation Count 1, Auto Upscale and Internet Search off;
  5. read the cost off the visible Generate button ("Generate 0.6"), the balance off the sidebar Credits
     button; click Generate only when cost <= --max-credits and cost <= balance; one click, never twice.
     On the Free plan (sidebar badge "Free") Generate opened the pricing modal "UPGRADE YOUR PLAN" and
     generated nothing (2026-09-26, balance stayed 5), so the runner stops before the click on "Free"
     (ledger "stopped", plan_required) and, if the modal appears after a click anyway, stops there too;
  6. wait for a new video (a new <video> src in the page, or an .mp4 URL in a JSON response after the click),
     fetch its bytes with page.request, write <out>/<key>.mp4, md5, balance after, ledger row "done".

Money (HARD, the brief): the runner clicks only the selectors named here. It never clicks Subscribe, Upgrade,
Buy, Top up, "Get Free Unlimited Generations", a trial, a payment screen, Regenerate or Retry. A dialog or text
that says the balance is short or a plan is needed stops the run with that text in the ledger. A job whose
ledger row is "submitted" or "done" is never fired again (the Generate click is recorded BEFORE it happens);
use --recover KEY to collect a clip that finished after the runner stopped waiting.
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
# The "Wan 3.0" card on https://www.topview.ai/home; TopView redirects it to /board/<the account's first board>.
GENERATOR_URL = "https://www.topview.ai/board/my-first-board?tool-type=video-edit&model-id=qwen-wan3.0-video"
MODEL_LABEL = "Wan 3.0"
MODE_LABEL = "Omni Reference"
ASPECT = "16:9"
RESULT_TIMEOUT_S = 25 * 60
POLL_S = 5

# ── pure helpers (no browser; tests/test_topview_wan3.py) ─────────────────────

_TOKEN_RE = re.compile(r"@(Image|Video|Audio)\s+(\d+)\b")
_ANGLE_RE = re.compile(r"<<<(Image|Video|Audio)(\d+)>>>")
_CHIP_RE = re.compile(r"@(Image|Video|Audio)(\d+)\b")


def normalize_tokens(prompt: str) -> str:
    """'@Image 1' / '<<<Image1>>>' -> '@Image1', the form TopView's paste handler turns into a chip."""
    return _ANGLE_RE.sub(r"@\1\2", _TOKEN_RE.sub(r"@\1\2", prompt))


def chip_tags(prompt: str) -> list[str]:
    """The chips a normalized prompt should produce, in order: ['@Image1', '@Image2', '@Image1', ...]."""
    return [m.group(0) for m in _CHIP_RE.finditer(prompt)]


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


_NUM = r"(\d+(?:[.,]\d+)?)"


def parse_cost(button_text: str, cost_aria=None) -> float | None:
    """What the click will charge. 'Generate 0.6' -> 0.6; 'Generate' (no number) -> None: no number, no click.
    With a free generation on the account the button reads 'Generate 7.5 0' (list price struck, then the charge)
    and the aria label reads 'Credits: 0' (measured 2026-09-26, Pro plan + the plugin's 5 free Wan 3.0): the
    aria label is the charge, else the LAST number on the button."""
    for a in cost_aria or []:
        m = re.fullmatch(r"\s*Credits:\s*" + _NUM + r"\s*", a or "")
        if m:
            return float(m.group(1).replace(",", ""))
    m = re.fullmatch(r"\s*Generate\s*" + _NUM + r"(?:\s+" + _NUM + r")?\s*", button_text or "")
    if not m:
        return None
    return float((m.group(2) or m.group(1)).replace(",", ""))


def parse_balance(text: str) -> float | None:
    m = re.search(_NUM, text or "")
    return float(m.group(1).replace(",", "")) if m else None


HAZARD_RE = re.compile(
    r"(insufficient|not enough credits|out of credits|credits? (are|is) not enough|top.?up credits to|"
    r"upgrade (your plan|to)|subscribe to|requires? (a|an)? ?(paid )?(plan|subscription)|"
    r"log ?in to|sign ?in to continue|violat|sensitive content|content policy|"
    r"generation failed|task failed|failed to generate)", re.IGNORECASE)


def classify_hazard(text: str) -> str | None:
    """An excerpt of the first money/login/failure phrase in `text`, else None."""
    m = HAZARD_RE.search(text or "")
    if not m:
        return None
    return normalize_ws(text[max(0, m.start() - 80):m.end() + 120])


RES_ORDER = ["360p", "480p", "540p", "720p", "1080p", "2k", "4k"]


def lowest_resolution(offered: list[str]) -> str:
    def rank(r):
        r = r.lower()
        return RES_ORDER.index(r) if r in RES_ORDER else 99
    return sorted(offered, key=rank)[0]


def job_key(job_path: Path) -> str:
    return re.sub(r"\.wan3$", "", job_path.stem)


def resolve_images(job: dict, refs_dir: Path) -> list[Path]:
    paths = [refs_dir / Path(p.replace("\\", "/")).name for p in job.get("images") or []]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("reference image(s) not found: " + ", ".join(missing))
    if len(paths) > 10:
        raise ValueError(f"{len(paths)} images; Wan 3.0 takes 10 at most")
    return paths


# a URL inside JSON may carry the escapes \/ and &; they are part of the URL, not its end
MP4_RE = re.compile(r"https?:(?:\\?/){2}(?:[^\"'\s\\]|\\/|\\u0026)+?\.mp4(?:\?(?:[^\"'\s\\]|\\/|\\u0026)*)?")


def mp4_urls(text: str) -> list[str]:
    return list(dict.fromkeys(u.replace("\\u0026", "&").replace("\\/", "/") for u in MP4_RE.findall(text or "")))


def mp4_duration(data: bytes) -> float | None:
    """Seconds from the mp4 'mvhd' box (no ffprobe needed on winbox); None if it is not an mp4."""
    i = data.find(b"mvhd")
    if i < 0 or len(data) < i + 40:
        return None
    if data[i + 4] == 1:  # version 1: 64-bit times
        scale, dur = int.from_bytes(data[i + 24:i + 28], "big"), int.from_bytes(data[i + 28:i + 36], "big")
    else:
        scale, dur = int.from_bytes(data[i + 16:i + 20], "big"), int.from_bytes(data[i + 20:i + 24], "big")
    return dur / scale if scale else None


# ── ledger (atomic, same as chatgpt_images) ────────────────────────────────────

def load_ledger(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_ledger(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


FIRED = ("submitted", "done", "failed-after-submit")


def _last(menu_text: str) -> str:
    """'SD 480p' -> '480p', '12s' -> '12s': menus compare by the last token, never by suffix ('12s' ends in '2s')."""
    parts = normalize_ws(menu_text).split(" ")
    return parts[-1] if parts else ""


class HazardStop(Exception):
    def __init__(self, kind: str, text: str):
        super().__init__(f"{kind}: {text}")
        self.kind, self.text = kind, text

# ── page scripts ───────────────────────────────────────────────────────────────

EDITOR = ".tiptap.ProseMirror"

PASTE_JS = """
(text) => { const el = document.querySelector('.tiptap.ProseMirror'); if (!el) return false; el.focus();
  const dt = new DataTransfer(); dt.setData('text/plain', text);
  el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); return true; }
"""

# The box read back as text: a chip becomes its data-image-tag ('@Image1'), <br> and paragraph ends newlines.
READ_EDITOR_JS = """
() => { const el = document.querySelector('.tiptap.ProseMirror'); if (!el) return null;
  const chips = []; let out = '';
  const walk = n => { for (const c of n.childNodes) {
      if (c.nodeType === 3) out += c.textContent;
      else if (c.nodeType === 1 && c.getAttribute('data-type') === 'mentionChip') { const t = c.getAttribute('data-image-tag'); chips.push(t); out += t; }
      else if (c.nodeName === 'BR') { if (!c.classList.contains('ProseMirror-trailingBreak')) out += '\\n'; }
      else { walk(c); if (c.nodeName === 'P') out += '\\n'; } } };
  walk(el); return {text: out, chips}; }
"""

STATE_JS = """
() => {
  const txt = e => (e ? (e.innerText || '').replace(/\\s+/g, ' ').trim() : '');
  const gen = [...document.querySelectorAll('button')].find(b => /^Generate\\b/.test(txt(b)));
  const credits = document.querySelector('button[aria-label="Credits"]');
  const costAria = [...document.querySelectorAll('[aria-label^="Credits:"]')].map(e => e.getAttribute('aria-label'));
  const menus = [...document.querySelectorAll('button[aria-haspopup=menu]')].map(txt);
  const model = [...document.querySelectorAll('button')].find(b => /^Wan \\d/.test(txt(b)) && b.getAttribute('data-state'));
  const modeBtn = [...document.querySelectorAll('button')].find(b => txt(b) === 'Omni Reference');
  const assets = [...document.querySelectorAll('[data-input-asset]')].map(a => ({label: a.getAttribute('aria-label'), busy: a.getAttribute('aria-busy')}));
  const switches = [...document.querySelectorAll('button[role=switch]')].map(s => {
      let p = s, label = ''; for (let i = 0; i < 4 && p && !label; i++) { p = p.parentElement; label = txt(p); }
      return {label: label.slice(0, 40), checked: s.getAttribute('aria-checked')}; });
  const body = document.body.innerText || '';
  const gc = body.match(/Generation Count\\s*:\\s*(\\d+)/);
  const dialogs = [...document.querySelectorAll('[role=dialog], [role=alertdialog]')]
      .filter(d => d.getBoundingClientRect().width > 0).map(txt).filter(Boolean);
  // the plan badge under the Credits number in the left sidebar ("Free" on 2026-09-26)
  const plan = [...document.querySelectorAll('div,span,p')].find(e => e.childElementCount === 0
      && /^(Free|Pro|Business|Ultra|Team|Enterprise)$/.test((e.innerText || '').trim())
      && e.getBoundingClientRect().x < 100 && e.getBoundingClientRect().width > 0);
  // what Generate opened on the Free plan: the pricing modal, "UPGRADE YOUR PLAN" (no generation, no charge)
  const pm = [...document.querySelectorAll('[class*=pricing-modal]')].find(e => e.getBoundingClientRect().width > 0);
  const pmHead = pm ? ((pm.innerText || '').match(/UPGRADE YOUR PLAN|Upgrade your plan|Buy Credits/) || [''])[0] : '';
  return {
    plan: txt(plan), pricingModal: pm ? (pmHead || txt(pm).slice(0, 120)) : '',
    url: location.href,
    signedIn: !!credits,
    loginButton: [...document.querySelectorAll('button')].some(b => /^(Login|Log in)$/.test(txt(b))),
    genText: txt(gen), genDisabled: gen ? gen.disabled : null, costAria,
    balanceText: txt(credits), menus, model: txt(model),
    modeActive: modeBtn ? /bg-\\[#3d3d3d\\]/.test(modeBtn.className) : null,
    assets, switches, generationCount: gc ? parseInt(gc[1]) : null, dialogs,
  };
}
"""

# Video URLs on the page, minus the site's own static assets (/public/ on the CDN: promo loops, icons).
MEDIA_JS = """
() => [...new Set([...document.querySelectorAll('video, video source')].map(v => v.currentSrc || v.src || v.getAttribute('src'))
      .filter(s => s && /^https?:/.test(s) && !/\\/public\\//.test(s)))]
"""

GEN_BUTTON_JS = """
() => [...document.querySelectorAll('button')].find(b => /^Generate\\b/.test((b.innerText || '').replace(/\\s+/g, ' ').trim()))
"""

MENU_ITEMS_JS = """
() => [...document.querySelectorAll('[data-radix-popper-content-wrapper] [role=menuitem]')]
      .map(e => (e.innerText || '').replace(/\\s+/g, ' ').trim())
"""


class TopViewBrowser:
    """Playwright-over-CDP adapter. The only class that touches Chrome; everything it clicks is named here."""

    def __init__(self, cdp_url: str = CDP_DEFAULT, log=print):
        self.cdp_url, self.log = cdp_url, log
        self._pw = self._browser = self.page = None
        self.responses: list = []

    # connection ---------------------------------------------------------------
    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        self.page = self._browser.contexts[0].new_page()  # our own tab, closed in close()
        # every TopView JSON answer is kept for drain_network: before the click it fills the "not ours" set,
        # after the click it is where the task's own video URL shows up first
        self.page.on("response", lambda r: self.responses.append(r)
                     if "topview" in r.url and r.request.resource_type in ("xhr", "fetch") else None)
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

    # navigation + setup ---------------------------------------------------------
    def open_generator(self, url: str = GENERATOR_URL) -> dict:
        self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        for _ in range(30):
            st = self.state()
            if st["signedIn"] and st["genText"]:
                break
            self.page.wait_for_timeout(1000)
        self.page.wait_for_timeout(1500)
        return self.state()

    def ensure_model(self) -> None:
        if self.state()["model"] == MODEL_LABEL:
            return
        self.page.locator("button[data-state]", has_text=re.compile(r"^Wan \d")).first.click(timeout=8000)
        self.page.wait_for_timeout(1200)
        items = self.page.locator("[role=dialog] button", has_text=re.compile(r"^Wan 3\.0(?! Prime)"))
        items.first.click(timeout=8000)
        self.page.wait_for_timeout(1500)
        if self.state()["model"] != MODEL_LABEL:
            raise RuntimeError(f"model did not switch to {MODEL_LABEL!r}: {self.state()['model']!r}")

    def ensure_mode(self) -> None:
        if not self.state()["modeActive"]:
            self.page.locator("button", has_text=re.compile(rf"^{MODE_LABEL}$")).first.click(timeout=8000)
            self.page.wait_for_timeout(1200)
        if not self.state()["modeActive"]:
            raise RuntimeError(f"tab {MODE_LABEL!r} is not active")

    def clear_references(self) -> None:
        for _ in range(12):
            rm = self.page.locator('button[aria-label^="Remove Image"], button[aria-label^="Remove Video"], '
                                   'button[aria-label^="Remove Audio"]')
            if rm.count() == 0:
                return
            rm.first.click(timeout=5000, force=True)
            self.page.wait_for_timeout(700)
        raise RuntimeError("could not remove the leftover references")

    def upload(self, paths: list[Path]) -> list[str]:
        for i, p in enumerate(paths, 1):
            self.page.locator("input[type=file][multiple]").first.set_input_files(str(p))
            for _ in range(60):
                assets = self.state()["assets"]
                if len(assets) >= i and all(a["busy"] != "true" for a in assets):
                    break
                self.page.wait_for_timeout(500)
            else:
                raise RuntimeError(f"upload {i} ({p.name}) did not settle: {self.state()['assets']}")
            self.page.wait_for_timeout(800)
        labels = [a["label"] for a in self.state()["assets"]]
        want = [f"Image{i}" for i in range(1, len(paths) + 1)]
        if labels != want:
            raise RuntimeError(f"references read {labels}, expected {want}")
        return labels

    def clear_prompt(self) -> None:
        self.page.locator(EDITOR).first.click(timeout=5000)
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Backspace")
        self.page.wait_for_timeout(400)

    def read_prompt(self) -> dict:
        return self.page.evaluate(READ_EDITOR_JS) or {"text": "", "chips": []}

    def put_prompt(self, prompt: str) -> dict:
        """Clear, paste once, verify; one clear-and-repaste if it did not match. Returns the read-back."""
        want_text, want_chips = normalize_ws(prompt), chip_tags(prompt)
        got = {}
        for _attempt in range(2):
            self.clear_prompt()
            if not self.page.evaluate(PASTE_JS, prompt):
                raise RuntimeError("prompt box (.tiptap.ProseMirror) not found")
            self.page.wait_for_timeout(1200)
            got = self.read_prompt()
            if normalize_ws(got["text"]) == want_text and got["chips"] == want_chips:
                return got
        raise RuntimeError(f"prompt read-back does not match: {len(normalize_ws(got.get('text', '')))} chars, "
                           f"chips {got.get('chips')} vs {want_chips}")

    # the settings menus (Radix dropdowns: modal, so a menu is closed by picking an item, never by Escape) ---
    def _menu_trigger(self, kind: str):
        pat = {"aspect": r"^\d+:\d+$", "duration": r"^\d+s$", "resolution": r"\d+p$"}[kind]
        return self.page.locator("button[aria-haspopup=menu]", has_text=re.compile(pat)).first

    def menu_value(self, kind: str) -> str:
        return normalize_ws(self._menu_trigger(kind).inner_text())

    def menu_options(self, kind: str) -> list[str]:
        """Open the menu, read the items, close it by re-picking the current value."""
        current = self.menu_value(kind)
        self._menu_trigger(kind).click(timeout=5000)
        self.page.wait_for_timeout(900)
        items = self.page.evaluate(MENU_ITEMS_JS)
        keep = next((it for it in items if _last(current) == it), items[0] if items else None)
        if keep:
            self._pick(keep)
        return items

    def _pick(self, item: str) -> None:
        self.page.locator("[data-radix-popper-content-wrapper] [role=menuitem]",
                          has_text=re.compile(rf"^\s*{re.escape(item)}\s*$")).first.click(timeout=5000)
        self.page.wait_for_timeout(900)

    def set_menu(self, kind: str, item: str) -> str:
        if _last(self.menu_value(kind)) != item:
            self._menu_trigger(kind).click(timeout=5000)
            self.page.wait_for_timeout(900)
            self._pick(item)
        got = self.menu_value(kind)
        if _last(got) != item:
            raise RuntimeError(f"{kind} reads {got!r}, wanted {item!r}")
        return got

    def switches_off(self) -> list[dict]:
        for i, sw in enumerate(self.state()["switches"]):
            if sw["checked"] == "true":
                self.page.locator("button[role=switch]").nth(i).click(timeout=5000)
                self.page.wait_for_timeout(600)
        sws = self.state()["switches"]
        if any(s["checked"] == "true" for s in sws):
            raise RuntimeError(f"a switch stayed on: {sws}")
        return sws

    # generate + result -----------------------------------------------------------
    def click_generate(self, expected_cost: float) -> None:
        """One click on the element whose text was just read; refuses if its number changed since the gate."""
        el = self.page.evaluate_handle(GEN_BUTTON_JS).as_element()
        if el is None:
            raise RuntimeError("Generate button not found")
        text = normalize_ws(el.inner_text())
        if parse_cost(text) != expected_cost:
            raise RuntimeError(f"Generate button now reads {text!r}, the gate read {expected_cost}; not clicked")
        el.click(timeout=8000)

    def media_srcs(self) -> list[str]:
        return self.page.evaluate(MEDIA_JS)

    def drain_network(self, seen: set) -> tuple[list[str], list[dict]]:
        """New .mp4 URLs in JSON responses since the click, and a short log of the POSTs/JSON bodies."""
        urls, notes = [], []
        batch, self.responses = self.responses, []
        for r in batch:
            try:
                ct = (r.headers or {}).get("content-type", "")
                if "json" not in ct or "topview" not in r.url:
                    continue
                body = r.text()
            except Exception:
                continue
            if r.request.method == "POST":
                notes.append({"url": r.url[:200], "status": r.status, "body": body[:600]})
            for u in mp4_urls(body):
                if u not in seen:
                    seen.add(u)
                    urls.append(u)
        return urls, notes

    def fetch(self, url: str) -> bytes:
        resp = self.page.request.get(url, timeout=120_000)
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url[:120]}")
        return resp.body()


# ── orchestration ──────────────────────────────────────────────────────────────

def prepare(browser: TopViewBrowser, job: dict, images: list[Path], resolution: str | None,
            probe_costs: bool) -> dict:
    """Everything up to (not including) the Generate click. Returns what was read."""
    st = browser.open_generator()
    if not st["signedIn"] or st["loginButton"]:
        raise HazardStop("signed_out", "TopView is not signed in (no Credits button / a Login button)")
    browser.ensure_model()
    browser.ensure_mode()
    browser.clear_references()
    browser.upload(images)
    prompt = normalize_tokens(job["prompt"])
    got = browser.put_prompt(prompt)
    info = {"generator_url": browser.page.url, "chips": got["chips"], "prompt_chars": len(prompt)}
    browser.set_menu("aspect", ASPECT)
    info["durations_offered"] = browser.menu_options("duration")
    secs = f"{int(job['seconds'])}s" if float(job["seconds"]) == int(job["seconds"]) else f"{job['seconds']}s"
    if secs not in info["durations_offered"]:
        raise RuntimeError(f"{secs} is not offered: {info['durations_offered']}")
    browser.set_menu("duration", secs)
    info["resolutions_offered"] = browser.menu_options("resolution")
    res = resolution or lowest_resolution(info["resolutions_offered"])
    if probe_costs:
        info["costs"] = {}
        for r in info["resolutions_offered"]:
            browser.set_menu("resolution", r)
            info["costs"][f"{secs} {r}"] = browser.state()["genText"]
    info["resolution"] = browser.set_menu("resolution", res)
    info["switches"] = browser.switches_off()
    st = browser.state()
    if st["generationCount"] != 1:
        raise RuntimeError(f"Generation Count reads {st['generationCount']}, the runner only fires 1")
    info.update(seconds=secs, gen_text=st["genText"], gen_disabled=st["genDisabled"], cost_aria=st["costAria"],
                balance_text=st["balanceText"], plan=st["plan"], model=st["model"],
                aspect=browser.menu_value("aspect"))
    return info


def wait_for_clip(browser: TopViewBrowser, seen: set, seconds: float, timeout_s: int,
                  row: dict) -> tuple[str, bytes]:
    """Poll until a NEW video whose file really is ~`seconds` long appears; return (url, bytes).

    `seen` holds every video URL on the page and in JSON before the click (promo loops, earlier clips), so
    only something that appeared after the click is a candidate, and a candidate is taken only when its own
    mp4 header says it is the job's length (+-1 s): a stray example clip is rejected and logged, not saved."""
    start, last_note = time.time(), None
    while time.time() - start < timeout_s:
        urls, notes = browser.drain_network(seen)
        if notes:
            row["network"] = (row.get("network", []) + notes[:5])[-12:]
        st = browser.state()
        if st["pricingModal"]:
            raise HazardStop("plan_required", f"pricing modal {st['pricingModal']!r} while waiting")
        for d in st["dialogs"]:
            hz = classify_hazard(d)
            if hz:
                raise HazardStop("dialog", hz)
        cands = urls + [u for u in browser.media_srcs() if u not in seen and u not in urls]
        for u in cands:  # a URL from the task's own JSON first, then a new <video> on the board
            seen.add(u)
            try:
                data = browser.fetch(u)
            except Exception as e:
                row.setdefault("rejected", []).append(f"{u[:120]} fetch {e!r}"[:220])
                continue
            dur = mp4_duration(data)
            if len(data) > 20_000 and dur is not None and abs(dur - float(seconds)) <= 1.0:
                row["video_duration_header"] = round(dur, 3)
                return u, data
            row.setdefault("rejected", []).append(f"{u[:120]} bytes={len(data)} dur={dur}")
        body = browser.page.evaluate("() => document.body.innerText || ''")
        hz = classify_hazard(body)
        if hz and re.search(r"fail|insufficient|not enough|violat|sensitive|policy", hz, re.I):
            raise HazardStop("page", hz)
        prog = re.findall(r"(Generating\b[^\n]{0,40}|In queue[^\n]{0,40}|Queu(?:ed|ing)[^\n]{0,40})", body)
        note = " / ".join(dict.fromkeys(prog))[:200]
        if note and note != last_note:
            browser.log(f"  [{int(time.time() - start)}s] {note}")
            last_note = note
        time.sleep(POLL_S)
    raise TimeoutError(f"no new {seconds}s video after {timeout_s}s")


def write_clip(data: bytes, url: str, out_path: Path) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".mp4.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, out_path)
    return {"file": str(out_path), "bytes": len(data), "md5": md5_bytes(data), "video_url": url}


def run_job(browser: TopViewBrowser, job_path: Path, args, ledger: dict, ledger_path: Path) -> dict:
    key = job_key(job_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    refs = Path(args.refs) if args.refs else job_path.parent / "refs"
    out_path = Path(args.out) / f"{key}.mp4"
    # a dry run writes its own row, so it can never overwrite a fired row's status and re-arm the job
    lkey = f"{key}:dry-run" if args.dry_run else key
    row = dict(ledger.get(lkey) or {}, key=key, job=str(job_path), title=job.get("title"))

    def save(status: str, **kw) -> dict:
        row.update(kw, status=status, time=now_iso())
        ledger[lkey] = row
        save_ledger(ledger_path, ledger)
        return row

    if row.get("status") in FIRED and not args.dry_run:
        return save(row["status"], note=f"already {row['status']}; not fired again (use --recover {key})")
    if out_path.exists() and not args.dry_run:
        return save("failed", note=f"{out_path} exists; refusing to overwrite")
    images = resolve_images(job, refs)

    try:
        info = prepare(browser, job, images, args.resolution, args.probe_costs)
    except HazardStop as h:
        return save("stopped", hazard_kind=h.kind, note=h.text)
    except Exception as e:
        return save("failed", note=f"prepare: {e!r}"[:500])
    row.update({k: v for k, v in info.items()})

    cost = parse_cost(info["gen_text"], info.get("cost_aria"))
    balance = parse_balance(info["balance_text"])
    row.update(cost_read=cost, balance_before=balance)
    browser.log(f"{key}: {info['model']} {info['aspect']} {info['seconds']} {info['resolution']} · "
                f"button {info['gen_text']!r} · balance {info['balance_text']!r} · chips {info['chips']}")
    if args.dry_run:
        return save("dry-run", note="everything but the Generate click")

    # the money gate: the number is read again, off the visible button, at the moment of the click
    st = browser.state()
    cost = parse_cost(st["genText"], st.get("costAria"))
    balance = parse_balance(st["balanceText"])
    if cost is None:
        return save("stopped", hazard_kind="no_cost", note=f"no cost on the Generate button: {st['genText']!r}")
    if cost > args.max_credits:
        return save("stopped", hazard_kind="over_cap", cost_read=cost,
                    note=f"button says {cost} credits > --max-credits {args.max_credits}; not clicked")
    if balance is None or balance < cost:
        return save("stopped", hazard_kind="balance", cost_read=cost, balance_before=balance,
                    note=f"balance {st['balanceText']!r} < cost {cost}; not clicked")
    if st["genDisabled"]:
        return save("stopped", hazard_kind="disabled", note=f"Generate is disabled: {st['genText']!r}")
    if st["dialogs"] or st["pricingModal"]:
        return save("stopped", hazard_kind="dialog",
                    note=f"a dialog is open: {(st['dialogs'] or [st['pricingModal']])[0][:300]}")
    if st["plan"] == "Free" and not args.allow_free_plan:
        # measured 2026-09-26: on the Free plan (5 credits, button "Generate 0.6") the click opened the
        # pricing modal "UPGRADE YOUR PLAN" and generated nothing; the CEO buys the plan himself
        return save("stopped", hazard_kind="plan_required", cost_read=cost, balance_before=balance,
                    note="plan badge reads 'Free': Generate on the Free plan opens 'UPGRADE YOUR PLAN' and "
                         "generates nothing (2026-09-26). Not clicked. Buy the plan, then re-run.")

    seen = set(browser.media_srcs())
    browser.drain_network(seen)  # every mp4 URL the page's JSON carried before the click is not ours
    t0 = time.time()
    save("submitted", cost_read=cost, balance_before=balance, fired_at=now_iso(),
         note="Generate clicked once; never click it again for this key")
    try:
        browser.click_generate(cost)
    except Exception as e:
        # the click may or may not have landed; the row stays 'submitted' so nothing re-fires it
        return save("failed-after-submit", note=f"Generate click raised {e!r}; check the board, then --recover")
    for _ in range(8):  # the pricing modal, if any, is up within a few seconds
        browser.page.wait_for_timeout(1000)
        st = browser.state()
        if st["pricingModal"]:
            break
    row["gen_text_after_click"] = st["genText"]
    if st["pricingModal"]:
        after = parse_balance(st["balanceText"])
        if after == balance:  # nothing was charged: the click only opened the modal, so the job may run again
            return save("stopped", hazard_kind="plan_required", balance_after=after,
                        note=f"Generate opened the pricing modal {st['pricingModal']!r} (plan badge "
                             f"{st['plan']!r}); balance unchanged {after}; nothing generated. Not clicked further.")
        return save("failed-after-submit", hazard_kind="plan_required", balance_after=after,
                    note=f"pricing modal {st['pricingModal']!r} after the click AND balance {balance} -> {after}")
    try:
        url, data = wait_for_clip(browser, seen, float(job["seconds"]), args.timeout_s, row)
        row["generation_s"] = round(time.time() - t0)
        clip = write_clip(data, url, out_path)
    except HazardStop as h:
        return save("failed-after-submit", hazard_kind=h.kind, note=h.text, generation_s=round(time.time() - t0))
    except Exception as e:
        return save("failed-after-submit", note=f"{e!r}"[:500], generation_s=round(time.time() - t0))
    browser.page.reload(wait_until="domcontentloaded")
    browser.page.wait_for_timeout(5000)
    after = parse_balance(browser.state()["balanceText"])
    return save("done", balance_after=after, board_url=browser.page.url, **clip)


def recover(browser: TopViewBrowser, key: str, args, ledger: dict, ledger_path: Path) -> dict:
    """Collect a clip that finished after the runner stopped waiting. Opens the board, fires nothing."""
    row = ledger.get(key) or {}
    out_path = Path(args.out) / f"{key}.mp4"
    if row.get("status") == "done" or out_path.exists():
        return {"key": key, "status": "failed", "note": "already done / file exists"}
    browser.open_generator(row.get("board_url") or row.get("generator_url") or GENERATOR_URL)
    browser.page.wait_for_timeout(5000)
    srcs = [args.video_url] if args.video_url else browser.media_srcs()
    want = parse_balance(str(row.get("seconds") or ""))  # "2s" -> 2.0
    tried = []
    for u in srcs:
        data = browser.fetch(u)
        dur = mp4_duration(data)
        tried.append(f"{u[:120]} dur={dur}")
        if args.video_url or (want and dur and abs(dur - want) <= 1.0):
            break
    else:
        return {"key": key, "status": "failed", "note": f"no {want}s video on the board; pass --video-url",
                "videos": tried}
    clip = write_clip(data, u, out_path)
    row.update(clip, status="done", time=now_iso(), note=f"recovered; videos looked at: {tried[:4]}")
    row["balance_after"] = parse_balance(browser.state()["balanceText"])
    ledger[key] = row
    save_ledger(ledger_path, ledger)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs", nargs="*", help="<key>.wan3.json job files, fired in this order")
    ap.add_argument("--out", required=True, help="dir for <key>.mp4 and ledger.json")
    ap.add_argument("--refs", help="dir holding the reference images by basename (default <job dir>/refs)")
    ap.add_argument("--resolution", help="480p / 720p / 1080p (default: the lowest the menu offers)")
    ap.add_argument("--max-credits", type=float, required=True,
                    help="fire only when the Generate button shows this many credits or fewer")
    ap.add_argument("--dry-run", action="store_true", help="everything except the Generate click")
    ap.add_argument("--probe-costs", action="store_true", help="with --dry-run: read the button at every resolution")
    ap.add_argument("--recover", metavar="KEY", help="collect KEY's finished clip from the board; fires nothing")
    ap.add_argument("--video-url", help="with --recover: the exact video URL to save")
    ap.add_argument("--cdp-url", default=CDP_DEFAULT)
    ap.add_argument("--timeout-s", type=int, default=RESULT_TIMEOUT_S)
    ap.add_argument("--keep-tab", action="store_true", help="leave the runner's tab open (debugging)")
    ap.add_argument("--allow-free-plan", action="store_true",
                    help="click Generate even when the plan badge reads 'Free' (it opened the pricing modal "
                         "on 2026-09-26; use only if TopView changes that)")
    args = ap.parse_args(argv)
    if args.probe_costs and not args.dry_run:
        ap.error("--probe-costs only with --dry-run")
    if not args.jobs and not args.recover:
        ap.error("give job files or --recover KEY")

    ledger_path = Path(args.out) / "ledger.json"
    ledger = load_ledger(ledger_path)
    browser = TopViewBrowser(args.cdp_url)
    browser.attach()
    rc = 0
    try:
        if args.recover:
            row = recover(browser, args.recover, args, ledger, ledger_path)
            print(json.dumps(row, indent=1, ensure_ascii=False)[:3000])
            return 0 if row.get("status") == "done" else 1
        for jp in args.jobs:
            row = run_job(browser, Path(jp), args, ledger, ledger_path)
            print(json.dumps({k: v for k, v in row.items() if k != "network"}, indent=1, ensure_ascii=False)[:4000])
            if row["status"] not in ("done", "dry-run"):
                print(f"STOP at {row['key']}: {row['status']} — {row.get('note')}")
                rc = 1
                break
    finally:
        browser.close(keep_tab=args.keep_tab)
    return rc


if __name__ == "__main__":
    sys.exit(main())
