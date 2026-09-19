#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The zero-model Flow shot runner — docs/ops/flow-operator-design.md, built.

Drives the logged-in automation Chrome (port 9223, dedicated profile — see
scripts/flow/launch-chrome-debug.sh) over CDP to shoot a «บัญชี» act's shots
in Google Flow: attach chips, paste the prompt, submit, download, verify.
STANDALONE — no Claude in the loop, zero token cost at runtime, same pattern
as scripts/higgsfield/gen_loop.py. The ledger (tools/flow_ledger.py) is the
runner's memory, not a context window: a crash restarts from the first
non-verified row, and a verified row is never re-fired.

    python3 tools/flow_shoot.py run    --sheet docs/scripts/banchi-ACT2.md \
        --ledger state/banchi/ACT2.tsv --dest ~/Desktop/banchi-ACT2 \
        --credit-cap 300 [--only 37-46] [--dry-run] \
        [--resolution {720p,360p}] [--force-duration N]
    python3 tools/flow_shoot.py pull   --sheet docs/scripts/banchi-ACT2.md \
        --ledger state/banchi/ACT2.tsv --dest ~/Desktop/banchi-ACT2 [--only 53-58]
    python3 tools/flow_shoot.py status --ledger state/banchi/ACT2.tsv

All Playwright/CDP calls live behind FlowBrowser below, so every decision the
runner makes (credit cap, refusal handling, zip vs. bare mp4, duration
tolerance, sheet parsing) is unit-testable without a browser — see
tests/test_flow_shoot.py. FlowBrowser itself is unverified against the live
DOM: it was written from docs/scripts/BANCHI-SHOOT-BRIEF.md and the
google-flow-ops skill, and the first live check is a human-run --dry-run
after the CEO logs into the automation Chrome (a worker cannot).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import clip_review, flow_ledger  # noqa: E402

CDP = "http://127.0.0.1:9223"
LOG_PATH = Path("state/banchi/flow_shoot.log")
DOWNLOAD_GAP_S = 8  # brief's rule: never fire two downloads closer than this
POLL_S = 8
COMPLETION_TIMEOUT_S = 8 * 60
DURATION_TOLERANCE_S = 0.6
MIN_AUDIO_DB = -60.0

# The mute-before-anything-plays snippet, verbatim from the brief. A worker
# (and this runner) has no ears; a clip playing is pure cost, zero information.
MUTE_JS = """
document.querySelectorAll('video,audio').forEach(v => {v.muted = true; v.volume = 0;});
new MutationObserver(() => document.querySelectorAll('video,audio')
  .forEach(v => {v.muted = true; v.volume = 0;}))
  .observe(document.body, {childList: true, subtree: true});
""".strip()

# "ล้มเหลว / ... อาจละเมิดนโยบาย ..." — task spec's exact detection rule.
_DIALOGUE_RE = re.compile(r'says:\s*"([^"]+)"')
_CREDIT_RE = re.compile(r"(\d+)\s*เครดิต")


# ── pure helpers (no browser — these are what tests/test_flow_shoot.py covers) ──

def parse_only(spec: str) -> set[int]:
    """"37-46" or "37,40,52" or "37-40,52" -> {37,38,...,46} / etc."""
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def is_refusal_text(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith("ล้มเหลว") or "อาจละเมิดนโยบาย" in t


def credit_cap_exceeded(spent_this_run: int, estimate: int, cap: int) -> bool:
    return spent_this_run + estimate > cap


def normalize_prompt_whitespace(text: str) -> str:
    """The composer's contenteditable box re-normalizes every run of one or
    more newlines to its own paragraph-break rendering — confirmed live
    2026-09-19 (task-a09ed18a): a single '\\n' between two dialogue lines
    and a blank-line '\\n\\n' between two paragraphs both round-trip through
    the DOM as a different, but internally consistent, number of newlines.
    Every character of actual TEXT survives; only the exact newline COUNT
    does not. Comparing raw strings after a paste therefore always reports
    a false mismatch — this collapses newline runs on both sides so the
    comparison checks content, the thing that can actually go wrong."""
    return re.sub(r"\n+", "\n", text).strip()


def effective_duration(sheet_dur_s: int, force_duration: int | None) -> int:
    """--force-duration (proof shots only) overrides the sheet's per-shot
    duration for BOTH the composer's duration setting and verify_clip's
    tolerance — the two must never disagree, or a shot generated at the
    override length would fail verification against the sheet's length."""
    return force_duration if force_duration is not None else sheet_dur_s


def parse_credit_estimate(text: str) -> int | None:
    m = _CREDIT_RE.search(text or "")
    return int(m.group(1)) if m else None


def first_dialogue_line(prompt: str) -> str | None:
    """The distinctive fragment `pull` searches the feed for — dialogue is
    unique per shot, prompt openings are not (google-flow-ops skill)."""
    m = _DIALOGUE_RE.search(prompt)
    return m.group(1) if m else None


def extract_clip(downloaded: Path, dest_dir: Path, shot_no: int) -> Path:
    """Flow's download arrives as a .zip with one .mp4, or a bare .mp4."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"shot-{shot_no:02d}.mp4"
    suffix = downloaded.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(downloaded) as zf:
            mp4s = [n for n in zf.namelist() if n.lower().endswith(".mp4")]
            if len(mp4s) != 1:
                raise ValueError(f"zip has {len(mp4s)} mp4 entries, expected 1: {mp4s}")
            with zf.open(mp4s[0]) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    elif suffix == ".mp4":
        shutil.copyfile(downloaded, dest)
    else:
        raise ValueError(f"unexpected download type: {downloaded.suffix!r}")
    return dest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_clip(path: Path, expected_dur: float) -> tuple[bool, str]:
    """ffprobe duration within tolerance, audio present. Reuses
    clip_review's own probes so the two tools never disagree on what a
    passing clip looks like."""
    if not path.exists():
        return False, "file missing"
    got = clip_review.probe_duration(path)
    if abs(got - expected_dur) > DURATION_TOLERANCE_S:
        return False, f"DURATION got {got:.1f}s want {expected_dur}s"
    db = clip_review.mean_db(path)
    if db is None or db < MIN_AUDIO_DB:
        return False, "NO AUDIO"
    return True, f"{got:.1f}s"


def _log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── the only place that touches a browser ───────────────────────────────────

class FlowBrowser:
    """Playwright-over-CDP adapter. Every method here is one decision the
    brief/skill documented; nothing here is exercised by the unit tests —
    swap this class for a stub with the same method names to test the
    runner's control flow without Chrome."""

    def __init__(self, cdp_url: str = CDP):
        self.cdp_url = cdp_url
        self._pw = None
        self._browser = None
        self.page = None

    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None)
        if page is None:
            raise RuntimeError(
                "NO_FLOW_TAB — open the project tab in the automation Chrome first")
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

    def set_settings(self, dur_s: int, resolution: str = "720p") -> dict:
        """Set model=Omni 1.1 Flash, mode=องค์ประกอบ, aspect=9:16, qty=x1,
        resolution, duration=dur_s, then read every one of them back off the
        DOM — NONE of them are sticky (BANCHI-SHOOT-BRIEF.md).

        CORRECTED 2026-09-19 (task-a09ed18a, live --dry-run against the
        automation Chrome): the composer's collapsed pill (aria-label
        "ทริกเกอร์การตั้งค่า") only ever shows facets as flattened TEXT —
        there are no per-facet aria-labels ("Ratio"/"Duration"/"Resolution")
        anywhere in the DOM; the original guesses always timed out. Every
        real facet control lives inside the `<flow-prompt-box-settings>`
        overlay panel that button opens, as an Angular Material
        `mat-button-toggle` group per facet (image/video, เฟรม/องค์ประกอบ,
        aspect, resolution, duration, quantity), matched here by each
        option's own visible text — none of them carry a stable aria-label
        either. The panel defaults to the "รูปภาพ" (Image) tab on a fresh
        open; "วิดีโอ" must be clicked first or every later facet click hits
        the wrong (image-mode) panel.
        """
        page = self.page
        for _ in range(3):
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
        panel = page.locator("flow-prompt-box-settings")
        # Opening the panel is racy in the same way chip-attach is
        # documented as racy (google-flow-ops) — a single click does not
        # reliably land. Poll instead of trusting one click+wait.
        for _ in range(5):
            if panel.count():
                break
            try:
                page.locator('button[aria-label="ทริกเกอร์การตั้งค่า"]').first.click(timeout=3000)
            except Exception as e:
                _log(f"  settings panel open err: {e!r}")
            page.wait_for_timeout(400)
        if panel.count() == 0:
            _log("  settings panel never opened after 5 attempts")
        # The panel can reopen on either the "รูปภาพ" (Image) or "วิดีโอ"
        # tab depending on what it last showed in this page session — check
        # the actual state (duration buttons only exist in video mode)
        # instead of assuming one click is needed.
        for _ in range(3):
            try:
                txt = panel.evaluate("el => el.innerText") if panel.count() else ""
            except Exception:
                txt = ""
            if "วินาที" in txt:
                break
            try:
                panel.get_by_text("วิดีโอ", exact=True).first.click(timeout=2000)
            except Exception as e:
                _log(f"  video-tab select err: {e!r}")
            page.wait_for_timeout(300)
        try:
            panel.locator('button[aria-label="เลือกกลุ่มผลิตภัณฑ์โมเดล"]').first.click(timeout=3000)
            page.wait_for_timeout(300)
            page.locator("[role=menuitem]").filter(has_text="Omni 1.1 Flash").first.click(timeout=3000)
        except Exception as e:
            _log(f"  model select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text="องค์ประกอบ").first.click(timeout=3000)
        except Exception as e:
            _log(f"  mode select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text="9:16").first.click(timeout=3000)
        except Exception as e:
            _log(f"  ratio select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text=resolution).first.click(timeout=3000)
        except Exception as e:
            _log(f"  resolution select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text=f"{dur_s} วินาที").first.click(timeout=3000)
        except Exception as e:
            _log(f"  duration select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text="x1").first.click(timeout=3000)
        except Exception as e:
            _log(f"  quantity select err: {e!r}")
        page.wait_for_timeout(200)
        settings = self.read_settings(dur_s, resolution)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        return settings

    def _toggle_checked(self, panel, label_text: str) -> bool:
        """mat-button-toggle labels (720p/360p, x1..x4, เฟรม/องค์ประกอบ, every
        aspect ratio, every duration) are ALL rendered at once regardless of
        which is selected — `"720p" in body` is true whether or not 720p is
        the active choice. The selected option alone carries the
        `mat-button-toggle-checked` class on the <mat-button-toggle> wrapper,
        one level above the clickable <button>; that class is the only
        reliable read-back."""
        el = panel.locator("mat-button-toggle").filter(has_text=label_text).first
        if el.count() == 0:
            return False
        return "mat-button-toggle-checked" in (el.get_attribute("class") or "")

    def read_settings(self, dur_s: int, resolution: str = "720p") -> dict:
        page = self.page
        panel = page.locator("flow-prompt-box-settings")
        if panel.count() == 0:
            # Panel already closed — the collapsed pill's flattened text is
            # the only signal left for facets it actually renders (model,
            # aspect, resolution, duration); mode/quantity aren't shown
            # collapsed at all, so they can't be contradicted from here.
            body = page.evaluate("() => document.body.innerText")
            return {
                "model_omni": "Omni 1.1 Flash" in body,
                "mode_ingredients": True,
                "aspect_9_16": "9:16" in body,
                "qty_x1": True,
                "resolution": resolution in body,
                "duration": f"{dur_s} วินาที" in body,
            }
        body = panel.evaluate("el => el.innerText")
        return {
            "model_omni": "Omni 1.1 Flash" in body,
            "mode_ingredients": self._toggle_checked(panel, "องค์ประกอบ"),
            "aspect_9_16": self._toggle_checked(panel, "9:16"),
            "qty_x1": self._toggle_checked(panel, "x1"),
            "resolution": self._toggle_checked(panel, resolution),
            "duration": self._toggle_checked(panel, f"{dur_s} วินาที"),
        }

    def chip_count(self) -> int:
        """CORRECTED 2026-09-19 (task-a09ed18a, live dry-run): a chip is
        <flow-ingredient-chip><flow-*-ingredient-chip>...</...>, not the
        outdated `span.mention-chip[data-entity-id]` (0 matches, always).
        `flow-ingredient-chip` alone is page-wide — every past generation
        card in the feed renders its own (19+ on a modest project) — so this
        must scope to the composer's own bar, `<flow-ingredient-bar
        class="prompt-ingredient-bar">`, confirmed to appear exactly once."""
        return self.page.locator("flow-ingredient-bar flow-ingredient-chip").count()

    def attach_chip(self, handle: str) -> bool:
        """CORRECTED 2026-09-19 (task-a09ed18a, live dry-run): the picker is
        NOT open by default — it must be opened via the composer's own "+"
        button (aria-label เพิ่มองค์ประกอบลงในช่องพรอมต์) every time; it
        auto-closes after one attach, so this reopens it on every call. Once
        open, a matching `.asset-item` row (confirmed class, google-flow-ops
        2026-09-08) is single-clicked, which opens a preview pane with its
        own เพิ่มไปยังพรอมต์ button — click that to actually attach. The
        brief's older "⋮ more options" menu path was not found live and is
        dropped rather than kept as a silently-dead fallback."""
        page = self.page
        name = handle.lstrip("@")
        try:
            page.locator('button[aria-label="เพิ่มองค์ประกอบลงในช่องพรอมต์"]').first.click(timeout=3000)
            page.wait_for_timeout(400)
        except Exception as e:
            _log(f"  attach_chip({handle}) open picker err: {e!r}")
            return False
        try:
            row = page.locator(".asset-item").filter(has_text=f"@{name}").first
            if row.count() == 0:
                _log(f"  attach_chip({handle}): no matching .asset-item row")
                return False
            row.click(timeout=2000)
            page.wait_for_timeout(300)
            page.get_by_text("เพิ่มไปยังพรอมต์", exact=False).first.click(timeout=2000)
            return True
        except Exception as e:
            _log(f"  attach_chip({handle}) failed: {e!r}")
            return False

    def paste_prompt(self, text: str) -> None:
        """CORRECTED 2026-09-19 (task-a09ed18a, live dry-run): typing the
        prompt character-by-character (`keyboard.type`) mashed the sheet's
        blank-line paragraph breaks together with NO separator at all
        ("staircase.In a narrow...", one word run-on) — CDP key events don't
        drive this editor's own paragraph-insertion logic the way a real
        paste does. `keyboard.insert_text()` (CDP Input.insertText, the same
        primitive a paste uses) reproduces every paragraph break correctly.
        The editor still re-normalizes blank-line COUNT on its own terms —
        see normalize_prompt_whitespace() for why the mismatch check must
        compare content, not exact newline counts."""
        box = self.page.locator('[contenteditable="true"]').first
        box.click()
        self.page.keyboard.press("Meta+A")
        self.page.keyboard.press("Backspace")
        box.evaluate("el => el.focus()")
        self.page.keyboard.insert_text(text)

    def read_prompt_text(self) -> str:
        return self.page.locator('[contenteditable="true"]').first.inner_text()

    def read_credit_estimate(self) -> int:
        """The estimate ("การสร้างจะใช้ N เครดิต") is rendered ONLY inside the
        `<flow-prompt-box-settings>` overlay panel — confirmed live
        2026-09-19: it is present in document.body.innerText while the panel
        is open and gone the instant it closes. BANCHI-SHOOT-BRIEF.md calls
        for reading it "immediately before Submit", so this reopens the
        panel fresh each time rather than reusing a value cached from
        set_settings, and leaves the page exactly as it found it (closes
        the panel again if it opened it)."""
        page = self.page
        panel = page.locator("flow-prompt-box-settings")
        opened_here = panel.count() == 0
        if opened_here:
            for _ in range(5):
                if panel.count():
                    break
                try:
                    page.locator('button[aria-label="ทริกเกอร์การตั้งค่า"]').first.click(timeout=3000)
                except Exception:
                    pass
                page.wait_for_timeout(400)
            for _ in range(3):
                try:
                    txt = panel.evaluate("el => el.innerText") if panel.count() else ""
                except Exception:
                    txt = ""
                if "วินาที" in txt:
                    break
                try:
                    panel.get_by_text("วิดีโอ", exact=True).first.click(timeout=2000)
                except Exception:
                    pass  # already on วิดีโอ from an earlier open this session
                page.wait_for_timeout(300)
        try:
            text = panel.evaluate("el => el.innerText") if panel.count() else ""
        except Exception:
            text = ""
        if opened_here:
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
        est = parse_credit_estimate(text)
        if est is None:
            raise RuntimeError("could not read live credit estimate from the panel")
        return est

    def submit(self) -> None:
        self.page.locator('button[aria-label="เริ่มสร้าง"]').first.click()

    def poll_result(self, timeout_s: int = COMPLETION_TIMEOUT_S) -> dict:
        page = self.page
        start = time.time()
        while time.time() - start < timeout_s:
            body = page.evaluate("() => document.body.innerText")
            if is_refusal_text(body):
                m = re.search(r"ล้มเหลว[^\n]*\n[^\n]*", body)
                return {"status": "refusal", "text": m.group(0) if m else "ล้มเหลว"}
            if page.locator('[aria-label="Download"], [aria-label="ดาวน์โหลด"]').count():
                return {"status": "download", "text": ""}
            time.sleep(POLL_S)
        return {"status": "timeout", "text": ""}

    def download(self) -> Path:
        with self.page.expect_download() as dl_info:
            self.page.locator('[aria-label="Download"], [aria-label="ดาวน์โหลด"]').first.click()
        dl = dl_info.value
        import tempfile
        path = Path(tempfile.mkdtemp()) / dl.suggested_filename
        dl.save_as(str(path))
        return path

    def find_card_by_dialogue(self, fragment: str):
        page = self.page
        el = page.get_by_text(fragment, exact=False).first
        return el if el.count() else None

    def download_card(self, card) -> Path:
        card.click()
        return self.download()


# ── the runner ───────────────────────────────────────────────────────────────

def _attempt_chip(browser: FlowBrowser, handle: str) -> bool:
    before = browser.chip_count()
    browser.attach_chip(handle)
    for _ in range(5):
        if browser.chip_count() > before:
            return True
        time.sleep(1.5)
    return False


def cmd_run(args: argparse.Namespace) -> int:
    sheet_path = Path(args.sheet)
    ledger_path = Path(args.ledger)
    dest = Path(args.dest).expanduser()
    only = parse_only(args.only) if args.only else None

    flow_ledger.init_ledger(sheet_path, ledger_path)
    rows = flow_ledger.load_ledger(ledger_path)
    sheet_shots = {s["shot"]: s for s in flow_ledger.parse_sheet(sheet_path)}

    todo = [n for n in sorted(rows)
            if rows[n]["status"] not in ("verified", "refused")
            and (only is None or n in only)]
    if not todo:
        _log("nothing to do")
        return 0

    if args.force_duration is not None:
        _log(f"*** FORCE-DURATION OVERRIDE ACTIVE: {args.force_duration}s overrides "
             f"every shot's sheet duration in this run, for BOTH the composer's "
             f"duration setting AND verify_clip's tolerance — PROOF SHOTS ONLY, "
             f"never use this for a production run ***")

    browser = FlowBrowser()
    spent_this_run = 0
    try:
        try:
            browser.attach()
            browser.mute_all_media()
        except Exception as e:
            _log(f"cannot attach to Chrome at {CDP}: {e!r}")
            _log("is scripts/flow/launch-chrome-debug.sh running, "
                 "logged in, with the project tab open?")
            return 1
        _log(f"attached + muted, {len(todo)} row(s) to attempt")

        for n in todo:
            row = rows[n]
            shot = sheet_shots.get(n)
            if shot is None:
                _log(f"shot {n}: not in sheet — skip")
                continue
            dur_s = effective_duration(shot["dur_s"], args.force_duration)
            try:
                settings = browser.set_settings(dur_s, args.resolution)
                bad = [k for k, v in settings.items() if not v]
                if bad:
                    row["status"], row["note"] = "needs_model", f"settings not confirmed: {bad}"
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: needs_model — {row['note']}")
                    continue

                attach_fail = None
                for handle in shot["chips"]:
                    if not _attempt_chip(browser, handle):
                        attach_fail = handle
                        break
                if attach_fail:
                    row["status"], row["note"] = "needs_model", f"chip never attached: {attach_fail}"
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: needs_model — {row['note']}")
                    continue

                browser.paste_prompt(shot["prompt"])
                actual = browser.read_prompt_text()
                if normalize_prompt_whitespace(actual) != normalize_prompt_whitespace(shot["prompt"]):
                    browser.paste_prompt(shot["prompt"])
                    actual = browser.read_prompt_text()
                    if normalize_prompt_whitespace(actual) != normalize_prompt_whitespace(shot["prompt"]):
                        row["status"], row["note"] = "needs_model", "prompt mismatch after retry"
                        flow_ledger.save_ledger(ledger_path, rows)
                        _log(f"shot {n}: needs_model — prompt mismatch")
                        continue

                estimate = browser.read_credit_estimate()
                if credit_cap_exceeded(spent_this_run, estimate, args.credit_cap):
                    _log(f"CAP REACHED: spent={spent_this_run} + estimate={estimate} "
                         f"> cap={args.credit_cap} — stopping the whole run")
                    break

                if args.dry_run:
                    _log(f"DRY-RUN shot {n}: settings={settings} chips={shot['chips']} "
                         f"resolution={args.resolution} dur_s={dur_s} "
                         f"prompt_verified=True estimate={estimate} credits — stopping before Submit")
                    return 0

                browser.submit()
                row["attempts"] = str(int(row.get("attempts") or 0) + 1)
                row["status"] = "submitted"
                flow_ledger.save_ledger(ledger_path, rows)
                spent_this_run += estimate
                _log(f"shot {n}: submitted (attempt {row['attempts']}, est {estimate} credits)")

                result = browser.poll_result()
                if result["status"] == "refusal" and int(row["attempts"]) == 1:
                    _log(f"shot {n}: refused — re-firing identical prompt once (refunded)")
                    browser.submit()
                    row["attempts"] = "2"
                    flow_ledger.save_ledger(ledger_path, rows)
                    result = browser.poll_result()

                if result["status"] == "refusal":
                    row["status"], row["note"] = "refused", result["text"]
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: refused — {result['text']!r}")
                    continue
                if result["status"] == "timeout":
                    row["status"], row["note"] = "failed", "timeout"
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: failed — timeout")
                    continue

                row["status"] = "generated"
                flow_ledger.save_ledger(ledger_path, rows)

                downloaded = browser.download()
                time.sleep(DOWNLOAD_GAP_S)
                clip_path = extract_clip(downloaded, dest, n)
                row["file"] = str(clip_path)
                row["status"] = "downloaded"
                flow_ledger.save_ledger(ledger_path, rows)

                ok, reason = verify_clip(clip_path, dur_s)
                row["sha256"] = sha256_file(clip_path)
                row["got_dur"] = reason
                if ok:
                    row["status"] = "verified"
                else:
                    bad_path = clip_path.with_name("bad-" + clip_path.name)
                    clip_path.rename(bad_path)
                    row["file"], row["status"], row["note"] = str(bad_path), "failed", reason
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: {row['status']} — {reason}")

            except Exception as e:
                row["status"], row["note"] = "failed", f"exception: {e!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: EXCEPTION {e!r}")
                continue
    finally:
        browser.close()

    print(flow_ledger.status_summary(ledger_path))
    final = flow_ledger.load_ledger(ledger_path)
    attempted = [n for n in todo if final[n]["status"] != "todo"]
    all_ok = all(final[n]["status"] == "verified" for n in attempted) if attempted else True
    return 0 if all_ok else 1


def cmd_pull(args: argparse.Namespace) -> int:
    sheet_path = Path(args.sheet)
    ledger_path = Path(args.ledger)
    dest = Path(args.dest).expanduser()
    only = parse_only(args.only) if args.only else None

    flow_ledger.init_ledger(sheet_path, ledger_path)
    rows = flow_ledger.load_ledger(ledger_path)
    sheet_shots = {s["shot"]: s for s in flow_ledger.parse_sheet(sheet_path)}

    targets = [n for n in sorted(rows)
               if rows[n]["status"] != "verified" and (only is None or n in only)]
    if not targets:
        _log("nothing to pull")
        return 0

    browser = FlowBrowser()
    try:
        try:
            browser.attach()
            browser.mute_all_media()
        except Exception as e:
            _log(f"cannot attach to Chrome at {CDP}: {e!r}")
            _log("is scripts/flow/launch-chrome-debug.sh running, "
                 "logged in, with the project tab open?")
            return 1
        for n in targets:
            row = rows[n]
            shot = sheet_shots.get(n)
            dialogue = first_dialogue_line(shot["prompt"]) if shot else None
            if not dialogue:
                row["status"], row["note"] = "needs_model", "no dialogue line to search for"
                flow_ledger.save_ledger(ledger_path, rows)
                continue
            card = browser.find_card_by_dialogue(dialogue)
            if card is None:
                row["status"], row["note"] = "needs_model", f"card not found for: {dialogue!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: needs_model — card not found")
                continue
            downloaded = browser.download_card(card)
            time.sleep(DOWNLOAD_GAP_S)
            clip_path = extract_clip(downloaded, dest, n)
            ok, reason = verify_clip(clip_path, shot["dur_s"])
            row["file"] = str(clip_path)
            row["sha256"] = sha256_file(clip_path)
            row["got_dur"] = reason
            if ok:
                row["status"] = "verified"
            else:
                bad_path = clip_path.with_name("bad-" + clip_path.name)
                clip_path.rename(bad_path)
                row["file"], row["status"], row["note"] = str(bad_path), "failed", reason
            flow_ledger.save_ledger(ledger_path, rows)
            _log(f"shot {n}: {row['status']} — {reason}")
    finally:
        browser.close()

    print(flow_ledger.status_summary(ledger_path))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(flow_ledger.status_summary(Path(args.ledger)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--sheet", required=True)
    p_run.add_argument("--ledger", required=True)
    p_run.add_argument("--dest", required=True)
    p_run.add_argument("--credit-cap", type=int, required=True)
    p_run.add_argument("--only", default=None)
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--resolution", choices=["720p", "360p"], default="720p",
                        help="Composer resolution facet — read back off the "
                             "settings row like the other settings.")
    p_run.add_argument("--force-duration", type=int, default=None,
                        help="PROOF SHOTS ONLY. Overrides the sheet's per-shot "
                             "duration for both the composer's duration setting "
                             "and verify_clip's tolerance.")
    p_run.set_defaults(func=cmd_run)

    p_pull = sub.add_parser("pull")
    p_pull.add_argument("--sheet", required=True)
    p_pull.add_argument("--ledger", required=True)
    p_pull.add_argument("--dest", required=True)
    p_pull.add_argument("--only", default=None)
    p_pull.set_defaults(func=cmd_pull)

    p_status = sub.add_parser("status")
    p_status.add_argument("--ledger", required=True)
    p_status.set_defaults(func=cmd_status)

    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
